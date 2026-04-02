from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home and authentication
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # File upload and management
    path('upload/', views.upload_file, name='upload_file'),
    path('upload/handle/', views.handle_file_upload, name='handle_file_upload'),
    path('file/<int:file_id>/', views.dataset_detail, name='dataset_detail'),
    path('file/<int:file_id>/delete/', views.delete_file, name='delete_file'),
    path('api/dataset/<int:file_id>/columns/', views.get_dataset_columns, name='get_dataset_columns'),
    
    # Dashboard management
    path('dashboard/create/<int:file_id>/', views.create_dashboard, name='create_dashboard'),
    path('dashboard/<int:dashboard_id>/', views.dashboard_view, name='dashboard_view'),
    path('dashboards/', views.dashboard_list, name='dashboard_list'),
    path('dashboard/<int:dashboard_id>/delete/', views.delete_dashboard, name='delete_dashboard'),
    
    # Chart management (AJAX APIs)
    path('api/dashboard/<int:dashboard_id>/chart/add/', views.add_chart, name='add_chart'),
    path('api/chart/<int:chart_id>/delete/', views.delete_chart, name='delete_chart'),
    path('api/chart/<int:chart_id>/data/', views.get_chart_data, name='get_chart_data'),
    
    # Collaboration and sharing APIs
    path('api/dashboard/<int:dashboard_id>/share-settings/', views.dashboard_share_settings, name='dashboard_share_settings'),
    path('api/dashboard/<int:dashboard_id>/collaborators/', views.dashboard_collaborators, name='dashboard_collaborators'),
    path('api/dashboard/<int:dashboard_id>/duplicate/', views.duplicate_dashboard, name='duplicate_dashboard'),
    path('api/dashboards/shared-with-me/', views.shared_dashboards, name='shared_dashboards'),
    
    # Public and export endpoints
    path('dashboard/<int:dashboard_id>/public/', views.dashboard_public_view, name='dashboard_public_view'),
    path('dashboard/<int:dashboard_id>/export/pdf/', views.dashboard_export_pdf, name='dashboard_export_pdf'),
]