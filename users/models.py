import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'USER', 'Normal User'
        COLLECTOR = 'COLLECTOR', 'Local Collector'
        ADMIN = 'ADMIN', 'Operational Admin'
        COMPANY = 'COMPANY', 'Company Buyer'
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        help_text="Primary platform role for this account"
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    profile_photo = models.FileField(upload_to='avatars/', blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_normal_user(self):
        return self.role == self.Role.USER

    @property
    def is_collector(self):
        return self.role == self.Role.COLLECTOR

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_company(self):
        return self.role == self.Role.COMPANY

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN or self.is_superuser

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_profile')
    eco_points = models.IntegerField(default=0)
    total_recycled_items = models.IntegerField(default=0)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[('PHONE', 'Phone'), ('EMAIL', 'Email'), ('SMS', 'SMS')],
        default='PHONE'
    )

    def __str__(self):
        return f"Profile of {self.user.username}"


class CollectorProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified & Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='collector_profile')
    service_area = models.CharField(max_length=150, default="City Wide")
    vehicle_type = models.CharField(max_length=100, default="Eco Transport Van")
    vehicle_number = models.CharField(max_length=50, blank=True, null=True)
    is_available = models.BooleanField(default=True)
    current_workload = models.IntegerField(default=0)
    completed_pickups_count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

    def __str__(self):
        return f"Collector: {self.user.get_full_name() or self.user.username} ({self.service_area}) [{self.get_verification_status_display()}]"


