from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("books/", views.books, name="books"),
    path("contact/", views.contact, name="contact"),
    path("start/", views.start, name="start"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
]
