import random
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from company.models import RecycledProduct, Cart, CartItem, Order, OrderItem
from users.models import CompanyProfile
from company.forms import CheckoutForm, AddToCartForm, CompanyProfileEditForm
from users.models import EWasteCategory, User
from users.decorators import company_required, send_system_notification


# -------------------------------------------------------------------
# MARKETPLACE & STOREFRONT VIEWS
# -------------------------------------------------------------------

def marketplace_home_view(request):
    featured_products = RecycledProduct.objects.filter(
        status=RecycledProduct.Status.PUBLISHED,
        is_featured=True
    )[:6]
    
    recent_products = RecycledProduct.objects.filter(
        status=RecycledProduct.Status.PUBLISHED
    ).order_by('-created_at')[:8]

    categories = EWasteCategory.objects.filter(is_active=True)

    materials = RecycledProduct.objects.filter(
        status=RecycledProduct.Status.PUBLISHED
    ).values_list('material_type', flat=True).distinct()[:10]

    context = {
        'featured_products': featured_products,
        'recent_products': recent_products,
        'categories': categories,
        'materials': materials,
    }
    return render(request, 'marketplace/home.html', context)


def product_list_view(request):
    products = RecycledProduct.objects.filter(status=RecycledProduct.Status.PUBLISHED)
    categories = EWasteCategory.objects.filter(is_active=True)

    # Filters
    category_slug = request.GET.get('category')
    condition = request.GET.get('condition')
    material = request.GET.get('material')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    query = request.GET.get('q')
    sort_by = request.GET.get('sort', 'newest')

    if category_slug:
        products = products.filter(category__slug=category_slug)
    if condition:
        products = products.filter(product_condition=condition)
    if material:
        products = products.filter(material_type__icontains=material)
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except:
            pass
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except:
            pass
    if query:
        products = products.filter(
            Q(product_name__icontains=query) |
            Q(description__icontains=query) |
            Q(material_type__icontains=query) |
            Q(specifications__icontains=query) |
            Q(sku__icontains=query)
        )

    # Sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'popular':
        products = products.order_by('-rating', '-created_at')
    else:
        products = products.order_by('-created_at')

    conditions = RecycledProduct.Condition.choices

    context = {
        'products': products,
        'categories': categories,
        'conditions': conditions,
        'selected_category': category_slug,
        'selected_condition': condition,
        'selected_material': material,
        'min_price': min_price,
        'max_price': max_price,
        'query': query,
        'sort_by': sort_by,
        'total_count': products.count(),
    }
    return render(request, 'marketplace/product_list.html', context)


def product_detail_view(request, slug):
    product = get_object_or_404(RecycledProduct, slug=slug, status=RecycledProduct.Status.PUBLISHED)
    related_products = RecycledProduct.objects.filter(
        category=product.category,
        status=RecycledProduct.Status.PUBLISHED
    ).exclude(id=product.id)[:4]

    form = AddToCartForm()
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'related_products': related_products,
        'form': form
    })


# -------------------------------------------------------------------
# CART & CHECKOUT VIEWS
# -------------------------------------------------------------------

@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product').all()
    return render(request, 'marketplace/cart.html', {'cart': cart, 'items': items})


@login_required
def add_to_cart_view(request, product_id):
    product = get_object_or_404(RecycledProduct, id=product_id, status=RecycledProduct.Status.PUBLISHED)
    cart, _ = Cart.objects.get_or_create(user=request.user)
    
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    if quantity < 1:
        quantity = 1

    # Check available stock
    available = int(product.quantity_available)
    if available <= 0:
        messages.error(request, f"Sorry, '{product.product_name}' is currently out of stock.")
        return redirect('product_detail', slug=product.slug)

    if quantity > available:
        messages.error(
            request,
            f"Alert: Cannot add {quantity} units of '{product.product_name}'. Only {available} {product.unit} available in stock!"
        )
        return redirect('product_detail', slug=product.slug)

    is_buy_now = request.POST.get('buy_now') == '1'

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if is_buy_now:
        cart_item.quantity = quantity
    else:
        if not created:
            if cart_item.quantity + quantity > available:
                messages.error(
                    request,
                    f"Alert: Cannot add {quantity} more. You already have {cart_item.quantity} in cart and only {available} {product.unit} available in stock!"
                )
                return redirect('cart')
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
    cart_item.save()

    if is_buy_now:
        return redirect('checkout')

    messages.success(request, f"Added {quantity} x '{product.product_name}' to your cart.")
    return redirect('cart')


