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
    try:
        # 予約者へのメール送信
        send_customer_email(reservation)
        
        # 管理者へのメール送信
        send_admin_email(reservation)
        
        logger.info(f"予約メール送信完了: 予約番号 {reservation.confirmation_number}")
        
    except Exception as e:
        logger.error(f"メール送信エラー: {str(e)}")
        # メール送信失敗しても予約自体は成功として扱う


def send_customer_email(reservation):
    """予約者へのメール送信"""
    subject = f"【予約完了】きぐるみレンタル予約 - {reservation.confirmation_number}"
    
    # テキストメール内容
    message = f"""
{reservation.name} 様

きぐるみレンタル予約システムをご利用いただき、ありがとうございます。
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

きぐるみレンタル予約システム
"""

    # メール送信
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[reservation.email],
        fail_silently=False,
    )


def send_admin_email(reservation):
    """管理者へのメール送信"""
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
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.ADMIN_EMAIL],
        fail_silently=False,
    )