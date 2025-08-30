import logging
from django.utils import timezone
from django.conf import settings

# ログ設定
audit_logger = logging.getLogger('audit')
security_logger = logging.getLogger('security')

def get_client_ip(request):
    """クライアントIPアドレスを取得"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def log_reservation_activity(request, action, reservation_id=None, details=None):
    """予約関連アクティビティのログ記録"""
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    log_data = {
        'timestamp': timezone.now().isoformat(),
        'ip': client_ip,
        'user_agent': user_agent,
        'action': action,
        'reservation_id': reservation_id,
        'details': details,
        'session_key': request.session.session_key
    }
    
    audit_logger.info(
        f"RESERVATION_ACTIVITY IP:{client_ip} ACTION:{action} "
        f"RESERVATION_ID:{reservation_id} DETAILS:{details} "
        f"SESSION:{request.session.session_key[:10]}... "
        f"TIMESTAMP:{timezone.now()}"
    )

def log_security_event(request, event_type, details=None, level='warning'):
    """セキュリティイベントのログ記録"""
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    log_data = {
        'timestamp': timezone.now().isoformat(),
        'ip': client_ip,
        'user_agent': user_agent,
        'event_type': event_type,
        'details': details,
        'session_key': request.session.session_key
    }
    
    log_message = (
        f"SECURITY_EVENT TYPE:{event_type} IP:{client_ip} "
        f"DETAILS:{details} USER_AGENT:{user_agent} "
        f"TIMESTAMP:{timezone.now()}"
    )
    
    if level == 'warning':
        security_logger.warning(log_message)
    elif level == 'error':
        security_logger.error(log_message)
    else:
        security_logger.info(log_message)

def log_validation_error(request, field_name, error_type, value=None):
    """バリデーションエラーのログ記録"""
    details = f"FIELD:{field_name} ERROR_TYPE:{error_type}"
    if value and len(str(value)) < 100:  # 長すぎる値はログに残さない
        details += f" VALUE:{value}"
    
    log_security_event(
        request, 
        'VALIDATION_ERROR', 
        details, 
        level='warning'
    )

def log_rate_limit_exceeded(request, limit_type):
    """レート制限違反のログ記録"""
    log_security_event(
        request,
        'RATE_LIMIT_EXCEEDED',
        f"LIMIT_TYPE:{limit_type}",
        level='error'
    )