
from django.conf.urls import url
from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^oauth_callback$',views.QQLoginView.as_view(),name='qqlogin'),
]
