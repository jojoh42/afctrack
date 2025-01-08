"""App URLs"""

# Django
from django.urls import path

from afctrack import views

app_name = "afctrack"

urlpatterns = [
    path("", views.index, name="index"),
    path("fleet_counts/", views.fleet_counts, name="fleet_counts"),
    path("about/", views.about, name="about"),
    path("doctrine_amount/", views.doctrine_amount, name="doctrine_amount"),  # Add this line
]
