from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q, Count, Sum
from .models import Product, Category, Cart, CartItem, Order, OrderItem, User
from .forms import UserRegisterForm, ProductForm, CategoryForm, CheckoutForm
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta


class CustomLoginView(LoginView):
    template_name = 'store/login.html'
    redirect_authenticated_user = True

    def form_invalid(self, form):
        messages.error(self.request, 'Неверное имя пользователя или пароль.')
        return super().form_invalid(form)

class CustomLogoutView(LogoutView):
    template_name = 'store/logout.html'


def is_admin(user):
    return user.is_authenticated and (user.role == 'admin' or user.is_superuser)

def index(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    featured_products = Product.objects.filter(is_featured=True)
    # Фильтрация по категории
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Поиск по названию и описанию
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query)
        )
    
    # Фильтрация по цене
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    
    if min_price:
        try:
            products = products.filter(price__gte=float(min_price))
        except ValueError:
            pass
            
    if max_price:
        try:
            products = products.filter(price__lte=float(max_price))
        except ValueError:
            pass
    
    context = {
        'products': products,
        'featured_products': featured_products,
        'categories': categories,
    }
    return render(request, 'store/index.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    context = {'product': product}
    return render(request, 'store/product_detail.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('index')
    else:
        form = UserRegisterForm()
    return render(request, 'store/register.html', {'form': form})


@login_required
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)

    for item in cart.items.all():
        item.product = Product.objects.get(id=item.product.id)
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all(),
    }
    return render(request, 'store/cart.html', context)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    # Проверяем наличие товара на складе
    if product.stock <= 0:
        messages.error(request, f'{product.name} нет в наличии')
        return redirect('product_detail', product_id=product_id)
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # Проверяем, не превышает ли запрашиваемое количество доступное
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        if cart_item.quantity + 1 > product.stock:
            messages.error(request, f'Недостаточно товара {product.name} на складе')
            return redirect('cart')
        cart_item.quantity += 1
        cart_item.save()
    else:
        if cart_item.quantity > product.stock:
            messages.error(request, f'Недостаточно товара {product.name} на складе')
            cart_item.delete()
            return redirect('cart')
    
    messages.success(request, f'{product.name} добавлен в корзину')
    return redirect('cart')

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Товар удален из корзины')
    return redirect('cart')

@login_required
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    
    # Проверяем, не превышает ли новое количество доступное на складе
    if quantity > cart_item.product.stock:
        messages.error(request, f'Недостаточно товара {cart_item.product.name} на складе')
        return redirect('cart')
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()
    
    return redirect('cart')

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.warning(request, 'Ваша корзина пуста')
        return redirect('cart')
    
    # Проверяем наличие всех товаров перед оформлением заказа
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.error(request, f'Недостаточно товара {item.product.name} на складе')
            return redirect('cart')
    
    if request.method == 'POST':
        # Обновляем данные пользователя
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone = request.POST.get('phone', '')
        user.country = request.POST.get('country', '')
        user.city = request.POST.get('city', '')
        user.postal_code = request.POST.get('postal_code', '')
        user.address = request.POST.get('address', '')
        user.save()
        
        # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            delivery_method=request.POST.get('delivery_method', 'pickup'),
            payment_method=request.POST.get('payment_method', 'online'),
            total_price=cart.total_price() + (500 if request.POST.get('delivery_method') == 'delivery' else 0),
            shipping_address=user.get_full_address(),
            shipping_city=user.city,
            shipping_zip_code=user.postal_code
        )
        
        # Добавляем товары в заказ и уменьшаем количество на складе
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
            
            # Уменьшаем количество товара на складе
            product = item.product
            product.stock -= item.quantity
            product.save()
        
        # Очищаем корзину
        cart.items.all().delete()
        
        messages.success(request, f'Заказ успешно оформлен! Номер вашего заказа: #{order.id}')
        return redirect('order_detail', order_id=order.id)
    
    context = {
        'cart': cart,
    }
    return render(request, 'store/checkout.html', context)

