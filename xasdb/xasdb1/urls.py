from django.urls import path, re_path
from django.contrib.auth.views import PasswordResetView
from . import views

app_name = 'xasdb1'
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('change_password/', views.change_password, name='change_password'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset_done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password_reset_complete/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    re_path(r'^password_reset_confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('upload/', views.upload, name='upload'),
    path('download/<path:path_id>/', views.download, name='download'),
    path('element/<str:element_id>/', views.element, name='element'),
    path('file/<int:file_id>/', views.file, name='file'),
    re_path(r'^activate/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$', views.activate, name='activate'),
]
