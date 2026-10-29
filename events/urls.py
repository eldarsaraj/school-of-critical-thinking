from django.urls import path

from . import views

urlpatterns = [
    path("hunter-briefing/", views.hunter_briefing, name="hunter_briefing"),
]