@login_required
def update_cart_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    action = request.POST.get('action')
    available = int(cart_item.product.quantity_available)
    
    if action == 'increase':
        if cart_item.quantity + 1 > available:
            messages.warning(
                request,
                f"Alert: Cannot increase quantity. Only {available} {cart_item.product.unit} available in stock!"
            )
        else:
            cart_item.quantity += 1
            cart_item.save()
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            messages.info(request, "Item removed from cart.")
            return redirect('cart')
    elif action == 'set':
        try:
            qty = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            qty = 1

        if qty > available:
            messages.warning(
                request,
                f"Alert: Quantity capped to maximum available stock of {available} {cart_item.product.unit}."
            )
            cart_item.quantity = available
            cart_item.save()
        elif qty > 0:
            cart_item.quantity = qty
            cart_item.save()
        else:
            cart_item.delete()
    return redirect('cart')


@login_required
def remove_from_cart_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.info(request, "Item removed from cart.")
    return redirect('cart')


@login_required
def checkout_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product').all()

    if not items.exists():
        messages.warning(request, "Your cart is empty. Add recycled products to begin checkout.")
        return redirect('product_list')

    # Verify inventory availability before checkout
    for item in items:
        if item.quantity > item.product.quantity_available:
            messages.error(
                request,
                f"Alert: '{item.product.product_name}' only has {int(item.product.quantity_available)} in stock, but your cart has {item.quantity}. Please adjust your quantity."
            )
            return redirect('cart')

    if request.user.role == User.Role.COMPANY:
        profile = getattr(request.user, 'company_profile', None)
        company_name_val = (profile.company_name if profile else '') or request.user.get_full_name() or request.user.username
        gst_tax_id_val = profile.gst_tax_id if profile else ''
        address_val = (profile.corporate_address if profile else '') or request.user.address or ''
        city_val = (profile.city if profile else '') or request.user.city or ''
        state_val = (profile.state if profile else '') or request.user.state or ''
        country_val = (profile.country if profile else '') or 'India'
        postal_code_val = (profile.postal_code if profile else '') or request.user.pincode or ''
    else:
        profile = None
        company_name_val = request.user.get_full_name() or request.user.username
        gst_tax_id_val = ''
        address_val = request.user.address or ''
        city_val = request.user.city or ''
        state_val = request.user.state or ''
        country_val = 'India'
        postal_code_val = request.user.pincode or ''

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.company = request.user
            order.subtotal = cart.subtotal
            order.tax_amount = cart.tax_amount
            order.shipping_fee = cart.shipping_fee
            order.total_amount = cart.grand_total
            order.order_status = Order.Status.PLACED
            order.payment_status = Order.PaymentStatus.PENDING
            if not order.country:
                order.country = "India"
            order.save()

            # Create order items
            for item in items:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    product_name=item.product.product_name,
                    sku=item.product.sku,
                    unit_price=item.product.effective_price,
                    quantity=item.quantity,
                    total_price=item.total_price
                )
                # Deduct inventory
                if item.product.quantity_available >= item.quantity:
                    item.product.quantity_available -= item.quantity
                    if item.product.quantity_available == 0:
                        item.product.status = RecycledProduct.Status.OUT_OF_STOCK
                    item.product.save()

            # Clear cart
            cart.items.all().delete()

            # Notify operational admins of order placement
            for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                send_system_notification(
                    user=admin_user,
                    title="New Order Placed - Assign Delivery",
                    message=f"Order {order.order_number} placed by {order.company_name} (₹{order.total_amount}). Please assign a local collector for delivery fulfillment.",
                    link=f"/admin-panel/orders/{order.id}/",
                    notification_type="INFO"
                )

            # Route to realistic Payment Gateway for payment processing
            return redirect('payment_gateway', order_id=order.id)
        else:
            messages.error(request, "Please correct the highlighted errors in the checkout form.")
    else:
        initial_data = {
            'company_name': company_name_val,
            'contact_person': request.user.get_full_name() or request.user.username,
            'contact_phone': request.user.phone or '',
            'contact_email': request.user.email or '',
            'gst_tax_id': gst_tax_id_val,
            'billing_address': address_val,
            'shipping_address': address_val,
            'city': city_val,
            'state': state_val,
            'country': country_val,
            'postal_code': postal_code_val,
        }
        form = CheckoutForm(initial=initial_data)

    return render(request, 'marketplace/checkout.html', {
        'cart': cart,
        'items': items,
        'form': form,
        'profile': profile
    })


