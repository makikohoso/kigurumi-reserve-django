from django.core.management.base import BaseCommand
from reservations.models import Reservation, CalendarStatus

class Command(BaseCommand):
    help = '既存の予約データをカレンダーステータスと連動させる'

    def handle(self, *args, **options):
        # 有効な予約（物品が設定されている）のみを対象
        valid_reservations = Reservation.objects.filter(item__isnull=False)
        
        self.stdout.write(f'処理対象の予約数: {valid_reservations.count()}')
        
        updated_count = 0
        created_count = 0
        
        for reservation in valid_reservations:
            # 対応するカレンダーステータスを取得または作成
            calendar_status, created = CalendarStatus.objects.get_or_create(
                date=reservation.date,
                item=reservation.item,
                defaults={'is_available': False}
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    f'作成: {reservation.date} - {reservation.item.name} → 予約不可'
                )
            else:
                # 既存のレコードがある場合、予約不可に更新
                if calendar_status.is_available:
                    calendar_status.is_available = False
                    calendar_status.save()
                    updated_count += 1
                    self.stdout.write(
                        f'更新: {reservation.date} - {reservation.item.name} → 予約不可'
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'完了: 新規作成 {created_count}件, 更新 {updated_count}件'
            )
        )