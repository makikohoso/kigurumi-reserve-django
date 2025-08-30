from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import Reservation, RentalItem, CalendarStatus
from .email_utils import send_reservation_emails
from datetime import datetime, date, timedelta
import json
import time
import re
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def validate_reservation_business_rules(date_obj, item, user_ip=None, phone=None):
    """予約ビジネスルールの検証"""
    errors = []
    now = timezone.now()
    
    # 1. 予約期間制限チェック
    max_advance = timedelta(days=settings.RESERVATION_SETTINGS['MAX_ADVANCE_DAYS'])
    min_advance = timedelta(days=settings.RESERVATION_SETTINGS['MIN_ADVANCE_DAYS'])
    
    if date_obj > (now.date() + max_advance):
        errors.append(f"予約は{settings.RESERVATION_SETTINGS['MAX_ADVANCE_DAYS']}日前までしかできません")
    
    if date_obj < (now.date() + min_advance):
        errors.append(f"予約は{settings.RESERVATION_SETTINGS['MIN_ADVANCE_DAYS']}日前までに行ってください")
    
    # 2. 同日同一ユーザーの予約制限（電話番号ベース）
    if phone:
        today_reservations = Reservation.objects.filter(
            phone=phone,
            created_at__date=now.date(),
            status__in=['adjusting', 'completed']
        ).count()
        
        # デバッグ情報（開発環境のみ）
        if settings.DEBUG:
            print(f"予約制限チェック: 電話番号={phone}, 今日の予約数={today_reservations}, 上限={settings.RESERVATION_SETTINGS['MAX_RESERVATIONS_PER_USER_PER_DAY']}")
        
        if today_reservations >= settings.RESERVATION_SETTINGS['MAX_RESERVATIONS_PER_USER_PER_DAY']:
            errors.append(f"1日あたり{settings.RESERVATION_SETTINGS['MAX_RESERVATIONS_PER_USER_PER_DAY']}件までしか予約できません（現在{today_reservations}件）")
    
    # 3. 営業時間・営業日チェック（基本的な例）
    if date_obj.weekday() == 6:  # 日曜日
        errors.append("日曜日は休業日のため予約できません")
    
    return errors

def check_rate_limiting(user_ip):
    """レート制限チェック（実装版）"""
    if not settings.RESERVATION_SETTINGS['ENABLE_RATE_LIMITING']:
        return []
    
    # 1時間以内の予約試行回数をチェック
    hour_ago = timezone.now() - timedelta(hours=1)
    
    # 実際の予約作成試行をカウント（今回はReservationテーブルを利用）
    recent_attempts = Reservation.objects.filter(
        created_at__gte=hour_ago
    ).exclude(status='cancelled').count()
    
    # 同一IPからの試行をより厳密にチェック（簡易実装）
    # 実際の運用では、専用のRateLimitテーブルやRedisを使用することを推奨
    if recent_attempts >= settings.RESERVATION_SETTINGS['RATE_LIMIT_PER_HOUR']:
        return ['現在アクセスが集中しています。しばらく時間を置いてから再度お試しください。']
    
    return []

def check_date_availability(target_date, item, is_current_month=True, is_past_date=False):
    """日付の予約可能性を効率的にチェック"""
    # 過去の日付や当月以外は利用不可
    if is_past_date or not is_current_month:
        return False
    
    # 在庫ベースの可用性チェック
    return item.is_available_for_date(target_date)

def get_date_status_text(target_date, item, is_current_month=True, is_past_date=False):
    """日付のステータステキスト（◯/△/✕）を取得"""
    # 過去の日付や当月以外、物品が非アクティブの場合
    if is_past_date or not is_current_month or not item.is_active:
        return '-'
    
    # 在庫ベースのステータス取得
    return item.get_status_for_date(target_date)

