import base64
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class BasicAuthMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Basic認証が無効な場合はスキップ
        if not getattr(settings, 'BASIC_AUTH_ENABLED', False):
            return None
        
        # 管理者ページはDjangoの認証を使用
        if request.path.startswith('/admin/'):
            return None
            
        # 静的ファイルとfaviconは認証をスキップ
        if request.path.startswith('/static/') or request.path == '/favicon.ico':
            return None

        # 認証情報をチェック
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    try:
                        username, password = base64.b64decode(auth[1]).decode('utf-8').split(':', 1)
                        if (username == getattr(settings, 'BASIC_AUTH_USERNAME', '') and 
                            password == getattr(settings, 'BASIC_AUTH_PASSWORD', '')):
                            return None
                    except Exception:
                        pass

        # 認証失敗時のレスポンス
        response = HttpResponse('Unauthorized', status=401)
        response['WWW-Authenticate'] = 'Basic realm="Restricted"'
        return response