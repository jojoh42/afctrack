"""App URLs"""

# Django
from django.urls import path

# AA afctrack App
from afctrack import views

app_name: str = "afctrack"

urlpatterns = [
    path("", views.index, name="index"),
]
