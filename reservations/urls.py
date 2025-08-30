from django.urls import path
from .views import (
    reserve_form, reservations_list, get_calendar_data_for_item, 
    check_availability, get_disabled_dates, reservation_lookup, 
    cancel_reservation, get_merged_calendar_data, get_available_items_for_date,
    get_item_images, reservation_confirm, reservation_complete
)

urlpatterns = [
    path("", reserve_form, name="reserve_form"),
    path("reservations/", reservations_list, name="reservations_list"),
    path("confirm/", reservation_confirm, name="reservation_confirm"),
    path("complete/", reservation_complete, name="reservation_complete"),
    path("calendar-data/<int:item_id>/", get_calendar_data_for_item, name="calendar_data"),
    path("merged-calendar-data/", get_merged_calendar_data, name="merged_calendar_data"),
    path("available-items/", get_available_items_for_date, name="available_items_for_date"),
    path("check-availability/", check_availability, name="check_availability"),
    path("disabled-dates/<int:item_id>/", get_disabled_dates, name="get_disabled_dates"),
    path("lookup/", reservation_lookup, name="reservation_lookup"),
    path("cancel/<str:confirmation_number>/", cancel_reservation, name="cancel_reservation"),
    path("item-images/<int:item_id>/", get_item_images, name="item_images"),
]
