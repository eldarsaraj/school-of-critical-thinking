from django.urls import path
from . import views

urlpatterns = [
    # Public
    path("", views.landing, name="shsat_landing"),
    path("signup/", views.shsat_signup, name="shsat_signup"),
    path("login/", views.shsat_login, name="shsat_login"),
    path("logout/", views.shsat_logout, name="shsat_logout"),
    path("resources/", views.resources, name="shsat_resources"),

    # Protected
    path("upgrade/", views.upgrade, name="shsat_upgrade"),
    path("checkout/", views.create_checkout_session, name="shsat_checkout"),
    path("checkout/success/", views.checkout_success, name="shsat_checkout_success"),
    path("checkout/cancel/", views.checkout_cancel, name="shsat_checkout_cancel"),
    path("webhook/stripe/", views.stripe_webhook, name="shsat_stripe_webhook"),
    path("dashboard/", views.dashboard, name="shsat_dashboard"),
    path("log-score/", views.log_score, name="shsat_log_score"),
    path("log-score/<int:score_id>/delete/", views.delete_manual_score, name="shsat_delete_manual_score"),
    path("tests/", views.test_list, name="shsat_test_list"),
    path("tests/<int:test_id>/", views.test_intro, name="shsat_test_intro"),
    path("tests/<int:test_id>/take/", views.test_take, name="shsat_test_take"),
    path("tests/<int:test_id>/submit/", views.test_submit, name="shsat_test_submit"),
    path("tests/<int:attempt_id>/results/", views.test_results, name="shsat_test_results"),
    path("error-analysis/", views.error_analysis_list, name="shsat_error_analysis_list"),
    path("tests/<int:attempt_id>/error-analysis/", views.error_analysis, name="shsat_error_analysis"),
    path("account/", views.account, name="shsat_account"),
    path("tests/<int:attempt_id>/delete/", views.delete_attempt, name="shsat_delete_attempt"),

    # AJAX
    path("api/save-answer/", views.save_answer, name="shsat_save_answer"),
    path("api/flag-question/", views.flag_question, name="shsat_flag_question"),
    path("api/assign-modules/", views.assign_modules, name="shsat_assign_modules"),

    # Content review (staff only — not linked in nav)
    path("content/", views.content_home, name="shsat_content_home"),
    path("content/add-test/", views.content_test_add, name="shsat_content_test_add"),
    path("content/<int:test_id>/edit/", views.content_test_edit, name="shsat_content_test_edit"),
    path("content/<int:test_id>/", views.content_test, name="shsat_content_test"),
    path("content/<int:test_id>/add/", views.content_question_add, name="shsat_content_question_add"),
    path("content/question/<int:question_id>/edit/", views.content_question_edit, name="shsat_content_question_edit"),
    path("content/question/<int:question_id>/delete/", views.content_question_delete, name="shsat_content_question_delete"),
    path("content/<int:test_id>/delete/", views.content_test_delete, name="shsat_content_test_delete"),
    path("content/<int:test_id>/export/", views.content_test_export, name="shsat_content_test_export"),
    path("content/<int:test_id>/answers-csv/", views.content_test_answers_csv, name="shsat_content_answers_csv"),
]
