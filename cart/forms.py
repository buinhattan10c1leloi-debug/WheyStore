from django import forms

PRODUCT_QUANTITY_CHOICES = [(i, str(i)) for i in range(1, 11)]


class CartAddProductForm(forms.Form):
    quantity = forms.TypedChoiceField(
        choices=PRODUCT_QUANTITY_CHOICES,
        coerce=int,
        label='Số lượng',
        widget=forms.Select(attrs={'class': 'quantity-select'})
    )
    override = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput
    )


class CouponApplyForm(forms.Form):
    code = forms.CharField(
        max_length=50,
        label='Mã giảm giá',
        widget=forms.TextInput(attrs={
            'class': 'fitness-input coupon-input',
            'placeholder': 'Nhập mã giảm giá (VD: GYMBRO10, WHEYVIP20)',
        })
    )
