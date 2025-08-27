from django.contrib import admin
from .models import Reservation, RentalItem

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
