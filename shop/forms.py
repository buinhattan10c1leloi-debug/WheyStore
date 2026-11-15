from django import forms
from .models import Review, Product


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


class ProductManageForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'category', 'name', 'slug', 'brand', 'goal', 'image',
            'price', 'old_price', 'weight', 'servings',
            'protein_per_serving', 'bcaa_per_serving', 'calories', 'sugar',
            'flavor', 'origin', 'free_gift', 'stock', 'available', 'description'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'fitness-textarea'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.FileInput, forms.Textarea)):
                field.widget.attrs.setdefault('class', 'fitness-input')
