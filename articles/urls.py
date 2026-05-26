from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="articles_index"),
    path("<slug:slug>/", views.detail, name="articles_detail"),
    path("<slug:slug>/og-image.jpg", views.og_image, name="articles_og_image"),
]
