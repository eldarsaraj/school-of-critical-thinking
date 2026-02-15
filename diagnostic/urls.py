from django.urls import path
from . import views

urlpatterns = [
    path("", views.diagnostic_home, name="diagnostic_home"),
    path("results/", views.diagnostic_results, name="diagnostic_results"),
    path("email/", views.diagnostic_email, name="diagnostic_email"),
    path("syllabus/", views.diagnostic_syllabus, name="diagnostic_syllabus"),
    path("pdf/", views.diagnostic_pdf, name="diagnostic_pdf"),
]
