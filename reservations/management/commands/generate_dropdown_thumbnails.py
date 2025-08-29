from django.core.management.base import BaseCommand
from reservations.models import RentalItemImage
import os
from PIL import Image


class Command(BaseCommand):
    help = '既存の画像にドロップダウン用48x48pxサムネイルを生成'

    def handle(self, *args, **options):
        images = RentalItemImage.objects.all()
        
        self.stdout.write(f'処理対象の画像数: {images.count()}')
        
        success_count = 0
        error_count = 0
        
        for image in images:
            try:
                if image.image and hasattr(image.image, 'path') and os.path.exists(image.image.path):
                    self.generate_dropdown_thumbnail(image)
                    success_count += 1
                    self.stdout.write(f'✓ {image.item.name} - {image.id}')
                else:
                    self.stdout.write(
                        self.style.WARNING(f'スキップ: {image.item.name} - {image.id} (画像ファイルが見つからない)')
                    )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'エラー: {image.item.name} - {image.id}: {str(e)}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'完了: 成功 {success_count}件, エラー {error_count}件'
            )
        )
    
    def generate_dropdown_thumbnail(self, image_instance):
        """48x48pxドロップダウン用サムネイルを生成"""
        try:
            img_path = image_instance.image.path
            
            with Image.open(img_path) as img:
                # ドロップダウン用サムネイル生成 (48x48)
                dropdown_path = image_instance.get_dropdown_thumbnail_path()
                os.makedirs(os.path.dirname(dropdown_path), exist_ok=True)
                
                dropdown = img.copy()
                dropdown.thumbnail((48, 48), Image.Resampling.LANCZOS)
                dropdown.save(dropdown_path, quality=85, optimize=True)
                
        except Exception as e:
            raise Exception(f"ドロップダウンサムネイル生成エラー: {e}")