def check_date_availability_legacy(target_date, item, is_current_month=True, is_past_date=False):
    """レガシー: CalendarStatusを使った日付の予約可能性チェック（後方互換性）"""
    # 過去の日付や当月以外は利用不可
    if is_past_date or not is_current_month:
        return False
    
    # 予約の存在チェック（優先）
    if Reservation.objects.filter(
        date=target_date, 
        item=item, 
        status__in=['adjusting', 'confirmed']
    ).exists():
        return False
    
    # CalendarStatusチェック
    try:
        calendar_status = CalendarStatus.objects.get(date=target_date, item=item)
        return calendar_status.is_available
    except CalendarStatus.DoesNotExist:
        # CalendarStatusが存在しない場合はデフォルトで利用可能
        return True

def reserve_form(request):
    if request.method == "POST":
        name = request.POST.get("name")
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        date_str = request.POST.get("date")
        item_id = request.POST.get("item")
        notes = request.POST.get("notes", "").strip()
        user_ip = request.META.get('REMOTE_ADDR')
        
        # 強化された基本バリデーション
        errors = []
        
        # 名前の検証
        if not name or not name.strip():
            errors.append("名前を入力してください")
        elif len(name.strip()) > 100:
            errors.append("名前は100文字以内で入力してください")
        
        # 電話番号の検証
        if not phone:
            errors.append("電話番号を入力してください")
        else:
            # 電話番号の形式チェック（日本の電話番号形式）
            phone_cleaned = re.sub(r'[^\d-]', '', phone)
            if not re.match(r'^(\d{2,4}-\d{2,4}-\d{4}|\d{10,11})$', phone_cleaned):
                errors.append("電話番号の形式が正しくありません（例：090-1234-5678）")
        
        # メールアドレスの検証
        if not email:
            errors.append("メールアドレスを入力してください")
        else:
            # メールアドレスの形式チェック
            if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                errors.append("メールアドレスの形式が正しくありません")
            elif len(email) > 254:
                errors.append("メールアドレスが長すぎます")
        
        # 予約日の検証
        if not date_str:
            errors.append("予約日を選択してください")
        
        # 物品IDの検証
        if not item_id:
            errors.append("レンタル物品を選択してください")
        
        # 備考欄の文字数制限
        if notes and len(notes) > 500:
            errors.append("備考は500文字以内で入力してください")
        
        # レート制限チェック
        rate_limit_errors = check_rate_limiting(user_ip)
        errors.extend(rate_limit_errors)
            
        if not errors:
            try:
                # 日付文字列を日付オブジェクトに変換
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                # レンタル物品を取得
                item = get_object_or_404(RentalItem, id=item_id, is_active=True)
                
                # ビジネスルール検証
                business_rule_errors = validate_reservation_business_rules(
                    date_obj, item, user_ip, phone
                )
                errors.extend(business_rule_errors)
                
                if not errors:
                    # セッションに予約データを保存
                    reservation_data = {
                        'name': name,
                        'phone': phone,
                        'email': email,
                        'date': date_str,
                        'item_id': item_id,
                        'notes': notes
                    }
                    
                    # セッションにデータを保存
                    request.session['pending_reservation'] = reservation_data
                    request.session.modified = True
                    
                    # デバッグ情報
                    if settings.DEBUG:
                        print(f"Debug - Saving reservation data to session: {reservation_data}")
                        print(f"Debug - Session key: {request.session.session_key}")
                    
                    # サーバーサイドリダイレクトで確認画面へ
                    return redirect('reservation_confirm')
                        
            except ValueError:
                errors.append("無効な日付形式です")
                
        if errors:
            # 利用可能なレンタル物品を取得
            items = RentalItem.objects.filter(is_active=True)
            return render(request, "reservations/form.html", {
                "items": items,
                "errors": errors,
                "form_data": {
                    "name": name,
                    "phone": phone,
                    "email": email,
                    "date": date_str,
                    "item": item_id,
                    "notes": notes
                }
            })
    
    # 利用可能なレンタル物品を取得
    items = RentalItem.objects.filter(is_active=True)
    return render(request, "reservations/form.html", {
        "items": items
    })

