from django.contrib import admin
from django.template.response import TemplateResponse
from django.urls import path
from django.http import JsonResponse
from .models import Reservation, RentalItem, CalendarStatus
from datetime import date, timedelta
import json

@admin.register(RentalItem)
class RentalItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    list_editable = ('is_active',)  # 一覧画面で直接編集可能
    search_fields = ('name',)
    list_filter = ('is_active',)

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'date', 'name', 'created_at')  # テーブルに表示するフィールド
    list_filter = ('date', 'item', 'created_at')  # 右側のフィルター
    search_fields = ('name',)  # 検索可能フィールド
    ordering = ('-created_at', 'name')  # 並び順（新しい予約日時順、名前順）

@admin.register(CalendarStatus)
class CalendarStatusAdmin(admin.ModelAdmin):
    list_display = ('date', 'item', 'is_available')
    list_filter = ('item', 'is_available', 'date')
    change_list_template = 'admin/calendarstatus/change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('calendar-management/', 
                 self.admin_site.admin_view(self.calendar_management_view), 
                 name='calendar_management'),
            path('update-calendar-status/', 
                 self.admin_site.admin_view(self.update_calendar_status), 
                 name='update_calendar_status'),
        ]
        return custom_urls + urls
    
    def calendar_management_view(self, request):
        """スプレッドシート風のカレンダー管理画面"""
        # デフォルトは今月
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))
        
        # その月の1日を取得
        target_date = date(year, month, 1)
        
        # その月の日数を取得
        if month == 12:
            next_month_first = date(year + 1, 1, 1)
        else:
            next_month_first = date(year, month + 1, 1)
        days_in_month = (next_month_first - target_date).days
        
        # アクティブなレンタル物品を取得
        items = RentalItem.objects.filter(is_active=True).order_by('name')
        
        # その月の日付リストを生成
        dates = []
        for day in range(1, days_in_month + 1):
            dates.append(date(year, month, day))
        
        # カレンダーステータスデータを取得
        calendar_data = {}
        for item in items:
            calendar_data[item.id] = {}
            for target_date in dates:
                try:
                    status = CalendarStatus.objects.get(date=target_date, item=item)
                    calendar_data[item.id][target_date.day] = status.is_available
                except CalendarStatus.DoesNotExist:
                    calendar_data[item.id][target_date.day] = True  # デフォルトは利用可能
        
        context = {
            'year': year,
            'month': month,
            'month_name': f'{year}年{month}月',
            'items': items,
            'dates': dates,
            'calendar_data': json.dumps(calendar_data),  # JSONでテンプレートに渡す
            'title': 'カレンダー管理 - スプレッドシート形式',
            'opts': self.model._meta,
        }
        
        return TemplateResponse(request, 'admin/calendar_management.html', context)
    
    def update_calendar_status(self, request):
        """AJAX でカレンダーの状態を更新"""
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                year = int(data['year'])
                month = int(data['month'])
                day = int(data['day'])
                item_id = int(data['item_id'])
                is_available = bool(data['is_available'])
                
                target_date = date(year, month, day)
                item = RentalItem.objects.get(id=item_id)
                
                status, created = CalendarStatus.objects.get_or_create(
                    date=target_date,
                    item=item,
                    defaults={'is_available': is_available}
                )
                
                if not created:
                    status.is_available = is_available
                    status.save()
                
                return JsonResponse({
                    'success': True,
                    'is_available': is_available,
                    'status_text': '◯' if is_available else '✗'
                })
                
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})
        
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
