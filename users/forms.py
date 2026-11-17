from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from users.models import (
    User, UserProfile, CollectorProfile, CompanyProfile, 
    EWasteSubmission, EWasteCategory, PickupRecord, CollectorAssignment
)


class UserLoginForm(forms.Form):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your password'
        })
    )


class UserRegistrationForm(forms.ModelForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose Username', 'autofocus': True}),
        help_text="Unique username for your account"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.com'}),
        help_text="We will send collection updates to this email"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create secure password'}),
        min_length=6,
        help_text="Minimum 6 characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        help_text="Re-enter your password to confirm"
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another username.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.USER
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)
        return user


class CompanyRegistrationForm(forms.ModelForm):
    # User account fields
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. greentech_buyer'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'procurement@company.com'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create secure password'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    contact_person = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Official Contact Person Name'})
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Corporate Phone Number'})
    )

    class Meta:
        model = CompanyProfile
        fields = [
            'company_name', 'registration_number', 'business_type', 'gst_tax_id',
            'corporate_address', 'city', 'state', 'country', 'postal_code',
            'logo', 'business_description'
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. GreenTech Recyclers Pvt Ltd'}),
            'registration_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CIN / Reg No U72200MH2021PTC123456'}),
            'business_type': forms.Select(attrs={'class': 'form-select'}),
            'gst_tax_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 27AAAAA0000A1Z5'}),
            'corporate_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Corporate HQ Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PIN / Postal Code'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'business_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe your procurement requirements, factory materials needed, etc.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('country'):
            self.initial['country'] = 'India'

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another username.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address is already registered.")
        return email

    def clean_registration_number(self):
        reg = self.cleaned_data.get('registration_number')
        if CompanyProfile.objects.filter(registration_number__iexact=reg).exists():
            raise forms.ValidationError("A company with this Registration / CIN number is already registered.")
        return reg

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        username = self.cleaned_data['username']
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        contact_person = self.cleaned_data['contact_person']
        phone = self.cleaned_data['phone']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=contact_person,
            phone=phone,
            role=User.Role.COMPANY
        )

        company_profile = super().save(commit=False)
        company_profile.user = user
        if commit:
            company_profile.save()
        return user


class CollectorRegistrationForm(forms.ModelForm):
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name', 'autofocus': True})
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose Username'}),
        help_text="Unique username for your collector account"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'collector@example.com'}),
        help_text="Official email for operational assignments"
    )
    phone = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
        help_text="Direct mobile number for pickup coordination"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create secure password'}),
        min_length=6,
        help_text="Minimum 6 characters"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Operating base / depot address'})
    )
    city = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Operating City'})
    )
    state = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'})
    )
    pincode = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal PIN Code'})
    )

    class Meta:
        model = CollectorProfile
        fields = ['service_area', 'vehicle_type', 'vehicle_number']
        widgets = {
            'service_area': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Metro North & Tech Zone'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Electric Cargo Van / Light Truck'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. MH-02-EV-1234'}),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose another username.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        username = self.cleaned_data['username']
        email = self.cleaned_data['email']
        password = self.cleaned_data['password']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data.get('last_name', '')
        phone = self.cleaned_data['phone']
        address = self.cleaned_data.get('address', '')
        city = self.cleaned_data['city']
        state = self.cleaned_data['state']
        pincode = self.cleaned_data['pincode']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            address=address,
            city=city,
            state=state,
            pincode=pincode,
            role=User.Role.COLLECTOR
        )

        collector_profile = super().save(commit=False)
        collector_profile.user = user
        collector_profile.verification_status = CollectorProfile.VerificationStatus.PENDING
        if commit:
            collector_profile.save()
        return user


class EWasteSubmissionForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )

    class Meta:
        model = EWasteSubmission
        fields = [
            'waste_name', 'category', 'description', 'quantity', 'approximate_weight_kg',
            'condition', 'pickup_address', 'pickup_city', 'pickup_state', 'pickup_pincode',
            'contact_phone', 'preferred_date', 'preferred_time_slot', 'additional_notes',
            'primary_image'
        ]
        widgets = {
            'waste_name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'e.g. Old HP Pavilion Laptop + 2 CRT Monitors'
            }),
            'category': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Include brand, model, components included (e.g. charger, cables), known defects'
            }),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'approximate_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Approx weight in kg (e.g. 3.5)'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'pickup_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Full pickup address, street, landmark'}),
            'pickup_city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'pickup_state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pickup_pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Postal PIN'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91 9876543210'}),
            'preferred_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'preferred_time_slot': forms.Select(attrs={'class': 'form-select'}),
            'additional_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Any special instructions for collector'}),
            'primary_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CollectorPickupExecutionForm(forms.ModelForm):
    class Meta:
        model = PickupRecord
        fields = ['proof_image', 'verified_weight_kg', 'collector_remarks']
        widgets = {
            'proof_image': forms.FileInput(attrs={'class': 'form-control'}),
            'verified_weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'placeholder': 'Actual verified scale weight (kg)'}),
            'collector_remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Notes on item condition, package seal ID, etc.'}),
        }


class UserProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'pincode', 'bio', 'profile_photo']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'profile_photo': forms.FileInput(attrs={'class': 'form-control'}),
        }


class CollectorAvailabilityForm(forms.ModelForm):
    class Meta:
        model = CollectorProfile
        fields = ['is_available', 'service_area', 'vehicle_type', 'vehicle_number']
        widgets = {
            'is_available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'service_area': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_type': forms.TextInput(attrs={'class': 'form-control'}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control'}),
        }
