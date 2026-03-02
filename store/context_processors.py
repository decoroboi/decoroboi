from .models import Cart
from .models import Category

def categories_processor(request):
    categories = Category.objects.all()
    return {'categories': categories}

def cart_items_count(request):
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            count = cart.items.count()
        except Cart.DoesNotExist:
            count = 0
    else:
        count = 0
    return {'cart_items_count': count}

def user_processor(request):
    return {'current_user': request.user}