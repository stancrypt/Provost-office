from . import views
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView, CustomLogoutView
from django.views.generic import TemplateView

urlpatterns = [
    # path('login/', CustomLoginView.as_view(), name='login'),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('home/', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('daily/', views.daily, name='daily'),
    path('monthly/', views.monthly, name='monthly'),

]