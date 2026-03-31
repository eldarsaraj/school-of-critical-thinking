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
    path("dashboard/", views.dashboard, name="shsat_dashboard"),
    path("log-score/", views.log_score, name="shsat_log_score"),
    path("tests/", views.test_list, name="shsat_test_list"),
    path("tests/<int:test_id>/", views.test_intro, name="shsat_test_intro"),
    path("tests/<int:test_id>/take/", views.test_take, name="shsat_test_take"),
    path("tests/<int:test_id>/submit/", views.test_submit, name="shsat_test_submit"),
    path("tests/<int:attempt_id>/results/", views.test_results, name="shsat_test_results"),
    path("account/", views.account, name="shsat_account"),

    # AJAX
    path("api/save-answer/", views.save_answer, name="shsat_save_answer"),
    path("api/flag-question/", views.flag_question, name="shsat_flag_question"),
]
