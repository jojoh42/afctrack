from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('doctrine_amount/', views.doctrine_amount, name='doctrine_amount'),
]
