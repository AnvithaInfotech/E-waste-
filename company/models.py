import uuid
from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils.text import slugify


class RecycledProduct(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        PUBLISHED = 'PUBLISHED', 'Published / Available'
        OUT_OF_STOCK = 'OUT_OF_STOCK', 'Out of Stock'
        UNPUBLISHED = 'UNPUBLISHED', 'Unpublished'

    class Condition(models.TextChoices):
        REFURBISHED_A = 'REFURBISHED_A', 'Refurbished - Grade A (Pristine)'
        REFURBISHED_B = 'REFURBISHED_B', 'Refurbished - Grade B (Minor Wear)'
        TESTED_WORKING = 'TESTED_WORKING', 'Tested Reusable Component'
        RAW_MATERIAL = 'RAW_MATERIAL', 'Recovered Raw Secondary Material'
        INGOT_PELLET = 'INGOT_PELLET', 'Refined Ingot / Polymer Granule'

    recycling_record = models.ForeignKey(
        'custom_admin.RecyclingRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    product_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    category = models.ForeignKey('users.EWasteCategory', on_delete=models.PROTECT, related_name='products')
    description = models.TextField()
    specifications = models.TextField(help_text="Key specifications, purity percentage, test results")
    material_type = models.CharField(max_length=150, help_text="e.g. Pure Copper 99.8%, Recovered Rare Earth, Recycled ABS")
    quantity_available = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit = models.CharField(max_length=30, default="Units", help_text="Units, kg, Metric Tons, Grams, Boxes")
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price per unit/kg in currency")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, editable=False)
    product_condition = models.CharField(
        max_length=40,
        choices=Condition.choices,
        default=Condition.REFURBISHED_A
    )
    primary_image = models.FileField(upload_to='products/')
    manufacturing_date = models.DateField(null=True, blank=True)
    origin_recycling_center = models.CharField(max_length=200, default="Central Eco-Recovery Facility #1")
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    is_featured = models.BooleanField(default=False)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.90)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.product_name)
            self.slug = f"{base_slug}-{str(uuid.uuid4())[:6]}"
        if not self.sku:
            self.sku = f"SKU-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def is_in_stock(self):
        return self.quantity_available > 0 and self.status == self.Status.PUBLISHED

    @property
    def effective_price(self):
        if self.discount_price and self.discount_price < self.price:
            return self.discount_price
        return self.price

    def __str__(self):
        return f"{self.product_name} ({self.sku}) - ₹{self.effective_price}"


class ProductImage(models.Model):
    product = models.ForeignKey(RecycledProduct, on_delete=models.CASCADE, related_name='images')
    image = models.FileField(upload_to='products/')
    caption = models.CharField(max_length=150, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.product_name}"


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def tax_amount(self):
        # 18% GST estimate for industrial goods
        return round(self.subtotal * Decimal('0.18'), 2)

    @property
    def shipping_fee(self):
        if self.subtotal == 0:
            return Decimal('0.00')
        if self.subtotal > Decimal('50000.00'):
            return Decimal('0.00')  # Free shipping on large orders
        return Decimal('1500.00')

    @property
    def grand_total(self):
        return self.subtotal + self.tax_amount + self.shipping_fee

    def __str__(self):
        return f"Cart of {self.user.username} ({self.total_items} items)"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(RecycledProduct, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product')

    @property
    def unit_price(self):
        return self.product.effective_price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.product_name}"


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = 'PLACED', 'Order Placed'
        CONFIRMED = 'CONFIRMED', 'Confirmed by Admin'
        PROCESSING = 'PROCESSING', 'Processing & Packaging'
        PACKED = 'PACKED', 'Packed & Ready'
        SHIPPED = 'SHIPPED', 'In Transit / Shipped'
        DELIVERED = 'DELIVERED', 'Delivered'
        CANCELLED = 'CANCELLED', 'Cancelled'
        COMPLETED = 'COMPLETED', 'Completed'

    class PaymentMethod(models.TextChoices):
        GPAY_UPI = 'GPAY_UPI', 'Google Pay / UPI'
        NET_BANKING = 'NET_BANKING', 'Internet Banking'
        CARD = 'CARD', 'Credit / Debit Card'
        COD = 'COD', 'Cash on Delivery (COD)'
        BANK_TRANSFER = 'BANK_TRANSFER', 'Direct Corporate Bank Transfer (NEFT/RTGS)'
        CREDIT_CARD = 'CREDIT_CARD', 'Commercial Credit / Debit Card'
        UPI_NETBANKING = 'UPI_NETBANKING', 'Corporate NetBanking / UPI'
        INVOICE_ON_DELIVERY = 'INVOICE_ON_DELIVERY', 'Net 30 Invoice on Delivery'

    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', 'Payment Pending'
        PAID = 'PAID', 'Payment Received'
        FAILED = 'FAILED', 'Payment Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    order_number = models.CharField(max_length=50, unique=True, editable=False)
    company = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_orders')
    
    # Snapshot Info
    company_name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=30)
    contact_email = models.EmailField()
    gst_tax_id = models.CharField(max_length=50, blank=True, null=True)
    
    billing_address = models.TextField()
    shipping_address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, default="India")
    postal_code = models.CharField(max_length=20)
    
    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    shipping_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Payment
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, default=PaymentMethod.BANK_TRANSFER)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    payment_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Fulfillment
    order_status = models.CharField(max_length=30, choices=Status.choices, default=Status.PLACED)
    assigned_collector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_order_deliveries'
    )
    shipping_carrier = models.CharField(max_length=100, blank=True, null=True)
    tracking_number = models.CharField(max_length=100, blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            unique_part = str(uuid.uuid4()).split('-')[0].upper()
            self.order_number = f"ORD-{unique_part}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.company_name} (₹{self.total_amount})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(RecycledProduct, on_delete=models.SET_NULL, null=True, related_name='ordered_items')
    product_name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product_name} in {self.order.order_number}"

