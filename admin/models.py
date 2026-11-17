import uuid
from django.conf import settings
from django.db import models


class RecyclingRecord(models.Model):
    class Status(models.TextChoices):
        RECEIVED = 'RECEIVED', 'Received at Center'
        SORTING = 'SORTING', 'Sorting & Dismantling'
        PROCESSING = 'PROCESSING', 'Material Processing'
        RECOVERED = 'RECOVERED', 'Raw Materials Recovered'
        PRODUCT_READY = 'PRODUCT_READY', 'Ready for Product Catalog'

    class ProcessingMethod(models.TextChoices):
        DISMANTLING = 'DISMANTLING', 'Manual Dismantling & Sorting'
        REFURBISHING = 'REFURBISHING', 'Component Refurbishment & Testing'
        SHREDDING = 'SHREDDING', 'Mechanical Shredding & Separation'
        HYDROMETALLURGICAL = 'HYDROMETALLURGICAL', 'Hydrometallurgical Chemical Leaching'
        PYROMETALLURGICAL = 'PYROMETALLURGICAL', 'Thermal / Smelting Refining'
        PLASTIC_GRANULATION = 'PLASTIC_GRANULATION', 'Plastic Polymer Granulation'

    batch_code = models.CharField(max_length=40, unique=True, editable=False)
    submission = models.ForeignKey(
        'users.EWasteSubmission',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recycling_records'
    )
    facility_name = models.CharField(max_length=200, default="Central Eco-Recovery Facility #1")
    received_date = models.DateField()
    waste_type = models.CharField(max_length=200, help_text="e.g. Printed Circuit Boards & ICs")
    original_weight_kg = models.DecimalField(max_digits=8, decimal_places=2)
    recovered_material = models.CharField(max_length=255, help_text="e.g. High-Purity Copper, Gold Flakes, ABS Plastic")
    material_category = models.ForeignKey(
        'users.EWasteCategory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recycled_materials'
    )
    processing_method = models.CharField(
        max_length=40,
        choices=ProcessingMethod.choices,
        default=ProcessingMethod.DISMANTLING
    )
    processing_description = models.TextField(help_text="Step-by-step description of extraction & refining")
    recovered_quantity = models.DecimalField(max_digits=8, decimal_places=2, help_text="Recovered volume")
    recovered_unit = models.CharField(max_length=20, default="kg", help_text="e.g. kg, grams, units, tons")
    
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.RECEIVED)
    recycling_date = models.DateField(null=True, blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_recycling_records'
    )
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.batch_code:
            unique_part = str(uuid.uuid4()).split('-')[0].upper()
            self.batch_code = f"REC-{unique_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.batch_code} - {self.recovered_material} ({self.get_status_display()})"


class SystemAuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=150)
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=100, blank=True, null=True)
    details = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} | {self.action} by {self.user}"

