from django.db import models
from django.core.validators import RegexValidator
from django.conf import settings
from datetime import date
import uuid
import os

class RentalItem(models.Model):
    """レンタル物品（きぐるみの種類）"""
    name = models.CharField(max_length=100, unique=True)  # レンタル物品名
    is_active = models.BooleanField(default=True)  # 利用可能かどうか
    total_stock = models.PositiveIntegerField(default=1, verbose_name="総在庫数")  # 総在庫数
    warning_threshold = models.PositiveIntegerField(default=1, verbose_name="警告しきい値")  # 残り何個になったら△表示
    
    def get_available_stock_for_date(self, target_date):
        """指定日の利用可能在庫数を取得"""
        reserved_count = self.reservation_set.filter(
            date=target_date,
            status__in=['confirmed', 'pending']
        ).count()
        return max(0, self.total_stock - reserved_count)
    
    def is_available_for_date(self, target_date):
        """指定日に予約可能かチェック"""
        return self.get_available_stock_for_date(target_date) > 0
    
    def get_status_for_date(self, target_date):
        """指定日のステータス表示を取得（◯/△/✕）"""
        if not self.is_active:
            return '✕'
        
        available_stock = self.get_available_stock_for_date(target_date)
        if available_stock == 0:
            return '✕'
        elif available_stock <= self.warning_threshold:
            return '△'
        else:
            return '◯'
    
    def get_primary_image(self):
        """メイン画像を取得"""
        return self.images.filter(is_primary=True).first()
    
    def get_all_images(self):
        """全画像を順序付きで取得"""
        return self.images.all().order_by('order', 'id')
    
    def has_images(self):
        """画像があるかチェック"""
        return self.images.exists()
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "レンタル物品"
        verbose_name_plural = "レンタル物品"

def rental_item_image_path(instance, filename):
    """画像のアップロードパスを生成"""
    ext = filename.split('.')[-1]
    filename = f'{instance.item.id}_{instance.order}_{uuid.uuid4().hex[:8]}.{ext}'
    return f'rental_items/{filename}'

class RentalItemImage(models.Model):
    """レンタル物品画像"""
    item = models.ForeignKey(
        RentalItem,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name="レンタル物品"
    )
    image = models.ImageField(
        upload_to=rental_item_image_path,
        verbose_name="画像",
        help_text="推奨サイズ: 800x600px, 最大ファイルサイズ: 5MB"
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="代替テキスト",
        help_text="画像の説明（アクセシビリティ向上）"
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name="表示順序"
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name="メイン画像"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        verbose_name = "レンタル物品画像"
        verbose_name_plural = "レンタル物品画像"
        indexes = [
            models.Index(fields=['item', 'order']),
            models.Index(fields=['is_primary']),
        ]
    
    def save(self, *args, **kwargs):
        # メイン画像の重複防止
        if self.is_primary:
            RentalItemImage.objects.filter(
                item=self.item,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        
        super().save(*args, **kwargs)
        
        # 画像リサイズ処理
        if self.image and hasattr(self.image, 'path'):
            self.resize_image()
    
    def resize_image(self):
        """画像リサイズとサムネイル生成"""
        try:
            from PIL import Image
            img_path = self.image.path
            
            with Image.open(img_path) as img:
                # メイン画像のリサイズ (最大800x600)
                if img.height > 600 or img.width > 800:
                    img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                    img.save(img_path, quality=85, optimize=True)
                
                # サムネイル生成 (150x150)
                thumb_path = self.get_thumbnail_path()
                os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
                
                thumb = img.copy()
                thumb.thumbnail((150, 150), Image.Resampling.LANCZOS)
                thumb.save(thumb_path, quality=85, optimize=True)
        except Exception as e:
            print(f"Image processing error: {e}")
    
    def get_thumbnail_path(self):
        """サムネイルパスを取得"""
        if not self.image:
            return ''
        img_path = self.image.path
        dir_name = os.path.dirname(img_path)
        base_name = os.path.basename(img_path)
        name, ext = os.path.splitext(base_name)
        return os.path.join(dir_name, 'thumbs', f'{name}_thumb{ext}')
    
    def get_thumbnail_url(self):
        """サムネイルURLを取得"""
        if self.image:
            img_url = self.image.url
            dir_name = os.path.dirname(img_url)
            base_name = os.path.basename(img_url)
            name, ext = os.path.splitext(base_name)
            return f'{dir_name}/thumbs/{name}_thumb{ext}'
        return ''
    
    def __str__(self):
        primary_text = " (メイン)" if self.is_primary else ""
        return f"{self.item.name} - 画像{self.order}{primary_text}"

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
