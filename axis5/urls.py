from django.urls import path
from . import views

app_name = "axis5"

urlpatterns = [
    path("", views.start, name="start"),
    path("<uuid:token>/item/<int:n>/", views.item, name="item"),
    path("<uuid:token>/item/<int:n>/step/", views.step, name="step"),
    path("<uuid:token>/complete/", views.complete, name="complete"),
    path("results/<uuid:token>/", views.results, name="results"),
]
