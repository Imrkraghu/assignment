from django.urls import path
from .views import LocationGeoJSONView, LocationStatsView
from . import views

urlpatterns = [
    path('',views.index, name='home'),
    path('adminpage/',views.adminpage, name='adminpage'),
    path('geojson/', LocationGeoJSONView.as_view(), name='geojson'),
    path('stats/', LocationStatsView.as_view(), name='stats'),
]