class CompanyProfile(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Verification'
        VERIFIED = 'VERIFIED', 'Verified & Approved'
        REJECTED = 'REJECTED', 'Rejected'
        SUSPENDED = 'SUSPENDED', 'Suspended'

    class BusinessType(models.TextChoices):
        MANUFACTURER = 'MANUFACTURER', 'Electronics Manufacturer'
        REFURBISHER = 'REFURBISHER', 'Hardware Refurbisher'
        MATERIAL_TRADER = 'MATERIAL_TRADER', 'Recycled Materials Trader'
        RECYCLER = 'RECYCLER', 'Smelting & Recovery Facility'
        CORPORATE = 'CORPORATE', 'Corporate Enterprise / Buyer'
        OTHER = 'OTHER', 'Other Organization'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    company_name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100)
    business_type = models.CharField(max_length=30, choices=BusinessType.choices, default=BusinessType.MANUFACTURER)
    gst_tax_id = models.CharField(max_length=50, blank=True, null=True)
    corporate_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    postal_code = models.CharField(max_length=20)
    logo = models.FileField(upload_to='logos/', blank=True, null=True)
    business_description = models.TextField(blank=True, null=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED

    def __str__(self):
        return f"{self.company_name} [{self.get_verification_status_display()}]"


class EWasteCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    icon_class = models.CharField(max_length=60, default='bi-cpu', help_text="Bootstrap icon class e.g. bi-phone, bi-laptop")
    description = models.TextField(blank=True)
    hazard_level = models.CharField(
        max_length=20,
        choices=[('LOW', 'Low Hazard'), ('MEDIUM', 'Medium Hazard'), ('HIGH', 'High Hazard / Toxic Compounds')],
        default='MEDIUM'
    )
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "E-Waste Category"
        verbose_name_plural = "E-Waste Categories"
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class EWasteSubmission(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'SUBMITTED', 'Submitted'
        UNDER_VERIFICATION = 'UNDER_VERIFICATION', 'Under Verification'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        COLLECTOR_ASSIGNED = 'COLLECTOR_ASSIGNED', 'Collector Assigned'
        PICKUP_SCHEDULED = 'PICKUP_SCHEDULED', 'Pickup Scheduled'
        ACCEPTED = 'ACCEPTED', 'Accepted by Collector'
        ON_THE_WAY = 'ON_THE_WAY', 'Collector On The Way'
        COLLECTED = 'COLLECTED', 'Collected'
        AT_RECYCLING_CENTER = 'AT_RECYCLING_CENTER', 'At Recycling Center'
        RECYCLING_IN_PROGRESS = 'RECYCLING_IN_PROGRESS', 'Recycling in Progress'
        RECYCLED = 'RECYCLED', 'Recycled'
        COMPLETED = 'COMPLETED', 'Completed'

    class Condition(models.TextChoices):
        WORKING = 'WORKING', 'Working / Functional'
        PARTIALLY_WORKING = 'PARTIAL', 'Partially Working / Defective'
        NON_FUNCTIONAL = 'NON_FUNCTIONAL', 'Non-Functional / Dead'
        SCRAP = 'SCRAP', 'Broken Scrap / Circuit Components'

    tracking_id = models.CharField(max_length=30, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ewaste_submissions')
    waste_name = models.CharField(max_length=200, help_text="e.g. Dell Latitude Laptop & Power Cable")
    category = models.ForeignKey(EWasteCategory, on_delete=models.PROTECT, related_name='submissions')
    description = models.TextField(help_text="Details, model number, specifications, defects")
    quantity = models.PositiveIntegerField(default=1)
    approximate_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, help_text="Estimated weight in kg")
    condition = models.CharField(max_length=30, choices=Condition.choices, default=Condition.NON_FUNCTIONAL)
    
    # Pickup Info
    pickup_address = models.TextField()
    pickup_city = models.CharField(max_length=100, default="")
    pickup_state = models.CharField(max_length=100, default="")
    pickup_pincode = models.CharField(max_length=20, default="")
    contact_phone = models.CharField(max_length=20)
    preferred_date = models.DateField()
    preferred_time_slot = models.CharField(
        max_length=50,
        choices=[
            ('MORNING', 'Morning (09:00 AM - 12:00 PM)'),
            ('AFTERNOON', 'Afternoon (12:00 PM - 04:00 PM)'),
            ('EVENING', 'Evening (04:00 PM - 08:00 PM)')
        ],
        default='MORNING'
    )
    additional_notes = models.TextField(blank=True, null=True)
    primary_image = models.FileField(upload_to='ewaste/', blank=True, null=True)
    
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)
    admin_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    reward_points_awarded = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            unique_part = str(uuid.uuid4()).split('-')[0].upper()
            self.tracking_id = f"EW-{unique_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tracking_id} - {self.waste_name} ({self.get_status_display()})"


class EWasteImage(models.Model):
    submission = models.ForeignKey(EWasteSubmission, on_delete=models.CASCADE, related_name='images')
    image = models.FileField(upload_to='ewaste/')
    caption = models.CharField(max_length=150, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.submission.tracking_id}"


class CollectorAssignment(models.Model):
    class AssignmentStatus(models.TextChoices):
        ASSIGNED = 'ASSIGNED', 'Assigned'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        ON_THE_WAY = 'ON_THE_WAY', 'On The Way'
        PICKED_UP = 'PICKED_UP', 'Picked Up'
        DELIVERED = 'DELIVERED', 'Delivered to Center'
        CANCELLED = 'CANCELLED', 'Cancelled'

    submission = models.OneToOneField(EWasteSubmission, on_delete=models.CASCADE, related_name='collector_assignment')
    collector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_pickups')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_assignments')
    scheduled_date = models.DateField(null=True, blank=True)
    scheduled_slot = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=30, choices=AssignmentStatus.choices, default=AssignmentStatus.ASSIGNED)
    collector_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Assignment: {self.submission.tracking_id} -> {self.collector.username} ({self.status})"


class PickupRecord(models.Model):
    assignment = models.OneToOneField(CollectorAssignment, on_delete=models.CASCADE, related_name='pickup_record')
    submission = models.ForeignKey(EWasteSubmission, on_delete=models.CASCADE, related_name='pickup_records')
    collector = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pickup_records')
    collected_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    proof_image = models.FileField(upload_to='proofs/', blank=True, null=True)
    verified_weight_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    collector_remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pickup Record for {self.submission.tracking_id}"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = 'INFO', 'Information'
        SUCCESS = 'SUCCESS', 'Success'
        WARNING = 'WARNING', 'Warning'
        DANGER = 'DANGER', 'Alert'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification to {self.user.username}: {self.title}"

