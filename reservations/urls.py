from django.urls import path
from .views import reserve_form, reservations_list

urlpatterns = [
    path("", reserve_form, name="reserve_form"),
    path("reservations/", reservations_list, name="reservations_list"),
]
