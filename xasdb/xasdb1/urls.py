from django.urls import path

from . import views

app_name = 'xasdb1'
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('upload/', views.upload, name='upload'),
    path('element/<str:element_id>/', views.element, name='element'),
    path('file/<int:file_id>/', views.file, name='file'),
    path('file/<int:file_id>/<str:xaxis_name>/<str:yaxis_name>/', views.file_plot, name='file_plot'),
]
