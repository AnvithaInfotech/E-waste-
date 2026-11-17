from django import forms
from django.utils import timezone
from users.models import User, EWasteCategory, EWasteSubmission, CollectorAssignment, CollectorProfile, CompanyProfile
from admin.models import RecyclingRecord
from company.models import RecycledProduct, Order


class EWasteVerificationForm(forms.Form):
    ACTION_CHOICES = [
        ('APPROVE', 'Approve Submission'),
        ('REJECT', 'Reject Submission'),
        ('REQUEST_INFO', 'Mark as Under Verification (Request More Info)'),
    ]
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.RadioSelect(attrs={'class': 'form-check-input'}))
    reward_points = forms.IntegerField(
        initial=50,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': 'Eco-Points to award user'})
    )
    collector = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role=User.Role.COLLECTOR,
            is_active=True,
            collector_profile__verification_status=CollectorProfile.VerificationStatus.VERIFIED
        ),
        required=False,
        empty_label="-- Leave Unassigned (Optional) --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    scheduled_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Internal verification notes'})
    )
    collector_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes for assigned collector'})
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Reason sent to user if rejected'})
    )


class AssignCollectorForm(forms.ModelForm):
    collector = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role=User.Role.COLLECTOR,
            is_active=True,
            collector_profile__verification_status=CollectorProfile.VerificationStatus.VERIFIED
        ),
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'})
    )

    class Meta:
        model = CollectorAssignment
        fields = ['collector', 'scheduled_date', 'scheduled_slot', 'collector_notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'scheduled_slot': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10:00 AM - 01:00 PM'}),
            'collector_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Instructions for the collector'}),
        }


class RecyclingRecordForm(forms.ModelForm):
    class Meta:
        model = RecyclingRecord
        fields = [
            'submission', 'facility_name', 'received_date', 'waste_type', 'original_weight_kg',
            'recovered_material', 'material_category', 'processing_method',
            'processing_description', 'recovered_quantity', 'recovered_unit',
            'status', 'recycling_date', 'notes'
        ]
        widgets = {
            'submission': forms.Select(attrs={'class': 'form-select'}),
            'facility_name': forms.TextInput(attrs={'class': 'form-control'}),
            'received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'waste_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Laptop Motherboards & RAM sticks'}),
            'original_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'recovered_material': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Refined Copper 99.8% & Gold Pins'}),
            'material_category': forms.Select(attrs={'class': 'form-select'}),
            'processing_method': forms.Select(attrs={'class': 'form-select'}),
            'processing_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detail dismantling, smelting, testing steps'}),
            'recovered_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'recovered_unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kg, grams, units'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'recycling_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ProductCreationForm(forms.ModelForm):
    class Meta:
        model = RecycledProduct
        fields = [
            'product_name', 'category', 'recycling_record', 'material_type', 'product_condition',
            'quantity_available', 'unit', 'price', 'discount_price', 'primary_image',
            'origin_recycling_center', 'status', 'is_featured', 'description', 'specifications'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'e.g. Recovered High Purity Copper Wire (99.8%)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'recycling_record': forms.Select(attrs={'class': 'form-select'}),
            'material_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Pure Copper / Gold Contacts / Refurbished PC'}),
            'product_condition': forms.Select(attrs={'class': 'form-select'}),
            'quantity_available': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'kg / Units / Tons'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Price in ₹'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Discounted Price in ₹ (optional)'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control'}),
            'origin_recycling_center': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Purity: 99.8%\nForm: Coil\nOrigin: Recycled Server Cables\nQuality Test: Passed ISO-14001'}),
        }


class ProductEditForm(forms.ModelForm):
    class Meta:
        model = RecycledProduct
        fields = [
            'product_name', 'category', 'material_type', 'product_condition',
            'quantity_available', 'unit', 'price', 'discount_price', 'primary_image',
            'origin_recycling_center', 'status', 'is_featured', 'description', 'specifications'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product title'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'material_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Material Type'}),
            'product_condition': forms.Select(attrs={'class': 'form-select'}),
            'quantity_available': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'unit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Units / kg'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'discount_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control'}),
            'origin_recycling_center': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'specifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['primary_image'].required = False



