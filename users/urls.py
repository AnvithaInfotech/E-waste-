from django.urls import path
from users import views

urlpatterns = [
    # Public & Auth
    path('', views.home_view, name='home'),
    path('about/', views.about_view, name='about'),
    path('impact/', views.impact_view, name='impact'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_user_view, name='register_user'),
    path('register/company/', views.register_company_view, name='register_company'),
    path('register/collector/', views.register_collector_view, name='register_collector'),
    path('role-redirect/', views.role_redirect_view, name='role_redirect'),
    path('switch-persona/<str:role_name>/', views.switch_persona_view, name='switch_persona'),

    # User Portal
    path('user/dashboard/', views.user_dashboard, name='user_dashboard'),
    path('user/submit-ewaste/', views.submit_ewaste_view, name='submit_ewaste'),
    path('user/my-ewaste/', views.my_ewaste_list_view, name='my_ewaste_list'),
    path('user/my-ewaste/<int:submission_id>/', views.ewaste_detail_view, name='ewaste_detail'),
    path('user/my-ewaste/<int:submission_id>/cancel/', views.cancel_ewaste_view, name='cancel_ewaste'),
    path('user/notifications/', views.notifications_view, name='user_notifications'),
    path('user/profile/', views.user_profile_view, name='user_profile'),

    # Local Collector Portal
    path('collector/dashboard/', views.collector_dashboard, name='collector_dashboard'),
    path('collector/pickups/', views.collector_assigned_pickups_view, name='collector_pickups'),
    path('collector/pickups/<int:assignment_id>/', views.collector_pickup_detail_view, name='collector_pickup_detail'),
    path('collector/deliveries/<int:order_id>/', views.collector_delivery_detail_view, name='collector_delivery_detail'),
    path('collector/deliveries/<int:order_id>/status/', views.collector_update_delivery_status_view, name='collector_update_delivery_status'),
    path('collector/history/', views.collector_history_view, name='collector_history'),
    path('collector/profile/', views.collector_profile_view, name='collector_profile'),
]
