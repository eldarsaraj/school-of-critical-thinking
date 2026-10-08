from django.urls import path
from . import tutor_views as views

urlpatterns = [
    # Public
    path("", views.tutor_landing, name="tutor_landing"),
    path("signup/", views.tutor_signup, name="tutor_signup"),
    path("login/", views.tutor_login, name="tutor_login"),
    path("logout/", views.tutor_logout, name="tutor_logout"),
    path("verify-email/", views.tutor_verify_pending, name="tutor_verify_pending"),
    path("verify-email/<uuid:token>/", views.tutor_verify_email, name="tutor_verify_email"),
    path("verify-email/resend/", views.tutor_verify_resend, name="tutor_verify_resend"),

    # Protected
    path("dashboard/", views.tutor_dashboard, name="tutor_dashboard"),
    path("dashboard/hunter/", views.tutor_dashboard, {"exam_type": "hunter"}, name="tutor_dashboard_hunter"),
    path("students/<int:parent_id>/", views.tutor_student_detail, name="tutor_student_detail"),
    path("students/<int:parent_id>/hunter/", views.tutor_student_detail, {"exam_type": "hunter"}, name="tutor_student_detail_hunter"),
    path("students/<int:parent_id>/error-analysis/<int:attempt_id>/", views.tutor_error_analysis, name="tutor_error_analysis"),
    path("pricing/", views.tutor_pricing, name="tutor_pricing"),
    path("checkout/", views.tutor_checkout, name="tutor_checkout"),
    path("checkout/success/", views.tutor_checkout_success, name="tutor_checkout_success"),
    path("account/", views.tutor_account, name="tutor_account"),
]
