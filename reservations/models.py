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

class Reservation(models.Model):
    name = models.CharField(max_length=100)  # 名前を文字列で保存
    date = models.DateField(default=date.today)  # 予約日
    item = models.ForeignKey(RentalItem, on_delete=models.CASCADE, null=True, blank=True)  # レンタル物品
    created_at = models.DateTimeField(auto_now_add=True, null=True)  # 予約日時（自動）

    def __str__(self):
        item_name = self.item.name if self.item else "未設定"
        return f"{self.name} - {item_name} - {self.date}"
