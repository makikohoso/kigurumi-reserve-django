from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Reservation, RentalItem, CalendarStatus
from datetime import datetime, date, timedelta

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
                
                Reservation.objects.create(name=name, date=date_obj, item=item)
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
