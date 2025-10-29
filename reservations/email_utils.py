from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_reservation_emails(reservation):
    """
    予約完了時にメールを送信する
    - 予約者にメール送信
    - 管理者にメール送信
    """
    logger.info(f"=== メール送信処理開始: 予約番号 {reservation.confirmation_number} ===")
    try:
        from .models import EmailSettings, AdminEmail

        # データベースから設定を取得
        email_settings = EmailSettings.get_current_settings()
        logger.info(f"メール設定取得完了: from={email_settings.from_email}")
        
        # 予約者へのメール送信
        if email_settings.send_customer_notification:
            logger.info(f"顧客メール送信開始: to={reservation.email}")
            send_customer_email(reservation, email_settings)
            logger.info(f"顧客メール送信完了: to={reservation.email}")
        
        # 管理者へのメール送信
        if email_settings.send_admin_notification:
            admin_emails = list(AdminEmail.get_active_emails())
            logger.info(f"取得した通知先メールアドレス: {admin_emails} (件数: {len(admin_emails)})")
            if admin_emails:
                send_admin_email(reservation, admin_emails, email_settings)
            else:
                logger.warning("有効な通知先メールアドレスが設定されていません")
        
        logger.info(f"予約メール送信完了: 予約番号 {reservation.confirmation_number}")
        
    except Exception as e:
        logger.error(f"メール送信エラー: {str(e)}")
        # メール送信失敗しても予約自体は成功として扱う


def send_customer_email(reservation, email_settings):
    """予約者へのメール送信"""
    subject = f"【予約完了】{email_settings.from_name} - {reservation.confirmation_number}"
    
    # テキストメール内容
    message = f"""
{reservation.name} 様

{email_settings.from_name}をご利用いただき、ありがとうございます。
予約が完了いたしました。

■ 予約内容
予約確認番号: {reservation.confirmation_number}
お名前: {reservation.name} 様
電話番号: {reservation.phone}
メールアドレス: {reservation.email}
予約日: {reservation.date.strftime('%Y年%m月%d日 (%A)')}
レンタル物品: {reservation.item.name}
{"備考: " + reservation.notes if reservation.notes else ""}

■ ご注意
・この時点では仮予約となります
・管理者が内容を確認後、正式に予約確定となります
・予約状況は予約状況確認ページからご確認いただけます
・予約のキャンセルは予約日の前日まで可能です

何かご不明な点がございましたら、お気軽にお問い合わせください。

{email_settings.from_name}
"""

    # メール送信
    send_mail(
        subject=subject,
        message=message,
        from_email=email_settings.get_from_email(),
        recipient_list=[reservation.email],
        fail_silently=True,  # メール送信失敗でも予約処理は続行
    )


def send_admin_email(reservation, admin_emails, email_settings):
    """通知先へのメール送信（複数の通知先に送信）"""
    logger.info(f"通知先メール送信開始: ADMIN_EMAILS = {admin_emails}")
    subject = f"【新規予約】{reservation.item.name} - {reservation.date.strftime('%m/%d')} - {reservation.name}様"
    
    # テキストメール内容
    message = f"""
新しい予約が入りました。

■ 予約内容
予約確認番号: {reservation.confirmation_number}
予約日時: {reservation.created_at.strftime('%Y年%m月%d日 %H:%M:%S')}

■ 予約者情報
お名前: {reservation.name} 様
電話番号: {reservation.phone}
メールアドレス: {reservation.email}

■ 予約詳細
予約日: {reservation.date.strftime('%Y年%m月%d日 (%A)')}
レンタル物品: {reservation.item.name}
ステータス: {reservation.get_status_display()}
{"備考: " + reservation.notes if reservation.notes else ""}

管理画面から予約の確認・承認を行ってください。
"""

    # メール送信
    logger.info(f"通知先メール送信実行: recipient_list={admin_emails}")
    send_mail(
        subject=subject,
        message=message,
        from_email=email_settings.get_from_email(),
        recipient_list=admin_emails,
        fail_silently=True,  # メール送信失敗でも予約処理は続行
    )
    logger.info(f"通知先メール送信完了: {reservation.confirmation_number}, 送信先: {len(admin_emails)}件")