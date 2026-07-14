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
    # Curriculum (canonical URLs)
    path("curriculum/", views.families, name="curriculum"),
    path("curriculum/download-sample/", views.download_sample, name="download_sample"),
    path("curriculum/sample-lesson.pdf", views.sample_pdf, name="sample_pdf"),
    path("curriculum/<slug:slug>/", views.module_detail, name="module_detail"),
    path("curriculum/waitlist/", views.waitlist_signup, name="waitlist_signup"),
    # Legacy /families/ URLs — permanent redirects for SEO
    path("families/", RedirectView.as_view(url="/curriculum/", permanent=True)),
    path("families/waitlist/", RedirectView.as_view(url="/curriculum/waitlist/", permanent=True)),
    path("families/<slug:slug>/", views.curriculum_module_redirect),
    path("newsletter/", views.newsletter_signup, name="newsletter_signup"),
    path("organizations/", views.organizations, name="organizations"),
    path("learners/", views.learners, name="learners"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("test-prep/", views.test_prep, name="test_prep"),
    path("robots.txt", robots_txt, name="robots_txt"),
]
