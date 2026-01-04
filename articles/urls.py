from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="articles_index"),
    path("<slug:slug>/", views.detail, name="articles_detail"),
]
