from django.contrib import admin
from .models import Reservation

# 管理画面に表示できるように登録
admin.site.register(Reservation)
