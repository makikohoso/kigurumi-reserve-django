from django.db import models
from django.core.validators import RegexValidator
from datetime import date
import uuid

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
    RESERVATION_STATUS_CHOICES = [
        ('confirmed', '確定'),
        ('cancelled', 'キャンセル'),
        ('completed', '利用完了'),
    ]
    
    # 基本情報
    confirmation_number = models.CharField(
        max_length=12, 
        unique=True,
        editable=False,
        help_text="予約確認番号（自動生成）",
        blank=True
    )
    name = models.CharField(max_length=100, verbose_name="予約者名")
    
    # 連絡先情報
    phone_regex = RegexValidator(
        regex=r'^[0-9\-]{10,15}$', 
        message="電話番号は10-15桁の数字とハイフンで入力してください"
    )
    phone = models.CharField(
        validators=[phone_regex], 
        max_length=15, 
        verbose_name="電話番号",
        help_text="例: 090-1234-5678",
        default="000-0000-0000"
    )
    email = models.EmailField(
        verbose_name="メールアドレス",
        help_text="予約確認メール送信用",
        default="noreply@example.com"
    )
    
    # 予約詳細
    date = models.DateField(verbose_name="予約日")
    item = models.ForeignKey(
        RentalItem, 
        on_delete=models.CASCADE, 
        verbose_name="レンタル物品",
        null=True, blank=True
    )
    
    # ステータス管理
    status = models.CharField(
        max_length=20,
        choices=RESERVATION_STATUS_CHOICES,
        default='confirmed',
        verbose_name="予約ステータス"
    )
    
    # タイムスタンプ
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name="予約日時")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新日時")
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name="キャンセル日時")
    
    # 備考
    notes = models.TextField(blank=True, verbose_name="備考", help_text="特記事項があれば記入")

    class Meta:
        verbose_name = "予約"
        verbose_name_plural = "予約"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['confirmation_number']),
            models.Index(fields=['date', 'item']),
            models.Index(fields=['status']),
        ]

    def save(self, *args, **kwargs):
        if not self.confirmation_number or self.confirmation_number == "R000000000":
            self.confirmation_number = self.generate_confirmation_number()
        super().save(*args, **kwargs)

    def generate_confirmation_number(self):
        """予約確認番号を生成（例: R240827001）"""
        import random
        from django.utils import timezone
        
        # 既存の予約番号と重複しないように生成
        while True:
            date_str = timezone.now().strftime('%y%m%d')
            random_num = random.randint(100, 999)
            confirmation_number = f"R{date_str}{random_num}"
            
            if not Reservation.objects.filter(confirmation_number=confirmation_number).exists():
                return confirmation_number

    def can_cancel(self):
        """キャンセル可能かチェック（予約日の前日まで）"""
        from django.utils import timezone
        if self.status != 'confirmed':
            return False
        return self.date > timezone.now().date()

    def cancel(self):
        """予約をキャンセル"""
        if self.can_cancel():
            from django.utils import timezone
            self.status = 'cancelled'
            self.cancelled_at = timezone.now()
            self.save()
            return True
        return False

    def __str__(self):
        return f"[{self.confirmation_number}] {self.name} - {self.item.name} - {self.date}"
