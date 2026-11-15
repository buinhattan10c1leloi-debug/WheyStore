from django import forms
from .models import Order


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'full_name',
            'phone',
            'email',
            'address',
            'city',
            'note',
            'payment_method',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'fitness-input',
                'placeholder': 'Nhập họ và tên người nhận (VD: Nguyễn Văn A)',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'fitness-input',
                'placeholder': 'Nhập số điện thoại liên hệ (VD: 0987654321)',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'fitness-input',
                'placeholder': 'Nhập email nhận thông báo (không bắt buộc)',
            }),
            'address': forms.TextInput(attrs={
                'class': 'fitness-input',
                'placeholder': 'Số nhà, tên đường, phường/xã, quận/huyện',
            }),
            'city': forms.TextInput(attrs={
                'class': 'fitness-input',
                'placeholder': 'Tỉnh / Thành phố (VD: TP. Hồ Chí Minh, Hà Nội)',
            }),
            'note': forms.Textarea(attrs={
                'class': 'fitness-textarea',
                'rows': 3,
                'placeholder': 'Ghi chú thêm khi giao hàng (giờ hành chính, gọi trước khi giao...)',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'fitness-select',
            }),
        }
