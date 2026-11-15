import re
from django import forms
from .models import Order


def normalize_vn_phone(raw_phone: str) -> str:
    """Chuẩn hóa SĐT Việt Nam: bỏ khoảng trắng/dấu gạch, chuyển +84xxxx -> 0xxxx."""
    cleaned = re.sub(r'[\s\-\.]', '', (raw_phone or '').strip())
    if cleaned.startswith('+84'):
        cleaned = '0' + cleaned[3:]
    return cleaned


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

    def clean_full_name(self):
        name = (self.cleaned_data.get('full_name') or '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Họ và tên phải có ít nhất 2 ký tự.")
        return name

    def clean_phone(self):
        raw = (self.cleaned_data.get('phone') or '').strip()
        cleaned = re.sub(r'[\s\-\.]', '', raw)
        if not re.match(r'^(0|\+84)\d{9}$', cleaned):
            raise forms.ValidationError("Số điện thoại không hợp lệ (VD: 0987654321 hoặc +84987654321).")
        return normalize_vn_phone(cleaned)

    def clean_address(self):
        addr = (self.cleaned_data.get('address') or '').strip()
        if len(addr) < 5:
            raise forms.ValidationError("Địa chỉ nhận hàng phải có ít nhất 5 ký tự.")
        return addr

    def clean_city(self):
        city = (self.cleaned_data.get('city') or '').strip()
        if len(city) < 2:
            raise forms.ValidationError("Vui lòng nhập Tỉnh / Thành phố hợp lệ.")
        return city
