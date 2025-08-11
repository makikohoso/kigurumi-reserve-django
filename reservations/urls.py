from django.urls import path
from .views import reserve_form

urlpatterns = [
    path("", reserve_form, name="reserve_form"),
]
