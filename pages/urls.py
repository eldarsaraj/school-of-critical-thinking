from django.urls import path
from . import views
from .views import robots_txt


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("books/", views.books, name="books"),
    path("contact/", views.contact, name="contact"),
    path("start/", views.start, name="start"),
    path("curriculum/", views.curriculum, name="curriculum"),
    path("curriculum/download-sample/", views.download_sample, name="download_sample"),
    path("curriculum/sample-lesson.pdf", views.sample_pdf, name="sample_pdf"),
    path("curriculum/<slug:slug>/", views.module_detail, name="module_detail"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("robots.txt", robots_txt, name="robots_txt"),
]
