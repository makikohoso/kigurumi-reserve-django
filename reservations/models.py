from django.db import models
from datetime import date

class RentalItem(models.Model):
    """レンタル物品（きぐるみの種類）"""
    name = models.CharField(max_length=100, unique=True)  # レンタル物品名
    is_active = models.BooleanField(default=True)  # 利用可能かどうか
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "レンタル物品"
        verbose_name_plural = "レンタル物品"

class CalendarStatus(models.Model):
    """カレンダーの各日付とアイテムの◯✗状態を管理"""
    date = models.DateField()
    item = models.ForeignKey(RentalItem, on_delete=models.CASCADE)
    is_available = models.BooleanField(default=True)  # True: ◯, False: ✗
    
    def __str__(self):
        status = "◯" if self.is_available else "✗"
        return f"{self.date} - {self.item.name}: {status}"
    
    class Meta:
        unique_together = ('date', 'item')  # 日付とアイテムの組み合わせは一意
        verbose_name = "カレンダー状態"
        verbose_name_plural = "カレンダー状態"

class Reservation(models.Model):
    name = models.CharField(max_length=100)  # 名前を文字列で保存
    date = models.DateField(default=date.today)  # 予約日
    item = models.ForeignKey(RentalItem, on_delete=models.CASCADE, null=True, blank=True)  # レンタル物品
    created_at = models.DateTimeField(auto_now_add=True, null=True)  # 予約日時（自動）

    def __str__(self):
        item_name = self.item.name if self.item else "未設定"
        return f"{self.name} - {item_name} - {self.date}"
