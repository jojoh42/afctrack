from django.urls import path
from . import views

app_name = 'afctrack'  # Add this line to specify the app name

urlpatterns = [
    path('', views.index, name='index'),
    path('doctrine_amount/', views.doctrine_amount, name='doctrine_amount'),
]
