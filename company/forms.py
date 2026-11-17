from django import forms
from company.models import Order, RecycledProduct
from users.models import EWasteCategory, CompanyProfile


class CheckoutForm(forms.ModelForm):
    same_as_billing = forms.BooleanField(required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Order
        fields = [
            'company_name', 'contact_person', 'contact_phone', 'contact_email', 'gst_tax_id',
            'billing_address', 'shipping_address', 'city', 'state', 'country', 'postal_code',
            'payment_method'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Buyer Full Name / Company Name'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Recipient / Contact Person'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@example.com'}),
            'gst_tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'GST / Tax ID (Optional for individuals)'}),
            'billing_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Billing Street Address'}),
            'shipping_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Delivery / Warehouse Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PIN / Postal Code'}),
            'payment_method': forms.Select(attrs={'class': 'form-select form-select-lg'}),
        }


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={
        'class': 'form-control text-center',
        'style': 'max-width: 100px;'
    }))


class CompanyProfileEditForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = [
            'company_name', 'registration_number', 'business_type', 'gst_tax_id',
            'corporate_address', 'city', 'state', 'country', 'postal_code',
            'logo', 'business_description'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control'}),
            'business_type': forms.Select(attrs={'class': 'form-select'}),
            'gst_tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'corporate_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
