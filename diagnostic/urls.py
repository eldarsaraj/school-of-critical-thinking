from django.urls import path
from . import views

urlpatterns = [
    path("", views.diagnostic_intro, name="diagnostic_intro"),
    path("questions/", views.diagnostic_questions, name="diagnostic_questions"),
    path("results/", views.diagnostic_results, name="diagnostic_results"),
    path("email/", views.diagnostic_email, name="diagnostic_email"),
    path("syllabus/", views.diagnostic_syllabus, name="diagnostic_syllabus"),
    path("pdf/", views.diagnostic_pdf, name="diagnostic_pdf"),
]
