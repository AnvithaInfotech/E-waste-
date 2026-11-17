from django.urls import path
from admin import views

urlpatterns = [
    # Operational Admin Panel
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/ewaste/', views.admin_ewaste_list_view, name='admin_ewaste_list'),
    path('admin-panel/collectors/', views.admin_collectors_list_view, name='admin_collectors_list'),
    path('admin-panel/ewaste/<int:submission_id>/verify/', views.admin_ewaste_verify_view, name='admin_ewaste_verify'),
    path('admin-panel/ewaste/<int:submission_id>/assign/', views.admin_assign_collector_view, name='admin_assign_collector'),
    path('admin-panel/ewaste/<int:submission_id>/recycle/', views.admin_recycle_submission_view, name='admin_recycle_submission'),
    path('admin-panel/ewaste/<int:submission_id>/delete/', views.admin_delete_ewaste_submission_view, name='admin_delete_ewaste_submission'),
    path('admin-panel/products/', views.admin_recycled_products_list_view, name='admin_recycled_products_list'),
    path('admin-panel/products/<int:product_id>/', views.admin_recycled_product_detail_view, name='admin_recycled_product_detail'),
    path('admin-panel/products/<int:product_id>/delete/', views.admin_delete_recycled_product_view, name='admin_delete_recycled_product'),
    path('admin-panel/recycling/', views.admin_recycling_list_view, name='admin_recycling_list'),
    path('admin-panel/recycling/create/', views.admin_create_recycling_record_view, name='admin_recycling_create'),
    path('admin-panel/recycling/<int:record_id>/edit/', views.admin_update_recycling_record_view, name='admin_recycling_edit'),
    path('admin-panel/publish-product/', views.admin_publish_product_view, name='admin_publish_product'),
    path('admin-panel/orders/', views.admin_order_list_view, name='admin_order_list'),
    path('admin-panel/orders/create/', views.admin_create_order_view, name='admin_create_order'),
    path('admin-panel/orders/<int:order_id>/', views.admin_order_detail_view, name='admin_order_detail'),

    # Super Admin Governance Panel
    path('super-admin/dashboard/', views.super_admin_dashboard, name='super_admin_dashboard'),
    path('super-admin/ewaste/', views.super_admin_ewaste_view, name='super_admin_ewaste'),
    path('super-admin/users/', views.super_admin_users_view, name='super_admin_users'),
    path('super-admin/collectors/', views.super_admin_collectors_view, name='super_admin_collectors'),
    path('super-admin/companies/', views.super_admin_companies_view, name='super_admin_companies'),
    path('super-admin/categories/', views.super_admin_categories_view, name='super_admin_categories'),
]

