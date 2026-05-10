from django.urls import path
from django.views.generic import RedirectView
from . import views
from .views import robots_txt


urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("books/", views.books, name="books"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
    path("contact/", views.contact, name="contact"),
    path("start/", views.start, name="start"),
    path("curriculum/", RedirectView.as_view(url="/families/", permanent=True)),
    path("curriculum/download-sample/", views.download_sample, name="download_sample"),
    path("curriculum/sample-lesson.pdf", views.sample_pdf, name="sample_pdf"),
    path("curriculum/<slug:slug>/", views.curriculum_module_redirect),
    path("families/<slug:slug>/", views.module_detail, name="module_detail"),
    path("newsletter/", views.newsletter_signup, name="newsletter_signup"),
    path("families/", views.families, name="families"),
    path("families/waitlist/", views.waitlist_signup, name="waitlist_signup"),
    path("organizations/", views.organizations, name="organizations"),
    path("learners/", views.learners, name="learners"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("robots.txt", robots_txt, name="robots_txt"),
]
