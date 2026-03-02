from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('register/', views.register, name='register'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/', views.checkout, name='checkout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('order/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('order/<int:order_id>/', views.order_detail, name='order_detail'),
    
    # Админские маршруты
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/orders/', views.admin_order_list, name='admin_order_list'),
    path('admin/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('admin/orders/delete/<int:order_id>/', views.admin_order_delete, name='admin_order_delete'),
    path('admin/users/', views.admin_user_list, name='admin_user_list'),
    path('admin/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('admin/products/', views.admin_product_list, name='admin_product_list'),
    path('admin/products/create/', views.admin_product_create, name='admin_product_create'),
    path('admin/products/edit/<int:product_id>/', views.admin_product_edit, name='admin_product_edit'),
    path('admin/products/delete/<int:product_id>/', views.admin_product_delete, name='admin_product_delete'),
    path('admin/categories/', views.admin_category_list, name='admin_category_list'),
    path('admin/categories/create/', views.admin_category_create, name='admin_category_create'),
    path('admin/categories/edit/<int:category_id>/', views.admin_category_edit, name='admin_category_edit'),
    path('admin/categories/delete/<int:category_id>/', views.admin_category_delete, name='admin_category_delete'),
]