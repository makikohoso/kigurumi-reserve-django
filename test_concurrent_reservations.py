#!/usr/bin/env python
"""
同時予約の競合テストスクリプト
"""
import os
import django
import threading
import time
from datetime import date, timedelta

# Django環境のセットアップ
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from reservations.models import Reservation, RentalItem, CalendarStatus
from django.db import transaction

def create_test_reservation(item_id, test_date, thread_id):
    """テスト用予約作成（スレッドセーフテスト）"""
    try:
        from reservations.views import reserve_form
        
        # 簡易的な予約作成テスト
        with transaction.atomic():
            existing = Reservation.objects.select_for_update().filter(
                date=test_date,
                item_id=item_id,
                status='confirmed'
            ).first()
            
            if existing:
                print(f"Thread {thread_id}: 予約競合検出 - 既に予約済み")
                return False
            
            # 少し遅延を追加して競合をシミュレート
            time.sleep(0.1)
            
            reservation = Reservation.objects.create(
                name=f"テストユーザー{thread_id}",
                phone=f"090-{thread_id:04d}-{thread_id:04d}",
                email=f"test{thread_id}@example.com",
                date=test_date,
                item_id=item_id,
                status='confirmed'
            )
            
            print(f"Thread {thread_id}: 予約成功 - ID: {reservation.id}")
            return True
            
    except Exception as e:
        print(f"Thread {thread_id}: エラー - {str(e)}")
        return False

def test_concurrent_reservations():
    """同時予約テスト"""
    print("=== 同時予約競合テスト開始 ===")
    
    # テストデータの準備
    try:
        # テスト用アイテムを取得または作成
        item, created = RentalItem.objects.get_or_create(
            name="テスト用きぐるみ",
            defaults={'is_active': True}
        )
        
        test_date = date.today() + timedelta(days=7)
        print(f"テスト対象: {item.name}, 日付: {test_date}")
        
        # 既存の予約をクリア
        Reservation.objects.filter(item=item, date=test_date).delete()
        CalendarStatus.objects.filter(item=item, date=test_date).delete()
        
        # 同時に10個のスレッドで予約を試行
        threads = []
        results = []
        
        def thread_wrapper(thread_id):
            result = create_test_reservation(item.id, test_date, thread_id)
            results.append((thread_id, result))
        
        for i in range(10):
            thread = threading.Thread(target=thread_wrapper, args=(i+1,))
            threads.append(thread)
        
        # 全スレッドを開始
        for thread in threads:
            thread.start()
        
        # 全スレッドの完了を待機
        for thread in threads:
            thread.join()
        
        # 結果の確認
        successful_reservations = Reservation.objects.filter(
            item=item, 
            date=test_date,
            status='confirmed'
        ).count()
        
        print(f"\n=== テスト結果 ===")
        print(f"成功した予約数: {successful_reservations}")
        print(f"スレッド結果: {results}")
        
        if successful_reservations == 1:
            print("✅ テスト成功: 競合制御が正常に動作しています")
        else:
            print(f"❌ テスト失敗: {successful_reservations}件の予約が作成されました（1件であるべき）")
            
    except Exception as e:
        print(f"テスト実行エラー: {str(e)}")

if __name__ == "__main__":
    test_concurrent_reservations()