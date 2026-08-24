from django.urls import path
from . import views

app_name = "axis5"

urlpatterns = [
    path("", views.start, name="start"),
    path("<uuid:token>/item/<int:n>/", views.item, name="item"),
    path("<uuid:token>/item/<int:n>/step/", views.step, name="step"),
    path("<uuid:token>/complete/", views.complete, name="complete"),
    path("results/<uuid:token>/", views.results, name="results"),
    # Auth
    path("auth/signup/", views.ax_signup, name="signup"),
    path("auth/login/", views.ax_login, name="login"),
    path("auth/logout/", views.ax_logout, name="logout"),
    # Staff
    path("admin/item-stats/", views.staff_item_stats, name="item_stats"),
]
