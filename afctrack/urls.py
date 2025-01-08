from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('doctrine_amount/', views.doctrine_amount, name='doctrine_amount'),
    path('fleet_counts/', views.fleet_counts, name='fleet_counts'),  # Added this line
]