def get_calendar_data():
    """カレンダー表示用のデータを生成（今日から30日間）"""
    today = date.today()
    end_date = today + timedelta(days=30)
    
    # 日付範囲を生成
    dates = []
    current_date = today
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    # アクティブなアイテムを取得
    items = RentalItem.objects.filter(is_active=True).order_by('name')
    
    # カレンダーデータを行形式で構築
    calendar_rows = []
    for current_date in dates:
        row_data = {
            'date': current_date,
            'items_status': []
        }
        
        for item in items:
            status, created = CalendarStatus.objects.get_or_create(
                date=current_date,
                item=item,
                defaults={'is_available': True}
            )
            row_data['items_status'].append({
                'item': item,
                'is_available': status.is_available,
                'status_text': "◯" if status.is_available else "✗"
            })
        
        calendar_rows.append(row_data)
    
    return {
        'items': items,
        'rows': calendar_rows
    }

def toggle_calendar_status(request):
    """カレンダーのステータスを切り替え"""
    if request.method == "POST":
        date_str = request.POST.get('date')
        item_id = request.POST.get('item_id')
        
        if date_str and item_id:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                item = get_object_or_404(RentalItem, id=item_id)
                
                status_obj, created = CalendarStatus.objects.get_or_create(
                    date=target_date,
                    item=item,
                    defaults={'is_available': True}
                )
                # ステータスを反転
                status_obj.is_available = not status_obj.is_available
                status_obj.save()
                
                return JsonResponse({
                    'success': True,
                    'is_available': status_obj.is_available,
                    'status_text': "◯" if status_obj.is_available else "✗"
                })
            except (ValueError, RentalItem.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'Invalid date or item'})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_item_images(request, item_id):
    """物品画像を取得するAPI"""
    try:
        item = get_object_or_404(RentalItem, id=item_id, is_active=True)
        images = []
        
        for img in item.get_all_images():
            images.append({
                'id': img.id,
                'url': img.image.url,
                'thumbnail_url': img.get_thumbnail_url(),
                'alt_text': img.alt_text,
                'is_primary': img.is_primary,
                'order': img.order
            })
        
        return JsonResponse({
            'success': True,
            'item_name': item.name,
            'images': images
        })
    except RentalItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

def reservation_confirm(request):
    """予約確認画面"""
    # セッションから予約データを取得
    reservation_data = request.session.get('pending_reservation')
    
    if not reservation_data:
        messages.error(request, "予約データが見つかりません。最初からやり直してください。")
        return redirect('reserve_form')
    
    try:
        # 日付文字列を日付オブジェクトに変換
        date_obj = datetime.strptime(reservation_data['date'], "%Y-%m-%d").date()
        item = get_object_or_404(RentalItem, id=reservation_data['item_id'], is_active=True)
        
        # デバッグ情報
        if settings.DEBUG:
            print(f"Debug - Confirm view loaded successfully for item: {item.name}, date: {date_obj}")
        
    except (ValueError, RentalItem.DoesNotExist) as e:
        logger.error(f"Reservation confirm validation error: {str(e)}")
        messages.error(request, f"予約データに問題があります。エラー: {str(e)}")
        return redirect('reserve_form')
    
    context = {
        'reservation_data': reservation_data,
        'date_obj': date_obj,
        'item': item,
    }
    return render(request, 'reservations/confirm.html', context)

