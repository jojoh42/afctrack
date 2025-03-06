from django.urls import path
from . import views

app_name = 'afctrack'  # Add this line to specify the app name

urlpatterns = [
    path('', views.index, name='index'),
    path('doctrine_amount/', views.doctrine_amount, name='doctrine_amount'),
    path('fleet_type_amount/', views.fleet_type_amount, name='fleet_type_amount'),
    path('start_fleet/', views.start_fleet, name='start_fleet'),
]
