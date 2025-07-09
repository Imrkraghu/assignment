from django.urls import path
from . import views

urlpatterns = [
    path('', views.adminpage, name='home'),
    path('login/', views.login_user, name="login_user"),
    path('adddata/', views.adddata_page, name="adddata_page"),
    path('save_location/', views.save_location, name="save_location"),
    path('download/geojson/', views.download_geojson_file, name="download_geojson"),
    path('download/excel/', views.download_excel_report, name="download_excel"),
]