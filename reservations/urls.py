from django.urls import path
from .views import (
    reserve_form, reservations_list, get_calendar_data_for_item, 
    check_availability, get_disabled_dates, reservation_lookup, 
    cancel_reservation
)

urlpatterns = [
    path("", reserve_form, name="reserve_form"),
    path("reservations/", reservations_list, name="reservations_list"),
    path("calendar-data/<int:item_id>/", get_calendar_data_for_item, name="calendar_data"),
    path("check-availability/", check_availability, name="check_availability"),
    path("disabled-dates/<int:item_id>/", get_disabled_dates, name="get_disabled_dates"),
    path("lookup/", reservation_lookup, name="reservation_lookup"),
    path("cancel/<str:confirmation_number>/", cancel_reservation, name="cancel_reservation"),
]
