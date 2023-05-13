from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('registration/', views.RegisterPage.as_view(), name='registration'),
    path('logout/', views.my_logout_view, name='logout'),
    path('dashboard/', views.weather_view, name='dashboard'),
]