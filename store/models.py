from django.contrib.auth.models import AbstractUser
from django.db import models 
import pytils
from django.urls import reverse

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Администратор'),
        ('user', 'Пользователь'),
    )
    
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='user',
        verbose_name='Роль'
    )
    
    phone = models.CharField(
        max_length=15, 
        blank=True, 
        verbose_name='Телефон'
    )
    
    address = models.TextField(
        blank=True, 
        verbose_name='Адрес'
    )
    
    city = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name='Город'
    )
    
    postal_code = models.CharField(
        max_length=10, 
        blank=True, 
        verbose_name='Почтовый индекс'
    )
    
    country = models.CharField(
        max_length=100, 
        blank=True, 
        default='Россия',
        verbose_name='Страна'
    )
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
    
    def __str__(self):
        return self.username
    
    def is_admin(self):
        return self.role == 'admin'
    
    def get_full_address(self):
        """Возвращает полный адрес в формате строки"""
        parts = []
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        if self.city:
            parts.append(f"г. {self.city}")
        if self.address:
            parts.append(self.address)
        return ", ".join(parts) if parts else "Адрес не указан"


class Category(models.Model):
    """Модель категорий товаров"""
    
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']  

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = pytils.translit.slugify(self.name)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.name


class Product(models.Model):
    """Модель товаров"""
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products/")
    stock = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products"
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name='Рекомендуемый товар',
        help_text='Отметьте, если товар должен отображаться в рекомендованных')

    def save(self, *args, **kwargs):
        if self.is_featured:
            featured_count = Product.objects.filter(is_featured=True).count()
            if featured_count >= 8:  # Максимум 8 рекомендуемых товаров
                pass
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']  # Добавлено для стандартной сортировки

    def __str__(self):
        return self.name


class Cart(models.Model):
    """Модель корзины пользователя"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def total_price(self):
        """Возвращает общую стоимость товаров в корзине"""
        return sum(item.total_price() for item in self.items.all())
    
    def total_items(self):
        """Возвращает общее количество товаров в корзине"""
        return sum(item.quantity for item in self.items.all())
    
    def __str__(self):
        return f"Корзина {self.user.username}"


class CartItem(models.Model):
    """Модель элемента корзины"""
    
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')

    def total_price(self):
        """Возвращает общую стоимость позиции"""
        return self.product.price * self.quantity
    
    def __str__(self):
        return f"{self.product.name} ({self.quantity})"


class Order(models.Model):
    STATUS_CHOICES = (
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
    )
    
    DELIVERY_CHOICES = (
        ('pickup', 'Самовывоз'),
        ('delivery', 'Доставка'),
    )
    
    PAYMENT_CHOICES = (
        ('online', 'Онлайн-оплата'),
        ('cod', 'Оплата при получении'),
    )
    
    PRIORITY_CHOICES = (
        ('low', 'Низкий'),
        ('medium', 'Средний'),
        ('high', 'Высокий'),
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name="orders",
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='new',
        verbose_name='Статус'
    )
    delivery_method = models.CharField(
        max_length=20, 
        choices=DELIVERY_CHOICES, 
        default='pickup',
        verbose_name='Способ доставки'
    )
    payment_method = models.CharField(
        max_length=20, 
        choices=PAYMENT_CHOICES, 
        default='cod',
        verbose_name='Способ оплаты'
    )
    total_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Общая стоимость'
    )
    
    # Информация о доставке
    shipping_address = models.TextField(
        verbose_name='Адрес доставки',
        blank=True
    )
    shipping_city = models.CharField(
        max_length=100,
        verbose_name='Город',
        blank=True
    )
    shipping_zip_code = models.CharField(
        max_length=10,
        verbose_name='Почтовый индекс',
        blank=True
    )
    customer_notes = models.TextField(
        blank=True,
        verbose_name='Примечания клиента'
    )
    
    # Поля для администрирования
    admin_notes = models.TextField(
        blank=True,
        verbose_name='Заметки администратора'
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
        verbose_name='Ответственный'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name='Приоритет'
    )
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заказ #{self.id} от {self.user.username}"
    
    def get_absolute_url(self):
        return reverse('order_detail', kwargs={'pk': self.pk})
    
    def update_total_price(self):
        """Обновляет общую стоимость заказа на основе позиций"""
        self.total_price = sum(item.total_price() for item in self.items.all())
        self.save()


class OrderItem(models.Model):
    """Модель элемента заказа"""
    
    order = models.ForeignKey(
        Order, 
        on_delete=models.CASCADE,  
        related_name="items",
        verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def total_price(self):
        """Возвращает общую стоимость позиции"""
        return self.price * self.quantity
    
    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
    

