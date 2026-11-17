from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from users.models import User, EWasteCategory, CompanyProfile, CollectorProfile
from company.models import RecycledProduct, Cart, CartItem, Order, OrderItem


class MarketplaceAndCompanyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = EWasteCategory.objects.create(name="Secondary Metals", icon_class="bi-cpu")
        self.product = RecycledProduct.objects.create(
            product_name="Recycled Copper Ingot 99.8%",
            category=self.category,
            material_type="Pure Copper",
            quantity_available=Decimal("100.00"),
            unit="kg",
            price=Decimal("800.00"),
            product_condition=RecycledProduct.Condition.RAW_MATERIAL,
            status=RecycledProduct.Status.PUBLISHED,
            description="Pure copper ingot",
            specifications="99.8% purity"
        )
        self.company_user = User.objects.create_user(
            username="greenmetal",
            password="password123",
            role=User.Role.COMPANY,
            first_name="Rohan",
            phone="9876543210"
        )
        self.company_profile = CompanyProfile.objects.create(
            user=self.company_user,
            company_name="Green Metal Recyclers",
            registration_number="REG-9912",
            corporate_address="Industrial Area",
            city="Pune",
            state="Maharashtra",
            postal_code="411001",
            verification_status=CompanyProfile.VerificationStatus.VERIFIED
        )

    def test_marketplace_listing_and_detail(self):
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recycled Copper Ingot 99.8%")

        response = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "800.00")

    def test_cart_operations(self):
        self.client.login(username="greenmetal", password="password123")
        
        # Add to cart
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]), {'quantity': 5}, follow=True)
        self.assertEqual(response.status_code, 200)

        cart = Cart.objects.get(user=self.company_user)
        self.assertEqual(cart.total_items, 5)
        self.assertEqual(cart.subtotal, Decimal("4000.00"))

    def test_checkout_and_order_creation(self):
        self.client.login(username="greenmetal", password="password123")
        cart = Cart.objects.create(user=self.company_user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)

        response = self.client.post(reverse('checkout'), {
            'company_name': 'Green Metal Recyclers',
            'contact_person': 'Rohan',
            'contact_phone': '9876543210',
            'contact_email': 'rohan@greenmetal.com',
            'gst_tax_id': '27AAACG1234H1Z5',
            'billing_address': 'Industrial Area',
            'shipping_address': 'Industrial Area',
            'city': 'Pune',
            'state': 'Maharashtra',
            'country': 'India',
            'postal_code': '411001',
            'payment_method': Order.PaymentMethod.BANK_TRANSFER
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        order = Order.objects.filter(company=self.company_user).first()
        self.assertIsNotNone(order)
        self.assertTrue(order.order_number.startswith("ORD-"))
        self.assertEqual(order.items.count(), 1)
        
    def test_stock_limit_alert_and_prevention(self):
        # Product with only 1 unit in stock
        scarce_product = RecycledProduct.objects.create(
            product_name="Refurbished Laptop Core i7",
            category=self.category,
            material_type="Electronics",
            quantity_available=Decimal("1.00"),
            unit="Unit",
            price=Decimal("25000.00"),
            product_condition=RecycledProduct.Condition.REFURBISHED_A,
            status=RecycledProduct.Status.PUBLISHED,
            description="Refurbished laptop",
            specifications="16GB RAM, 512GB SSD"
        )
        self.client.login(username="greenmetal", password="password123")

        # Attempt to add 2 units when only 1 is available
        response = self.client.post(reverse('add_to_cart', args=[scarce_product.id]), {'quantity': 2}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 1 Unit available in stock")

        # Verify nothing was added
        cart = Cart.objects.get(user=self.company_user)
        self.assertEqual(cart.items.filter(product=scarce_product).count(), 0)

        # Now add 1 unit (allowed)
        response = self.client.post(reverse('add_to_cart', args=[scarce_product.id]), {'quantity': 1}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cart.items.get(product=scarce_product).quantity, 1)

        # Now try to increase in cart beyond stock
        item = cart.items.get(product=scarce_product)
        response = self.client.post(reverse('update_cart', args=[item.id]), {'action': 'increase'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 1 Unit available in stock")
        item.refresh_from_db()
        self.assertEqual(item.quantity, 1)

    def test_admin_assigns_collector_and_collector_delivers(self):
        admin_user = User.objects.create_user(
            username="op_admin", password="password123", role=User.Role.ADMIN
        )
        collector_user = User.objects.create_user(
            username="fleet_raj", password="password123", role=User.Role.COLLECTOR,
            first_name="Rajesh", phone="9988776655"
        )
        CollectorProfile.objects.create(
            user=collector_user,
            service_area="Pune City",
            verification_status=CollectorProfile.VerificationStatus.VERIFIED
        )
        order = Order.objects.create(
            company=self.company_user,
            company_name="Green Metal Recyclers",
            contact_person="Rohan",
            contact_phone="9876543210",
            contact_email="rohan@greenmetal.com",
            billing_address="Industrial Area",
            shipping_address="Industrial Area",
            city="Pune",
            state="Maharashtra",
            country="India",
            postal_code="411001",
            subtotal=Decimal("800.00"),
            total_amount=Decimal("944.00"),
            order_status=Order.Status.PLACED
        )

        # Admin assigns collector
        self.client.login(username="op_admin", password="password123")
        response = self.client.post(reverse('admin_order_detail', args=[order.id]), {
            'order_status': Order.Status.CONFIRMED,
            'assigned_collector': collector_user.id,
            'payment_status': Order.PaymentStatus.PENDING,
            'shipping_carrier': 'Eco Express Fleet',
            'tracking_number': 'TRK-99001',
            'admin_notes': 'Assigned to Rajesh for delivery.'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.assigned_collector, collector_user)

        # Collector views dashboard and completes delivery
        self.client.login(username="fleet_raj", password="password123")
        dash_response = self.client.get(reverse('collector_dashboard'))
        self.assertEqual(dash_response.status_code, 200)
        self.assertContains(dash_response, order.order_number)

        deliv_response = self.client.post(
            reverse('collector_update_delivery_status', args=[order.id]),
            {'action': 'mark_delivered'},
            follow=True
        )
        self.assertEqual(deliv_response.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.Status.DELIVERED)

    def test_collector_delivery_detail_workflow(self):
        collector_user = User.objects.create_user(
            username="fleet_vikram", password="password123", role=User.Role.COLLECTOR,
            first_name="Vikram", phone="9911223344"
        )
        CollectorProfile.objects.create(
            user=collector_user,
            service_area="Pune City",
            verification_status=CollectorProfile.VerificationStatus.VERIFIED
        )
        other_collector = User.objects.create_user(
            username="fleet_other", password="password123", role=User.Role.COLLECTOR,
            first_name="Other", phone="9900000000"
        )
        CollectorProfile.objects.create(
            user=other_collector,
            service_area="Other City",
            verification_status=CollectorProfile.VerificationStatus.VERIFIED
        )
        order = Order.objects.create(
            company=self.company_user,
            company_name="Green Metal Recyclers",
            contact_person="Rohan",
            contact_phone="9876543210",
            contact_email="rohan@greenmetal.com",
            billing_address="Plot 55, Tech Zone",
            shipping_address="Plot 55, Tech Zone",
            city="Pune",
            state="Maharashtra",
            country="India",
            postal_code="411001",
            subtotal=Decimal("800.00"),
            total_amount=Decimal("944.00"),
            order_status=Order.Status.CONFIRMED,
            assigned_collector=collector_user
        )
        OrderItem.objects.create(
            order=order,
            product=self.product,
            product_name=self.product.product_name,
            sku=self.product.sku,
            unit_price=self.product.price,
            quantity=1,
            total_price=self.product.price
        )

        # Login as assigned collector
        self.client.login(username="fleet_vikram", password="password123")
        detail_res = self.client.get(reverse('collector_delivery_detail', args=[order.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, order.order_number)
        self.assertContains(detail_res, "Green Metal Recyclers")
        self.assertContains(detail_res, "Plot 55, Tech Zone")
        self.assertContains(detail_res, "maps.google.com")

        # Step 1: Start trip (OUT_FOR_DELIVERY)
        out_res = self.client.post(reverse('collector_delivery_detail', args=[order.id]), {
            'action': 'OUT_FOR_DELIVERY',
            'delivery_remarks': 'En route with van.'
        }, follow=True)
        self.assertEqual(out_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.Status.SHIPPED)
        self.assertIn("En route with van.", order.admin_notes)

        # Step 2: Confirm Delivered (MARK_DELIVERED)
        deliv_res = self.client.post(reverse('collector_delivery_detail', args=[order.id]), {
            'action': 'MARK_DELIVERED',
            'delivery_remarks': 'Handed over to warehouse supervisor.'
        }, follow=True)
        self.assertEqual(deliv_res.status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.order_status, Order.Status.DELIVERED)
        self.assertIn("Handed over to warehouse supervisor.", order.admin_notes)

        # Unauthorized collector should receive 404
        self.client.login(username="fleet_other", password="password123")
        unauth_res = self.client.get(reverse('collector_delivery_detail', args=[order.id]))
        self.assertEqual(unauth_res.status_code, 404)

    def test_buy_now_direct_to_checkout(self):
        self.client.login(username="greenmetal", password="password123")
        
        # Click Buy Now on product detail
        response = self.client.post(reverse('add_to_cart', args=[self.product.id]), {
            'quantity': 2,
            'buy_now': '1'
        })
        self.assertRedirects(response, reverse('checkout'))
        
        cart = Cart.objects.get(user=self.company_user)
        self.assertEqual(cart.items.get(product=self.product).quantity, 2)

    def test_payment_gateway_gpay_and_success_flow(self):
        self.client.login(username="greenmetal", password="password123")
        cart = Cart.objects.create(user=self.company_user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=1)

        # 1. Fill checkout
        checkout_res = self.client.post(reverse('checkout'), {
            'company_name': 'Green Metal Recyclers',
            'contact_person': 'Rohan',
            'contact_phone': '9876543210',
            'contact_email': 'rohan@greenmetal.com',
            'gst_tax_id': '27AAACG1234H1Z5',
            'billing_address': 'Industrial Area',
            'shipping_address': 'Industrial Area',
            'city': 'Pune',
            'state': 'Maharashtra',
            'country': 'India',
            'postal_code': '411001',
            'payment_method': Order.PaymentMethod.GPAY_UPI
        })
        order = Order.objects.filter(company=self.company_user).first()
        self.assertIsNotNone(order)
        self.assertRedirects(checkout_res, reverse('payment_gateway', args=[order.id]))

        # 2. View Payment Gateway
        gateway_res = self.client.get(reverse('payment_gateway', args=[order.id]))
        self.assertEqual(gateway_res.status_code, 200)
        self.assertContains(gateway_res, "Google Pay")
        self.assertContains(gateway_res, "Net Banking")
        self.assertContains(gateway_res, "Credit / Debit Cards")

        # 3. Pay via Google Pay UPI
        pay_res = self.client.post(reverse('payment_gateway', args=[order.id]), {
            'payment_method': 'GPAY_UPI'
        })
        self.assertRedirects(pay_res, reverse('order_success', args=[order.id]))
        
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)
        self.assertEqual(order.payment_method, Order.PaymentMethod.GPAY_UPI)
        self.assertTrue(order.payment_transaction_id.startswith('TXN_'))

        # 4. View Success Receipt
        success_res = self.client.get(reverse('order_success', args=[order.id]))
        self.assertEqual(success_res.status_code, 200)
        self.assertContains(success_res, "Payment Received Successfully")
        self.assertContains(success_res, order.payment_transaction_id)

    def test_citizen_user_marketplace_purchase_flow(self):
        # 1. Normal Citizen User
        citizen_user = User.objects.create_user(
            username="citizen_aarav",
            password="password123",
            role=User.Role.USER,
            first_name="Aarav",
            last_name="Sharma",
            phone="9811223344",
            email="aarav@example.com",
            address="Flat 402, Green Heights",
            city="Bangalore",
            state="Karnataka",
            pincode="560001"
        )
        self.client.login(username="citizen_aarav", password="password123")

        # 2. View product detail page as normal citizen
        res = self.client.get(reverse('product_detail', args=[self.product.slug]))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Buy Now")
        self.assertContains(res, "Add to Cart")
        self.assertNotContains(res, "Marketplace procurement is available to Corporate Buyer accounts")

        # 3. Use Buy Now to proceed directly to checkout
        buy_res = self.client.post(reverse('add_to_cart', args=[self.product.id]), {
            'quantity': 1,
            'buy_now': '1'
        })
        self.assertRedirects(buy_res, reverse('checkout'))

        # 4. Complete checkout
        checkout_post = self.client.post(reverse('checkout'), {
            'company_name': 'Aarav Sharma',
            'contact_person': 'Aarav Sharma',
            'contact_phone': '9811223344',
            'contact_email': 'aarav@example.com',
            'gst_tax_id': '',
            'billing_address': 'Flat 402, Green Heights',
            'shipping_address': 'Flat 402, Green Heights',
            'city': 'Bangalore',
            'state': 'Karnataka',
            'country': 'India',
            'postal_code': '560001',
            'payment_method': Order.PaymentMethod.GPAY_UPI
        })
        order = Order.objects.filter(company=citizen_user).first()
        self.assertIsNotNone(order)
        self.assertRedirects(checkout_post, reverse('payment_gateway', args=[order.id]))

        # 5. Process Payment Gateway
        pay_res = self.client.post(reverse('payment_gateway', args=[order.id]), {
            'payment_method': 'GPAY_UPI'
        })
        self.assertRedirects(pay_res, reverse('order_success', args=[order.id]))
        order.refresh_from_db()
        self.assertEqual(order.payment_status, Order.PaymentStatus.PAID)

        # 6. Citizen views their order list and detail
        orders_res = self.client.get(reverse('company_orders'))
        self.assertEqual(orders_res.status_code, 200)
        self.assertContains(orders_res, order.order_number)

        detail_res = self.client.get(reverse('company_order_detail', args=[order.id]))
        self.assertEqual(detail_res.status_code, 200)
        self.assertContains(detail_res, order.order_number)




