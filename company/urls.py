from django.urls import path
from company import views

urlpatterns = [
    # B2B E-Commerce Marketplace
    path('marketplace/', views.marketplace_home_view, name='marketplace_home'),
    path('marketplace/products/', views.product_list_view, name='product_list'),
    path('marketplace/products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('marketplace/cart/', views.cart_view, name='cart'),
    path('marketplace/cart/add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('marketplace/cart/update/<int:item_id>/', views.update_cart_view, name='update_cart'),
    path('marketplace/cart/remove/<int:item_id>/', views.remove_from_cart_view, name='remove_from_cart'),
    path('marketplace/checkout/', views.checkout_view, name='checkout'),
    path('marketplace/payment/<int:order_id>/', views.payment_gateway_view, name='payment_gateway'),
    path('marketplace/order-success/<int:order_id>/', views.order_success_view, name='order_success'),

    # Company Panel
    path('company/dashboard/', views.company_dashboard_view, name='company_dashboard'),
    path('company/orders/', views.company_orders_list_view, name='company_orders'),
    path('company/orders/<int:order_id>/', views.company_order_detail_view, name='company_order_detail'),
    path('company/profile/', views.company_profile_view, name='company_profile'),
]
