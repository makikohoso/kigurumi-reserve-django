from django.shortcuts import render, get_object_or_404
from .models import Reservation, RentalItem
from datetime import datetime

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
    return render(request, "reservations/form.html", {"items": items})