def reservation_complete(request):
    """予約完了処理"""
    if request.method != 'POST':
        return redirect('reserve_form')
    
    # セッションから予約データを取得
    reservation_data = request.session.get('pending_reservation')
    
    if not reservation_data:
        messages.error(request, "予約データが見つかりません。")
        return redirect('reserve_form')
    
    try:
        # 日付文字列を日付オブジェクトに変換
        date_obj = datetime.strptime(reservation_data['date'], "%Y-%m-%d").date()
        item = get_object_or_404(RentalItem, id=reservation_data['item_id'], is_active=True)
        
        # トランザクション処理で同時予約競合を回避
        with transaction.atomic():
            # 在庫ベースの予約可能性の最終チェック（ロック付き）
            confirmed_reservations_count = Reservation.objects.select_for_update().filter(
                date=date_obj,
                item=item,
                status__in=['adjusting', 'completed']
            ).count()
            
            if confirmed_reservations_count >= item.total_stock:
                messages.error(request, "申し訳ございませんが、この日時の在庫がありません。別の日付をお選びください。")
                return redirect('reserve_form')
            
            # 予約を作成
            reservation = Reservation.objects.create(
                name=reservation_data['name'], 
                phone=reservation_data['phone'],
                email=reservation_data['email'],
                date=date_obj, 
                item=item,
                notes=reservation_data['notes'],
                status='adjusting'  # 明示的に調整中で作成
            )
            
            # メール送信（エラーが起きても予約自体は成功として扱う）
            try:
                send_reservation_emails(reservation)
                logger.info(f"予約完了メール送信成功: {reservation.confirmation_number}")
            except Exception as e:
                logger.error(f"メール送信失敗: {str(e)} - 予約番号: {reservation.confirmation_number}")
                # メール送信失敗してもユーザーには成功画面を表示
            
            # セッションから予約データを削除
            if 'pending_reservation' in request.session:
                del request.session['pending_reservation']
                request.session.modified = True
            
            return render(request, "reservations/thanks.html", {
                "reservation": reservation
            })
            
    except (ValueError, ValidationError, IntegrityError) as e:
        messages.error(request, f"予約処理中にエラーが発生しました: {str(e)}")
        return redirect('reserve_form')
    except Exception as e:
        messages.error(request, "予約処理中にエラーが発生しました。")
        logger.error(f"Reservation creation error: {str(e)}")
        return redirect('reserve_form')

def reservations_list(request):
    """予約一覧表示（予約者向け）"""
    # 今日以降の予約を日付順で取得（キャンセル以外のみ）
    today = date.today()
    reservations = Reservation.objects.select_related('item').filter(
        date__gte=today,
        status__in=['adjusting', 'completed']  # キャンセル以外
    ).order_by('date', 'item__name')
    
    context = {
        'reservations': reservations
    }
    
    return render(request, "reservations/reservations.html", context)

