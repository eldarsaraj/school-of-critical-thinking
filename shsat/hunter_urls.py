from django.urls import path
from . import hunter_views, views

urlpatterns = [
    # Public
    path("", hunter_views.hunter_landing, name="hunter_landing"),
    path("signup/", hunter_views.hunter_signup, name="hunter_signup"),
    path("login/", hunter_views.hunter_login, name="hunter_login"),
    path("logout/", hunter_views.hunter_logout, name="hunter_logout"),
    path("verify-email/", hunter_views.hunter_verify_pending, name="hunter_verify_pending"),
    path("verify-email/resend/", hunter_views.hunter_verify_resend, name="hunter_verify_resend"),

    # Upgrade / checkout
    path("upgrade/", hunter_views.hunter_upgrade, name="hunter_upgrade"),
    path("checkout/", hunter_views.hunter_create_checkout_session, name="hunter_checkout"),
    path("checkout/success/", hunter_views.hunter_checkout_success, name="hunter_checkout_success"),
    path("checkout/cancel/", hunter_views.hunter_checkout_cancel, name="hunter_checkout_cancel"),

    # Protected
    path("dashboard/", hunter_views.hunter_dashboard, name="hunter_dashboard"),
    path("tests/", hunter_views.hunter_test_list, name="hunter_test_list"),
    path("resources/", hunter_views.hunter_resources, name="hunter_resources"),
    path("account/", hunter_views.hunter_account, name="hunter_account"),
    path("tests/<int:attempt_id>/delete/", hunter_views.hunter_delete_attempt, name="hunter_delete_attempt"),

    # Test-taking (shared views, Hunter-aware)
    path("tests/<int:test_id>/", views.test_intro, name="hunter_test_intro"),
    path("tests/<int:test_id>/take/", views.test_take, name="hunter_test_take"),
    path("tests/<int:test_id>/submit/", views.test_submit, name="hunter_test_submit"),
    path("tests/<int:attempt_id>/results/", views.test_results, name="hunter_test_results"),
    path("error-analysis/", hunter_views.hunter_error_analysis_list, name="hunter_error_analysis_list"),
    path("tests/<int:attempt_id>/error-analysis/", views.error_analysis, name="hunter_error_analysis"),
]
