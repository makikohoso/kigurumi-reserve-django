# 予約システム

Django で構築された予約管理システムです。

## 主な機能

### 🎯 予約管理
- ユーザーフレンドリーな予約フォーム
- リアルタイム在庫状況表示（◯/△/✕）
- 予約確認番号の自動生成
- 予約ステータス管理（調整中/完了/キャンセル）

### 📧 メール通知
- 予約確認メールの自動送信（顧客・管理者）
- カスタマイズ可能な送信者設定
- 複数の管理者メールアドレス対応

### 🖼️ 画像管理
- 複数画像のアップロード・管理
- 自動サムネイル生成（150x150, 160x160）
- メイン画像の設定
- レスポンシブ対応の画像表示
- Retina対応の高解像度表示

### 🔐 セキュリティ機能
- 包括的なログ・監査システム
- セキュリティイベント検知
- レート制限（設定可能）
- SQLインジェクション・XSS対策
- CSRF保護

### ⚡ パフォーマンス最適化
- データベースインデックス最適化
- 同時予約の競合制御
- 効率的な在庫計算
- セッション管理

## システム要件

- Python 3.11+
- Django 5.2.16
- SQLite3（開発環境）/ PostgreSQL（本番推奨）
- Pillow（画像処理）

## インストール・セットアップ

### 1. リポジトリのクローン
```bash
git clone https://github.com/makikohoso/kigurumi-reserve-django.git
cd kigurumi-reserve-django
```

### 2. 仮想環境の作成
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
```

### 3. 依存関係のインストール
```bash
pip install -r requirements.txt
```

### 4. 環境設定
```bash
# 環境変数ファイルのコピー
cp .env.example .env

# .env ファイルを編集し、以下の設定を行う：
# - SECRET_KEY: Django シークレットキー
# - EMAIL_HOST_USER: メール送信用アカウント
# - EMAIL_HOST_PASSWORD: メールパスワード
# - ADMIN_EMAIL: 管理者メールアドレス
```

#### 詳細なメール設定

**ロリポップメール使用の場合:**
```bash
# .env ファイル設定例
EMAIL_HOST_USER=noreply@yourdomain.com
EMAIL_HOST_PASSWORD=your_email_password
ADMIN_EMAIL=admin@yourdomain.com

# settings.py では以下が設定済み
EMAIL_HOST=smtp.lolipop.jp
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

**Gmail使用の場合:**
```bash
# .env ファイル設定例
EMAIL_HOST_USER=your_gmail@gmail.com
EMAIL_HOST_PASSWORD=your_app_password  # Googleアプリパスワード
ADMIN_EMAIL=admin@gmail.com

# settings.py で以下を変更
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

**メール送信のテスト:**
```bash
# Django shellでメール送信テスト
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('テスト', 'メール送信テストです', 'noreply@yourdomain.com', ['test@example.com'])
```

### 5. データベースのセットアップ
```bash
# マイグレーションの実行
python manage.py migrate

# 管理者ユーザーの作成
python manage.py createsuperuser

# 静的ファイルの収集
python manage.py collectstatic
```

### 6. 初期データの投入（オプション）
```bash
# ログディレクトリの作成
mkdir -p logs

# サムネイル生成（既存画像がある場合）
python manage.py generate_dropdown_thumbnails
```

#### デモデータの使用方法

**デモデータの投入:**
```bash
# demo_data.jsonからデモデータを読み込み
python manage.py loaddata demo_data.json
```

**デモデータの内容:**
- レンタル物品A〜E（5件の物品データ）
- 各物品に画像データが含まれています
- 予約状況確認のサンプルデータとして活用

**カスタムデモデータの作成:**
```bash
# 現在のデータをエクスポート
python manage.py dumpdata reservations.RentalItem reservations.RentalItemImage --indent 2 > my_demo_data.json

# カスタムデータの読み込み
python manage.py loaddata my_demo_data.json
```

**デモデータのリセット:**
```bash
# 既存データの削除（注意：全データが削除されます）
python manage.py flush
python manage.py migrate
python manage.py loaddata demo_data.json
```

## 開発サーバーの起動

```bash
python manage.py runserver
```

アクセス URL:
- フロントエンド: http://127.0.0.1:8000/
- 管理画面: http://127.0.0.1:8000/admin/

## テスト実行

```bash
# 全テスト実行
python manage.py test

# 同時予約の競合テスト
python test_concurrent_reservations.py
```

## 設定・カスタマイズ

### メール設定
管理画面 > メール設定から以下を設定：
- 送信者名・メールアドレス
- 顧客・管理者への通知オン/オフ
- 管理者メールアドレス一覧

### ビジネスルール設定
`config/settings.py` の `RESERVATION_SETTINGS` で調整：
```python
RESERVATION_SETTINGS = {
    'MAX_ADVANCE_DAYS': 90,        # 最大予約可能日数
    'MIN_ADVANCE_DAYS': 5,         # 最小予約日数
    'MAX_RESERVATIONS_PER_USER_PER_DAY': 10,  # 1日あたり予約上限
    'RESERVATION_TIMEOUT_MINUTES': 10,         # 予約タイムアウト
    'ENABLE_RATE_LIMITING': False,             # レート制限
    'RATE_LIMIT_PER_HOUR': 10,                # 時間あたり予約試行上限
}
```

## 運用・保守

### ログファイル
- `logs/audit.log`: 予約アクティビティログ
- `logs/security.log`: セキュリティイベントログ

### 定期メンテナンス
- ログローテーション（自動：10MB毎、5世代保持）
- 古い予約データのクリーンアップ（手動）
- 画像ファイルの最適化

### 監視項目
- 異常なアクセスパターン（security.log）
- 予約失敗率（audit.log）
- データベースパフォーマンス
- ディスク容量（画像・ログファイル）

## トラブルシューティング

### よくある問題
1. **メール送信失敗**: EMAIL_HOST_USER/PASSWORD の設定確認
2. **画像アップロード失敗**: MEDIA_ROOT の権限確認
3. **予約競合エラー**: データベースロック・在庫数の確認

### デバッグモード
開発時は `.env` ファイルで `DEBUG=True` に設定

### パフォーマンス問題
- データベースクエリの最適化
- 画像サイズの確認（推奨: 800x600px以下）
- ログファイルサイズの確認

## セキュリティ

### 本番環境での注意点
- `DEBUG=False` に設定
- `SECRET_KEY` を安全に生成・管理
- HTTPS の有効化
- セキュリティヘッダーの設定
- 定期的なセキュリティアップデート

### 監査ログ
すべての予約アクティビティとセキュリティイベントがログに記録されます。

## ライセンス

このプロジェクトは MIT ライセンスの下で配布されています。

---

## 開発者向け情報

### アーキテクチャ
- **フロントエンド**: Django テンプレート + Tailwind CSS
- **バックエンド**: Django 5.2 + SQLite/PostgreSQL
- **画像処理**: Pillow
- **メール送信**: Django Email Framework

### コードスタイル
- PEP 8 準拠
- 日本語コメント・ドキュメンテーション
- 包括的なテストカバレッジ

### 貢献方法
1. Issue の作成・確認
2. フィーチャーブランチの作成
3. テストの実装・実行
4. プルリクエストの作成