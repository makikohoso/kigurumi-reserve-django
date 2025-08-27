from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Reservation, RentalItem, CalendarStatus
from datetime import datetime, date, timedelta
import json

def reserve_form(request):
    if request.method == "POST":
        name = request.POST.get("name")
        date_str = request.POST.get("date")
        item_id = request.POST.get("item")
        
        if name and date_str and item_id:
            try:
                # 日付文字列を日付オブジェクトに変換
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                # レンタル物品を取得
                item = get_object_or_404(RentalItem, id=item_id, is_active=True)
                
                # 予約を作成
                Reservation.objects.create(name=name, date=date_obj, item=item)
                
                # 予約された日付・物品の組み合わせを予約不可に設定
                calendar_status, created = CalendarStatus.objects.get_or_create(
                    date=date_obj,
                    item=item,
                    defaults={'is_available': False}
                )
                
                # 既にレコードが存在する場合は予約不可に更新
                if not created:
                    calendar_status.is_available = False
                    calendar_status.save()
                
                return render(request, "reservations/thanks.html", {
                    "name": name, 
                    "date": date_obj,
                    "item": item
                })
            except ValueError:
                # 無効な日付形式の場合
                items = RentalItem.objects.filter(is_active=True)
                return render(request, "reservations/form.html", {
                    "items": items,
                    "error": "無効な日付形式です"
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
                
                # 予約が既に存在するかチェック（優先判定）
                reservation_exists = Reservation.objects.filter(
                    date=display_date, 
                    item=item
                ).exists()
                
                # 予約が存在する場合は必ず利用不可
                if reservation_exists:
                    is_available = False
                else:
                    # 予約がない場合、CalendarStatusをチェック
                    try:
                        status = CalendarStatus.objects.get(date=display_date, item=item)
                        is_available = status.is_available and is_current_month and not is_past_date
                    except CalendarStatus.DoesNotExist:
                        # CalendarStatusがない場合は、当月で過去日でなければ利用可能
                        is_available = is_current_month and not is_past_date
                
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
            
            # 予約が既に存在するかチェック（優先判定）
            reservation_exists = Reservation.objects.filter(
                date=target_date, 
                item=item
            ).exists()
            
            if reservation_exists:
                return JsonResponse({'available': False, 'reason': 'already_reserved'})
            
            # CalendarStatusをチェック
            try:
                status = CalendarStatus.objects.get(date=target_date, item=item)
                available = status.is_available
            except CalendarStatus.DoesNotExist:
                # CalendarStatusがない場合は、過去の日付でなければ利用可能
                available = target_date >= date.today()
            
            return JsonResponse({'available': available})
            
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
        
        # 予約済みの日付を取得
        reservations = Reservation.objects.filter(
            item=item,
            date__gte=today,
            date__lte=end_date
        ).values_list('date', flat=True)
        
        for reservation_date in reservations:
            disabled_dates.append(reservation_date.strftime('%Y-%m-%d'))
        
        # CalendarStatusで利用不可に設定された日付も取得
        calendar_statuses = CalendarStatus.objects.filter(
            item=item,
            is_available=False,
            date__gte=today,
            date__lte=end_date
        ).values_list('date', flat=True)
        
        for status_date in calendar_statuses:
            date_str = status_date.strftime('%Y-%m-%d')
            if date_str not in disabled_dates:
                disabled_dates.append(date_str)
        
        return JsonResponse({
            'success': True,
            'disabled_dates': disabled_dates
        })
        
    except RentalItem.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Item not found'})