class AdminOrderUpdateForm(forms.ModelForm):
    assigned_collector = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role=User.Role.COLLECTOR,
            is_active=True,
            collector_profile__verification_status=CollectorProfile.VerificationStatus.VERIFIED
        ).order_by('first_name', 'username'),
        required=False,
        empty_label="-- Select Local Collector for Delivery --",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Order
        fields = ['order_status', 'assigned_collector', 'payment_status', 'shipping_carrier', 'tracking_number', 'admin_notes']
        widgets = {
            'order_status': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'shipping_carrier': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Green Express Logistics'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. TRK-2026-98124'}),
            'admin_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CollectorCreationForm(forms.Form):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    service_area = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Metro North Zone'}))
    vehicle_type = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electric Cargo Van'}))
    vehicle_number = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MH-02-EC-1092'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address is already registered.")
        return email

    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data.get('last_name', ''),
            phone=self.cleaned_data['phone'],
            role=User.Role.COLLECTOR
        )
        CollectorProfile.objects.create(
            user=user,
            service_area=self.cleaned_data['service_area'],
            vehicle_type=self.cleaned_data['vehicle_type'],
            vehicle_number=self.cleaned_data.get('vehicle_number', ''),
            verification_status=CollectorProfile.VerificationStatus.VERIFIED,
            verified_at=timezone.now()
        )
        return user


class CompanyVerificationForm(forms.ModelForm):
    class Meta:
        model = CompanyProfile
        fields = ['verification_status', 'rejection_reason']
        widgets = {
            'verification_status': forms.Select(attrs={'class': 'form-select'}),
            'rejection_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'State reason if rejected or suspended'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = EWasteCategory
        fields = ['name', 'icon_class', 'description', 'hazard_level', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'icon_class': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. bi-phone, bi-laptop, bi-motherboard'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'hazard_level': forms.Select(attrs={'class': 'form-select'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AdminOrderPlacementForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.COMPANY).select_related('company_profile').order_by('first_name', 'username'),
        empty_label="-- Select Purchasing Company * --",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_company_select'})
    )
    product = forms.ModelChoiceField(
        queryset=RecycledProduct.objects.filter(status=RecycledProduct.Status.PUBLISHED, quantity_available__gt=0).order_by('product_name'),
        empty_label="-- Select Recycled Product / Secondary Material * --",
        widget=forms.Select(attrs={'class': 'form-select form-select-lg', 'id': 'id_product_select'})
    )
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-lg fw-bold text-center', 'id': 'id_quantity_input', 'min': '1'})
    )
    assigned_collector = forms.ModelChoiceField(
        queryset=User.objects.filter(
            role=User.Role.COLLECTOR,
            is_active=True,
            collector_profile__verification_status=CollectorProfile.VerificationStatus.VERIFIED
        ).order_by('first_name', 'username'),
        required=False,
        empty_label="-- Select Local Collector for Delivery (Optional) --",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_assigned_collector'})
    )

    # Corporate Snapshot Details
    company_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_company_name', 'placeholder': 'Registered Company Name'}))
    contact_person = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contact_person', 'placeholder': 'Procurement Officer Name'}))
    contact_phone = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_contact_phone', 'placeholder': '+91 9876543210'}))
    contact_email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'id': 'id_contact_email', 'placeholder': 'corporate@company.com'}))
    gst_tax_id = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_gst_tax_id', 'placeholder': 'GSTIN Number (Optional)'}))

    # Delivery & Billing Addresses
    billing_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'id': 'id_billing_address', 'placeholder': 'Registered Billing Address'}))
    shipping_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'id': 'id_shipping_address', 'placeholder': 'Delivery Warehouse Address'}))
    city = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_city'}))
    state = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_state'}))
    country = forms.CharField(initial='India', widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_country'}))
    postal_code = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'id_postal_code'}))

    # Payment & Logistics
    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        initial=Order.PaymentMethod.BANK_TRANSFER,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_status = forms.ChoiceField(
        choices=Order.PaymentStatus.choices,
        initial=Order.PaymentStatus.PENDING,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    order_status = forms.ChoiceField(
        choices=Order.Status.choices,
        initial=Order.Status.PLACED,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Special logistics handling, carrier instructions, or purchase order reference'})
    )