@login_required
def payment_gateway_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, company=request.user)
    items = order.items.select_related('product').all()

    if order.payment_status == Order.PaymentStatus.PAID:
        return redirect('order_success', order_id=order.id)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', 'GPAY_UPI')
        txn_ref = f"TXN_{int(timezone.now().timestamp())}{random.randint(1000, 9999)}"

        if payment_method == 'COD':
            order.payment_method = Order.PaymentMethod.COD
            order.payment_status = Order.PaymentStatus.PENDING
            order.payment_transaction_id = f"COD-AUTH-{int(timezone.now().timestamp())}"
            messages.success(request, "Order confirmed with Cash on Delivery / Pay on Delivery!")
        else:
            if payment_method in [c[0] for c in Order.PaymentMethod.choices]:
                order.payment_method = payment_method
            else:
                order.payment_method = Order.PaymentMethod.GPAY_UPI
            order.payment_status = Order.PaymentStatus.PAID
            order.payment_transaction_id = txn_ref
            messages.success(request, f"Payment of ₹{order.total_amount} processed successfully via {order.get_payment_method_display()}!")

        order.save()

        # Multi-party notifications
        send_system_notification(
            user=request.user,
            title=f"Payment Received: {order.order_number}",
            message=f"Thank you! Your payment of ₹{order.total_amount} was confirmed ({order.get_payment_method_display()}). Ref: {order.payment_transaction_id}.",
            link=f"/company/orders/{order.id}/",
            notification_type="SUCCESS"
        )

        for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
            send_system_notification(
                user=admin_user,
                title=f"Payment Cleared: {order.order_number}",
                message=f"Payment of ₹{order.total_amount} cleared by {order.company_name} ({order.get_payment_method_display()}).",
                link=f"/admin-panel/orders/{order.id}/",
                notification_type="SUCCESS"
            )

        return redirect('order_success', order_id=order.id)

    context = {
        'order': order,
        'items': items,
    }
    return render(request, 'marketplace/payment_gateway.html', context)


@login_required
def order_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, company=request.user)
    items = order.items.select_related('product').all()
    return render(request, 'marketplace/order_success.html', {'order': order, 'items': items})


# -------------------------------------------------------------------
# COMPANY DASHBOARD & ORDERS
# -------------------------------------------------------------------

@login_required
@company_required
def company_dashboard_view(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    orders = Order.objects.filter(company=request.user)

    total_orders = orders.count()
    active_orders = orders.filter(order_status__in=[
        Order.Status.PLACED, Order.Status.CONFIRMED, Order.Status.PROCESSING,
        Order.Status.PACKED, Order.Status.SHIPPED
    ]).count()

    total_spend = orders.filter(
        payment_status__in=[Order.PaymentStatus.PAID, Order.PaymentStatus.PENDING]
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    recent_orders = orders.order_by('-created_at')[:5]

    context = {
        'profile': profile,
        'total_orders': total_orders,
        'active_orders': active_orders,
        'total_spend': total_spend,
        'recent_orders': recent_orders,
    }
    return render(request, 'company/dashboard.html', context)


@login_required
def company_orders_list_view(request):
    orders = Order.objects.filter(company=request.user).order_by('-created_at')
    return render(request, 'company/orders.html', {'orders': orders})


@login_required
def company_order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, company=request.user)
    items = order.items.all()

    # Timeline checkpoints
    order_stages = [
        ('PLACED', 'Order Placed', True),
        ('CONFIRMED', 'Confirmed', order.order_status not in ['PLACED', 'CANCELLED']),
        ('PROCESSING', 'Processing & Packaging', order.order_status in ['PROCESSING', 'PACKED', 'SHIPPED', 'DELIVERED', 'COMPLETED']),
        ('PACKED', 'Packed', order.order_status in ['PACKED', 'SHIPPED', 'DELIVERED', 'COMPLETED']),
        ('SHIPPED', 'Shipped / In Transit', order.order_status in ['SHIPPED', 'DELIVERED', 'COMPLETED']),
        ('DELIVERED', 'Delivered', order.order_status in ['DELIVERED', 'COMPLETED']),
    ]

    return render(request, 'company/order_detail.html', {
        'order': order,
        'items': items,
        'order_stages': order_stages
    })


@login_required
@company_required
def company_profile_view(request):
    profile, _ = CompanyProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = CompanyProfileEditForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Company profile updated successfully.")
            return redirect('company_profile')
    else:
        form = CompanyProfileEditForm(instance=profile)

    return render(request, 'company/profile.html', {'form': form, 'profile': profile})