def get_calendar_data_for_item(request, item_id):
    """特定の物品のカレンダーデータを返すAPI"""
    try:
        item = get_object_or_404(RentalItem, id=item_id, is_active=True)
        
        # URLパラメータから年月を取得（デフォルトは今月）
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))
        
        # その月の1日を取得
        target_date = date(year, month, 1)
        
        # 月のカレンダーデータを生成
        calendar_weeks = []
        
        # その月の最初の日の曜日を取得（0=月曜日, 6=日曜日）
        first_day_weekday = target_date.weekday()
        # 日曜日を0にするため調整（Pythonは月曜日が0）
        first_day_of_week = (first_day_weekday + 1) % 7
        
        # その月の日数を取得
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        days_in_month = (next_month_first - target_date).days
        
        # カレンダーの週データを作成
        current_date = target_date - timedelta(days=first_day_of_week)
        today = date.today()
        
        for week in range(6):  # 最大6週間
            week_data = []
            for day in range(7):  # 日曜日から土曜日
                display_date = current_date + timedelta(days=week*7 + day)
                
                # 当月かどうかを判定
                is_current_month = display_date.month == month
                # MIN_ADVANCE_DAYSを考慮した予約可能日制限
                min_reservation_date = today + timedelta(days=settings.RESERVATION_SETTINGS['MIN_ADVANCE_DAYS'])
                is_past_date = display_date < min_reservation_date
                
                # 予約状況を効率的にチェック（休業日考慮）
                if display_date.weekday() == 6 and is_current_month and not is_past_date:  # 日曜日
                    is_available = False
                else:
                    is_available = check_date_availability(display_date, item, is_current_month, is_past_date)
                
                # 休業日の場合の表示調整
                if display_date.weekday() == 6 and is_current_month and not is_past_date:
                    status_text = '休'
                else:
                    status_text = get_date_status_text(display_date, item, is_current_month, is_past_date)
                
                # △も予約可能として扱う
                is_clickable = is_available or status_text == '△'
                
                week_data.append({
                    'date': display_date.strftime('%Y-%m-%d'),
                    'day': display_date.day,
                    'is_available': is_clickable,
                    'is_current_month': is_current_month,
                    'is_past_date': is_past_date,
                    'status_text': status_text
                })
            calendar_weeks.append(week_data)
            
            # 当月の日付が全て表示されたら終了
            if (week + 1) * 7 >= first_day_of_week + days_in_month:
                break
        
        return JsonResponse({
            'success': True,
            'calendar_data': {
                'item_name': item.name,
                'year': year,
                'month': month,
                'month_name': f'{year}年{month}月',
                'weeks': calendar_weeks
            }
        })
        
    except (RentalItem.DoesNotExist, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid request'})

def check_availability(request):
    """予約可能性をチェックするAPI"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            date_str = data.get('date')
            item_id = data.get('item_id')
            
            if not date_str or not item_id:
                return JsonResponse({'available': False, 'error': 'Missing parameters'})
            
            # 日付と物品の検証
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            item = get_object_or_404(RentalItem, id=item_id, is_active=True)
            
            # 統合された可用性チェック
            # MIN_ADVANCE_DAYSを考慮した予約可能日制限
            min_reservation_date = date.today() + timedelta(days=settings.RESERVATION_SETTINGS['MIN_ADVANCE_DAYS'])
            is_past_date = target_date < min_reservation_date
            available = check_date_availability(target_date, item, True, is_past_date)
            
            reason = None
            if not available:
                if Reservation.objects.filter(date=target_date, item=item, status__in=['adjusting', 'confirmed']).exists():
                    reason = 'already_reserved'
                elif is_past_date:
                    reason = 'past_date'
                else:
                    reason = 'unavailable'
            
            return JsonResponse({
                'available': available,
                'reason': reason
            })
            
        except (ValueError, json.JSONDecodeError, RentalItem.DoesNotExist):
            return JsonResponse({'available': False, 'error': 'Invalid request'})
    
    return JsonResponse({'available': False, 'error': 'Invalid method'})

def get_merged_calendar_data(request):
    """全物品をマージしたカレンダーデータを取得するAPI（最適化版）"""
    try:
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))
        
        # 有効な物品を取得
        active_items = list(RentalItem.objects.filter(is_active=True).values_list('id', flat=True))
        
        # 月の最初の日を作成
        target_date = date(year, month, 1)
        first_day_weekday = target_date.weekday()  # 0=月曜日, 6=日曜日
        
        # 日曜日を0にするため調整
        first_day_of_week = (first_day_weekday + 1) % 7
        
        # その月の日数を取得
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        days_in_month = (next_month_first - target_date).days
        
        # カレンダー表示範囲を計算
        start_date = target_date - timedelta(days=first_day_of_week)
        end_date = start_date + timedelta(days=6 * 7)  # 6週間分
        
        # 一括で予約データを取得（パフォーマンス最適化）
        reserved_dates = set(
            Reservation.objects.filter(
                date__range=(start_date, end_date),
                item_id__in=active_items,
                status__in=['adjusting', 'completed']
            ).values_list('date', 'item_id')
        )
        
        # 一括でカレンダー状態データを取得
        calendar_status_dict = {}
        calendar_statuses = CalendarStatus.objects.filter(
            date__range=(start_date, end_date),
            item_id__in=active_items
        ).values('date', 'item_id', 'is_available')
        
        for cs in calendar_statuses:
            calendar_status_dict[(cs['date'], cs['item_id'])] = cs['is_available']
        
        today = date.today()
        calendar_weeks = []
        
        for week in range(6):  # 最大6週間
            week_data = []
            for day in range(7):  # 日曜日から土曜日
                display_date = start_date + timedelta(days=week*7 + day)
                
                # 当月かどうかを判定
                is_current_month = display_date.month == month
                # MIN_ADVANCE_DAYSを考慮した予約可能日制限
                min_reservation_date = today + timedelta(days=settings.RESERVATION_SETTINGS['MIN_ADVANCE_DAYS'])
                is_past_date = display_date < min_reservation_date
                
                # 全物品での可用性をチェック（在庫ベース）
                is_any_available = False
                best_status = '✕'  # 最良のステータスを追跡（優先順位：◯ > △ > ✕）
                
                if not is_past_date and is_current_month:
                    # 日曜日（休業日）チェック
                    if display_date.weekday() == 6:  # 日曜日
                        is_any_available = False
                        best_status = '休'
                    else:
                        for item_id in active_items:
                            try:
                                item = RentalItem.objects.get(id=item_id)
                                item_status = item.get_status_for_date(display_date)
                                if item_status == '◯':
                                    is_any_available = True
                                    best_status = '◯'
                                    break  # ◯が見つかったら最優先
                                elif item_status == '△':
                                    is_any_available = True
                                    if best_status != '◯':
                                        best_status = '△'
                                # ✕の場合は何もしない（デフォルト）
                            except RentalItem.DoesNotExist:
                                continue
                
                # ステータステキストの設定
                if display_date.weekday() == 6 and is_current_month and not is_past_date:
                    status_text = '休'
                elif is_current_month and not is_past_date:
                    status_text = best_status
                else:
                    status_text = '-'
                
                week_data.append({
                    'date': display_date.strftime('%Y-%m-%d'),
                    'day': display_date.day,
                    'is_available': is_any_available or best_status == '△',  # △も予約可能として扱う
                    'is_current_month': is_current_month,
                    'is_past_date': is_past_date,
                    'status_text': status_text
                })
            calendar_weeks.append(week_data)
            
            # 当月の日付が全て表示されたら終了
            if (week + 1) * 7 >= first_day_of_week + days_in_month:
                break
        
        return JsonResponse({
            'success': True,
            'calendar_data': {
                'year': year,
                'month': month,
                'month_name': f'{year}年{month}月',
                'weeks': calendar_weeks
            }
        })
        
    except (ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid request'})

def get_available_items_for_date(request):
    """指定した日付に予約可能な物品リストを取得するAPI（最適化版）"""
    try:
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'success': False, 'error': 'Date parameter is required'})
        
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # 過去の日付はチェック不要
        if target_date < date.today():
            return JsonResponse({
                'success': True,
                'available_items': []
            })
        
        # 有効な物品を取得
        active_items = RentalItem.objects.filter(is_active=True)
        
        # 該当日に予約済みの物品IDを取得
        reserved_item_ids = set(
            Reservation.objects.filter(
                date=target_date,
                status__in=['adjusting', 'completed']
            ).values_list('item_id', flat=True)
        )
        
        # 該当日のカレンダー状態を一括取得
        calendar_status_dict = {}
        calendar_statuses = CalendarStatus.objects.filter(
            date=target_date,
            item__is_active=True
        ).values('item_id', 'is_available')
        
        for cs in calendar_statuses:
            calendar_status_dict[cs['item_id']] = cs['is_available']
        
        # 利用可能な物品をフィルタリング
        available_items = []
        for item in active_items:
            # 予約チェック
            if item.id in reserved_item_ids:
                continue
            
            # カレンダー状態チェック
            calendar_available = calendar_status_dict.get(item.id, True)
            if calendar_available:
                available_items.append({
                    'id': item.id,
                    'name': item.name
                })
        
        return JsonResponse({
            'success': True,
            'available_items': available_items
        })
        
    except (ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid date format'})

def get_disabled_dates(request, item_id):
    """指定された物品の予約不可日付を取得するAPI"""
    try:
        item = get_object_or_404(RentalItem, id=item_id, is_active=True)
        
        # 今日から1年後までの範囲で予約不可日付を取得
        today = date.today()
        end_date = today.replace(year=today.year + 1)
        
        disabled_dates = []
        
        # 確定済み予約の日付を取得
        confirmed_reservations = Reservation.objects.filter(
            item=item,
            status='confirmed',
            date__gte=today,
            date__lte=end_date
        ).values_list('date', flat=True)
        
        for reservation_date in confirmed_reservations:
            disabled_dates.append(reservation_date.strftime('%Y-%m-%d'))
        
        # CalendarStatusで利用不可に設定された日付も取得（予約済み以外）
        calendar_statuses = CalendarStatus.objects.filter(
            item=item,
            is_available=False,
            date__gte=today,
            date__lte=end_date
        ).exclude(
            date__in=confirmed_reservations
        ).values_list('date', flat=True)
        
        for status_date in calendar_statuses:
            disabled_dates.append(status_date.strftime('%Y-%m-%d'))
        
        return JsonResponse({
            'success': True,
            'disabled_dates': disabled_dates
        })
        
    except RentalItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})

def reservation_lookup(request):
    """予約確認・検索機能"""
    reservation = None
    error_message = None
    
    if request.method == "POST":
        confirmation_number = request.POST.get('confirmation_number', '').strip().upper()
        
        if confirmation_number:
            try:
                reservation = Reservation.objects.select_related('item').get(
                    confirmation_number=confirmation_number
                )
            except Reservation.DoesNotExist:
                error_message = "指定された予約確認番号の予約は見つかりませんでした"
        else:
            error_message = "予約確認番号を入力してください"
    
    context = {
        'reservation': reservation,
        'error_message': error_message
    }
    
    return render(request, "reservations/lookup.html", context)

def cancel_reservation(request, confirmation_number):
    """予約キャンセル機能"""
    try:
        reservation = Reservation.objects.get(confirmation_number=confirmation_number)
        
        if request.method == "POST":
            if reservation.can_cancel():
                if reservation.cancel():
                    # CalendarStatusも更新（予約不可から利用可能に戻す）
                    try:
                        calendar_status = CalendarStatus.objects.get(
                            date=reservation.date,
                            item=reservation.item
                        )
                        calendar_status.is_available = True
                        calendar_status.save()
                    except CalendarStatus.DoesNotExist:
                        pass
                    
                    return render(request, "reservations/cancel_success.html", {
                        'reservation': reservation
                    })
                else:
                    error_message = "予約のキャンセルに失敗しました"
            else:
                error_message = "この予約はキャンセルできません（予約日前日まで可能）"
        else:
            error_message = None
            
        context = {
            'reservation': reservation,
            'error_message': error_message,
            'can_cancel': reservation.can_cancel()
        }
        
        return render(request, "reservations/cancel_confirm.html", context)
        
    except Reservation.DoesNotExist:
        return render(request, "reservations/cancel_confirm.html", {
            'error_message': "指定された予約は見つかりませんでした"
        })

def privacy_policy(request):
    """プライバシーポリシー表示"""
    return render(request, 'reservations/privacy_policy.html')

def terms_of_service(request):
    """利用規約表示"""
    return render(request, 'reservations/terms.html')

def test_email(request):
    """テスト用：最新の予約でメール送信をテスト"""
    try:
        # 最新の予約を取得
        latest_reservation = Reservation.objects.latest('created_at')
        
        # メール送信をテスト
        send_reservation_emails(latest_reservation)
        
        return HttpResponse(f"テストメール送信完了: 予約番号 {latest_reservation.confirmation_number}")
        
    except Reservation.DoesNotExist:
        return HttpResponse("予約データが見つかりません")
    except Exception as e:
        return HttpResponse(f"メール送信エラー: {str(e)}")