@user_passes_test(is_admin)
def admin_product_list(request):
    products = Product.objects.all()
    context = {'products': products}
    return render(request, 'store/admin/product_list.html', context)

@user_passes_test(is_admin)
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, 'Товар успешно добавлен')
            return redirect('admin_product_list')
    else:
        form = ProductForm()
    return render(request, 'store/admin/product_form.html', {'form': form})

@user_passes_test(is_admin)
def admin_product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            # Проверяем, не уменьшается ли количество товара ниже 0
            if 'stock' in form.changed_data:
                new_stock = form.cleaned_data['stock']
                if new_stock < 0:
                    messages.error(request, 'Количество товара не может быть отрицательным')
                    return render(request, 'store/admin/product_form.html', {'form': form})
            
            product = form.save()
            
            messages.success(request, 'Товар успешно обновлен')
            return redirect('admin_product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'store/admin/product_form.html', {'form': form})

@user_passes_test(is_admin)
def admin_product_delete(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        product_name = product.name
        product_id = product.id
        product.delete()
        messages.success(request, 'Товар успешно удален')
        return redirect('admin_product_list')
    return render(request, 'store/admin/product_confirm_delete.html', {'product': product})

@user_passes_test(is_admin)
def admin_category_create(request):
    """Создание новой категории"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Категория "{category.name}" успешно создана')
            return redirect('admin_category_list')
    else:
        form = CategoryForm()
    
    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'store/admin/category_form.html', context)

@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    categories = Category.objects.all()
    context = {'orders': orders,
               'categories':categories}
    return render(request, 'store/profile.html', context)

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        
        # Обновляем основные данные
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')  # Добавляем обновление email
        
        # Обновляем контактные данные
        user.phone = request.POST.get('phone', '')
        user.address = request.POST.get('address', '')
        user.city = request.POST.get('city', '')
        user.postal_code = request.POST.get('postal_code', '')
        user.country = request.POST.get('country', 'Россия')
        
        # Проверяем уникальность email
        if user.email != request.user.email:
            if User.objects.filter(email=user.email).exclude(id=user.id).exists():
                messages.error(request, 'Пользователь с таким email уже существует.')
                return redirect('profile')
        
        try:
            user.save()
            messages.success(request, 'Профиль успешно обновлен')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении профиля: {str(e)}')
        
        return redirect('profile')
    
    messages.error(request, 'Неверный запрос')
    return redirect('profile')

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    context = {'order': order}
    return render(request, 'store/order_detail.html', context)

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status == 'new':
        # Возвращаем товары на склад при отмене заказа
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        
        order.status = 'cancelled'
        order.save()
        messages.success(request, 'Заказ успешно отменен')
    else:
        messages.error(request, 'Невозможно отменить заказ в текущем статусе')
    
    return redirect('order_detail', order_id=order.id)

@user_passes_test(is_admin)
def admin_dashboard(request):
    """Главная страница админ-панели"""
    # Основная статистика
    stats = {
        'total_orders': Order.objects.count(),
        'new_orders': Order.objects.filter(status='new').count(),
        'total_users': User.objects.count(),
        'total_products': Product.objects.count(),
    }
    
    # Статистика изменений
    week_ago = timezone.now() - timedelta(days=7)
    prev_week_ago = timezone.now() - timedelta(days=14)
    
    # Изменение количества заказов
    current_week_orders = Order.objects.filter(created_at__gte=week_ago).count()
    prev_week_orders = Order.objects.filter(created_at__gte=prev_week_ago, created_at__lt=week_ago).count()
    
    
    if prev_week_orders > 0:
        orders_change = round((current_week_orders - prev_week_orders) / prev_week_orders * 100, 1)
        stats['orders_trend'] = 'up' if orders_change >= 0 else 'down'
        stats['orders_change'] = abs(orders_change)
    else:
        stats['orders_trend'] = 'up'
        stats['orders_change'] = 100
    
    # Новые пользователи за месяц
    month_ago = timezone.now() - timedelta(days=30)
    stats['new_users'] = User.objects.filter(date_joined__gte=month_ago).count()
    
    # Товары с низким запасом
    stats['low_stock_count'] = Product.objects.filter(stock__lte=5).count()
    
    # Последние заказы
    recent_orders = Order.objects.all().order_by('-created_at')[:10]
    
    # Последние пользователи
    recent_users = User.objects.all().order_by('-date_joined')[:5]
    
    # Статистика по категориям
    category_stats = Category.objects.annotate(product_count=Count('products')).filter(product_count__gt=0)
    colors = ['primary', 'success', 'info', 'warning', 'danger', 'secondary']
    color_codes = ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#858796']
    hover_colors = ['#2e59d9', '#17a673', '#2c9faf', '#dda20a', '#be2617', '#60616f']
    
    category_data = []
    for i, category in enumerate(category_stats):
        color_index = i % len(colors)
        category_data.append({
            'name': category.name,
            'count': category.product_count,
            'color': colors[color_index],
            'color_code': color_codes[color_index],
            'hover_color': hover_colors[color_index]
        })
    
    # Статистика продаж за последние 7 дней
    sales_data = []
    for i in range(6, -1, -1):
        date = timezone.now() - timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime(date.year, date.month, date.day))
        day_end = day_start + timedelta(days=1)
        
        day_orders = Order.objects.filter(created_at__gte=day_start, created_at__lt=day_end)
        total_amount = day_orders.aggregate(total=Sum('total_price'))['total'] or 0
        
        sales_data.append({
            'date': date.strftime('%d.%m'),
            'amount': float(total_amount)
        })
    
    
    
    context = {
        'stats': stats,
        'recent_orders': recent_orders,
        'recent_users': recent_users,
        'category_stats': category_data,
        'sales_stats': sales_data,
        'today': timezone.now()
    }
    return render(request, 'store/admin/dashboard.html', context)


@user_passes_test(is_admin)
def admin_order_list(request):
    """Список заказов для администрирования"""
    orders = Order.objects.all().order_by('-created_at')
    
    # Фильтрация по статусу
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        orders = orders.filter(
            Q(id__icontains=search_query) |
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'status_choices': Order.STATUS_CHOICES,
    }
    return render(request, 'store/admin/order_list.html', context)

@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    """Детальная страница заказа для администрирования"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        # Обновление статуса заказа
        new_status = request.POST.get('status')
        old_status = order.status
        
        if new_status and new_status != old_status:
            # Если заказ отменяется, возвращаем товары на склад
            if new_status == 'cancelled' and old_status != 'cancelled':
                for item in order.items.all():
                    product = item.product
                    product.stock += item.quantity
                    product.save()
            # Если заказ восстанавливается из отмены, уменьшаем количество товаров
            elif old_status == 'cancelled' and new_status != 'cancelled':
                for item in order.items.all():
                    product = item.product
                    if item.quantity > product.stock:
                        messages.error(request, f'Недостаточно товара {product.name} на складе для восстановления заказа')
                        return redirect('admin_order_detail', order_id=order.id)
                    product.stock -= item.quantity
                    product.save()
            
            order.status = new_status
        
        # Добавление/обновление заметок
        admin_notes = request.POST.get('admin_notes')
        if admin_notes is not None:
            order.admin_notes = admin_notes
        # Назначение ответственного
        assigned_to_id = request.POST.get('assigned_to')
        if assigned_to_id:
            try:
                assigned_to = User.objects.get(id=assigned_to_id)
                order.assigned_to = assigned_to
            except User.DoesNotExist:
                messages.error(request, 'Указанный пользователь не найден')
        else:
            order.assigned_to = None
        
        # Установка приоритета
        priority = request.POST.get('priority')
        if priority:
            order.priority = priority
        
        try:
            order.save()
            messages.success(request, f'Заказ #{order.id} успешно обновлен')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении заказа: {str(e)}')
    
    context = {
        'order': order,
        'status_choices': Order.STATUS_CHOICES,
        'priority_choices': Order.PRIORITY_CHOICES,  # Добавляем приоритеты в контекст
        'admin_users': User.objects.filter(role='admin'),
    }
    return render(request, 'store/admin/order_detail.html', context)


@user_passes_test(is_admin)
def admin_user_list(request):
    """Список пользователей для администрирования"""
    users = User.objects.all().order_by('-date_joined')
    
    # Фильтрация по роли
    role_filter = request.GET.get('role')
    if role_filter:
        users = users.filter(role=role_filter)
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Пагинация
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'store/admin/user_list.html', context)

@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    """Детальная страница пользователя для администрирования"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Обновление роли пользователя
        new_role = request.POST.get('role')
        if new_role:
            user.role = new_role
            user.save()
            messages.success(request, f'Роль пользователя {user.username} изменена на {user.get_role_display()}')
        
        # Блокировка/разблокировка пользователя
        is_active = request.POST.get('is_active')
        if is_active is not None:
            user.is_active = (is_active == 'true')
            user.save()
            status = "активирован" if user.is_active else "деактивирован"
            messages.success(request, f'Пользователь {user.username} {status}')
    
    # Получаем заказы пользователя
    user_orders = Order.objects.filter(user=user).order_by('-created_at')
    
    context = {
        'user': user,
        'user_orders': user_orders,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'store/admin/user_detail.html', context)

@user_passes_test(is_admin)
def admin_category_list(request):
    """Список категорий для администрирования"""
    categories = Category.objects.all().order_by('name')
    
    # Поиск
    search_query = request.GET.get('q')
    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    context = {
        'categories': categories,
    }
    return render(request, 'store/admin/category_list.html', context)

@user_passes_test(is_admin)
def admin_category_edit(request, category_id):
    """Редактирование категории"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Категория "{category.name}" успешно обновлена')
            return redirect('admin_category_list')
    else:
        form = CategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'is_edit': True,
    }
    return render(request, 'store/admin/category_form.html', context)

