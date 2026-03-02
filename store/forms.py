from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Product, Category, Order

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Email'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Имя пользователя'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(UserRegisterForm, self).__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Пароль'
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Подтверждение пароля'
        })

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'image', 'stock', 'category', 'is_featured']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        # Делаем поле slug необязательным
        self.fields['slug'].required = False

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['delivery_method', 'payment_method']