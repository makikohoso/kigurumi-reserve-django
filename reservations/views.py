from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import Reservation, RentalItem, CalendarStatus
from datetime import datetime, date, timedelta
import json
import time
from django.conf import settings

def validate_reservation_business_rules(date_obj, item, user_ip=None, phone=None):
    """予約ビジネスルールの検証"""
    errors = []
    now = timezone.now()
    
    # 1. 予約期間制限チェック
    max_advance = timedelta(days=settings.RESERVATION_SETTINGS['MAX_ADVANCE_DAYS'])
    min_advance = timedelta(hours=settings.RESERVATION_SETTINGS['MIN_ADVANCE_HOURS'])
    
    if date_obj > (now.date() + max_advance):
        errors.append(f"予約は{settings.RESERVATION_SETTINGS['MAX_ADVANCE_DAYS']}日前までしかできません")
    
    if date_obj <= (now + min_advance).date():
        errors.append(f"予約は{settings.RESERVATION_SETTINGS['MIN_ADVANCE_HOURS']}時間前までに行ってください")
    
    # 2. 同日同一ユーザーの予約制限（電話番号ベース）
    if phone:
        today_reservations = Reservation.objects.filter(
            phone=phone,
            created_at__date=now.date(),
            status='confirmed'
        ).count()
        
        if today_reservations >= settings.RESERVATION_SETTINGS['MAX_RESERVATIONS_PER_USER_PER_DAY']:
            errors.append(f"1日あたり{settings.RESERVATION_SETTINGS['MAX_RESERVATIONS_PER_USER_PER_DAY']}件までしか予約できません")
    
    # 3. 営業時間・営業日チェック（基本的な例）
    if date_obj.weekday() == 6:  # 日曜日
        errors.append("日曜日は休業日のため予約できません")
    
    return errors

def check_rate_limiting(user_ip):
    """レート制限チェック（簡易版）"""
    if not settings.RESERVATION_SETTINGS['ENABLE_RATE_LIMITING']:
        return []
    
    # セッションベースの簡易レート制限（実際の実装ではRedisやCacheを使用推奨）
    hour_ago = timezone.now() - timedelta(hours=1)
    
    # IPベースの予約試行回数をチェック（実際にはより複雑な実装が必要）
    # ここでは簡易実装として省略
    
    return []

def check_date_availability(target_date, item, is_current_month=True, is_past_date=False):
    """日付の予約可能性を効率的にチェック"""
    # 過去の日付や当月以外は利用不可
    if is_past_date or not is_current_month:
        return False
    
    # 予約の存在チェック（優先）
    if Reservation.objects.filter(
        date=target_date, 
        item=item, 
        status='confirmed'
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
        
        # 基本バリデーション
        errors = []
        if not name:
            errors.append("名前を入力してください")
        if not phone:
            errors.append("電話番号を入力してください")
        if not email:
            errors.append("メールアドレスを入力してください")
        if not date_str:
            errors.append("予約日を選択してください")
        if not item_id:
            errors.append("レンタル物品を選択してください")
        
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
                    # トランザクション処理で同時予約競合を回避
                    try:
                        with transaction.atomic():
                            # 予約可能性の最終チェック（ロック付き）
                            existing_reservation = Reservation.objects.select_for_update().filter(
                                date=date_obj,
                                item=item,
                                status='confirmed'
                            ).first()
                            
                            if existing_reservation:
                                errors.append("申し訳ございませんが、この日時は既に予約済みです")
                                raise ValidationError("予約競合")
                            
                            # CalendarStatusもロックして確認
                            calendar_status = CalendarStatus.objects.select_for_update().filter(
                                date=date_obj,
                                item=item
                            ).first()
                            
                            if calendar_status and not calendar_status.is_available:
                                errors.append("この日時は予約できません")
                                raise ValidationError("利用不可日")
                            
                            # 予約を作成
                            reservation = Reservation.objects.create(
                                name=name, 
                                phone=phone,
                                email=email,
                                date=date_obj, 
                                item=item,
                                notes=notes
                            )
                            
                            # CalendarStatusを更新または作成
                            if calendar_status:
                                calendar_status.is_available = False
                                calendar_status.save()
                            else:
                                CalendarStatus.objects.create(
                                    date=date_obj,
                                    item=item,
                                    is_available=False
                                )
                            
                            return render(request, "reservations/thanks.html", {
                                "reservation": reservation
                            })
                            
                    except (ValidationError, IntegrityError):
                        # 競合やバリデーションエラーの場合はerrorsに追加済み
                        pass
                        
            except ValueError:
                errors.append("無効な日付形式です")
                
        if errors:
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

def reservations_list(request):
    """予約一覧表示（予約者向け）"""
    # 予約を日付順で取得（名前は含めない）
    reservations = Reservation.objects.select_related('item').order_by('date', 'item__name')
    
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
                is_past_date = display_date < today
                
                # 予約状況を効率的にチェック
                is_available = check_date_availability(display_date, item, is_current_month, is_past_date)
                
                week_data.append({
                    'date': display_date.strftime('%Y-%m-%d'),
                    'day': display_date.day,
                    'is_available': is_available,
                    'is_current_month': is_current_month,
                    'is_past_date': is_past_date,
                    'status_text': '◯' if is_available else ('✗' if is_current_month and not is_past_date else '-')
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
            is_past_date = target_date < date.today()
            available = check_date_availability(target_date, item, True, is_past_date)
            
            reason = None
            if not available:
                if Reservation.objects.filter(date=target_date, item=item, status='confirmed').exists():
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
