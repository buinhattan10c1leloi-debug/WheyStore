from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['user_name', 'rating', 'comment']
        widgets = {
            'user_name': forms.TextInput(attrs={
                'class': 'fitness-input',
                'placeholder': 'Nhập tên của bạn (VD: Minh Tuấn - Gymer)',
            }),
            'rating': forms.Select(attrs={
                'class': 'fitness-select',
            }),
            'comment': forms.Textarea(attrs={
                'class': 'fitness-textarea',
                'rows': 3,
                'placeholder': 'Chia sẻ cảm nhận về độ tan, mùi vị và hiệu quả phục hồi cơ bắp...',
            }),
        }
