from django.urls import path, re_path

from . import views

app_name = 'xasdb1'
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('upload/', views.upload, name='upload'),
    path('download/<path:path_id>/', views.download, name='download'),
    path('element/<str:element_id>/', views.element, name='element'),
    path('file/<int:file_id>/', views.file, name='file'),
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.activate, name='activate'),
]
