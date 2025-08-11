from django.shortcuts import render
from .models import Reservation

def reserve_form(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            Reservation.objects.create(name=name)
            return render(request, "reservations/thanks.html", {"name": name})
    return render(request, "reservations/form.html")
