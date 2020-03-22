
from django.conf.urls import url
from django.contrib import admin
from . import views

urlpatterns = [
    url(r'^areas/$',views.AreasView.as_view(),name='area'),
]