@user_passes_test(is_admin)
def admin_category_delete(request, category_id):
    """Удаление категории"""
    category = get_object_or_404(Category, id=category_id)
    
    # Проверяем, есть ли товары в этой категории
    if category.products.exists():
        messages.error(request, f'Невозможно удалить категорию "{category.name}", так как в ней есть товары')
        return redirect('admin_category_list')
    
    if request.method == 'POST':
        category_name = category.name
        category.delete()
        messages.success(request, f'Категория "{category_name}" успешно удалена')
        return redirect('admin_category_list')
    
    context = {
        'category': category,
    }
    return render(request, 'store/admin/category_confirm_delete.html', context)

@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    """Детальная страница пользователя для администрирования"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Обновление роли пользователя
        new_role = request.POST.get('role')
        if new_role:
            user_obj.role = new_role
        
        # Блокировка/разблокировка пользователя
        is_active = request.POST.get('is_active')
        user_obj.is_active = (is_active == 'on')
        
        try:
            user_obj.save()
            messages.success(request, f'Данные пользователя {user_obj.username} успешно обновлены')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении данных: {str(e)}')
    
    # Получаем заказы пользователя с пагинацией
    user_orders = Order.objects.filter(user=user_obj).order_by('-created_at')
    paginator = Paginator(user_orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'user': user_obj,
        'user_orders': page_obj,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'store/admin/user_detail.html', context)

@user_passes_test(is_admin)
def admin_order_delete(request, order_id):
    """Удаление заказа"""
    try:
        order = get_object_or_404(Order, id=order_id)
        
        if request.method == 'POST':
            # Возвращаем товары на склад при удалении заказа
            if order.status != 'cancelled':
                for item in order.items.all():
                    product = item.product
                    product.stock += item.quantity
                    product.save()
            
            order_id = order.id
            order.delete()
            messages.success(request, f'Заказ #{order_id} успешно удален')
            return redirect('admin_order_list')
        
        context = {
            'order': order,
        }
        return render(request, 'store/admin/order_confirm_delete.html', context)
    
    except Exception as e:
        messages.error(request, f'Ошибка при удалении заказа: {str(e)}')
        return redirect('admin_order_list')