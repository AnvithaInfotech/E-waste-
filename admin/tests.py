from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from users.models import User, EWasteCategory, EWasteSubmission, CollectorAssignment, CollectorProfile, CompanyProfile
from admin.models import RecyclingRecord


class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="adminuser", password="password123", role=User.Role.ADMIN)
        self.superadmin = User.objects.create_user(username="superadminuser", password="password123", role=User.Role.SUPER_ADMIN)
        self.collector = User.objects.create_user(username="collector1", password="password123", role=User.Role.COLLECTOR)
        CollectorProfile.objects.create(
            user=self.collector,
            service_area="North Zone",
            verification_status=CollectorProfile.VerificationStatus.VERIFIED
        )
        self.user = User.objects.create_user(username="user1", password="password123", role=User.Role.USER)
        self.category = EWasteCategory.objects.create(name="Cables", icon_class="bi-plug")
        self.submission = EWasteSubmission.objects.create(
            user=self.user,
            waste_name="Copper Cables Lot",
            category=self.category,
            description="50m copper cables",
            quantity=1,
            approximate_weight_kg=Decimal("10.00"),
            pickup_address="123 Street",
            pickup_city="Mumbai",
            contact_phone="9876543210",
            preferred_date=timezone.now().date(),
            preferred_time_slot="MORNING",
            status=EWasteSubmission.Status.SUBMITTED
        )

    def test_admin_verify_and_assign(self):
        self.client.login(username="adminuser", password="password123")
        
        # Approve submission
        response = self.client.post(reverse('admin_ewaste_verify', args=[self.submission.id]), {
            'action': 'APPROVE',
            'reward_points': 50,
            'admin_notes': 'Verified condition.'
        }, follow=True)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, EWasteSubmission.Status.APPROVED)
        self.assertEqual(self.submission.reward_points_awarded, 50)

        # Assign collector
        response = self.client.post(reverse('admin_assign_collector', args=[self.submission.id]), {
            'collector': self.collector.id,
            'scheduled_date': timezone.now().date(),
            'scheduled_slot': 'Morning',
            'collector_notes': 'Please collect promptly.'
        }, follow=True)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, EWasteSubmission.Status.COLLECTOR_ASSIGNED)
        self.assertEqual(self.submission.collector_assignment.collector, self.collector)

    def test_admin_create_order_for_company(self):
        company_user = User.objects.create_user(
            username="targetcorp", password="password123", role=User.Role.COMPANY,
            first_name="Target Tech Corp", phone="9112233445"
        )
        from users.models import CompanyProfile
        from company.models import RecycledProduct, Order
        CompanyProfile.objects.create(
            user=company_user,
            company_name="Target Tech Corp",
            corporate_address="Tech Park Phase 1",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            verification_status=CompanyProfile.VerificationStatus.VERIFIED
        )
        product = RecycledProduct.objects.create(
            product_name="Refined Silver Granules",
            category=self.category,
            material_type="Precious Metal",
            quantity_available=Decimal("20.00"),
            unit="kg",
            price=Decimal("5000.00"),
            status=RecycledProduct.Status.PUBLISHED
        )

        self.client.login(username="adminuser", password="password123")
        
        # Test GET
        get_res = self.client.get(reverse('admin_create_order'))
        self.assertEqual(get_res.status_code, 200)
        self.assertContains(get_res, "Place Order for Company")

        # Test POST
        post_res = self.client.post(reverse('admin_create_order'), {
            'company': company_user.id,
            'product': product.id,
            'quantity': 3,
            'assigned_collector': self.collector.id,
            'company_name': 'Target Tech Corp',
            'contact_person': 'Target Officer',
            'contact_phone': '9112233445',
            'contact_email': 'procure@targetcorp.com',
            'gst_tax_id': '29ABCDE1234F1Z5',
            'billing_address': 'Tech Park Phase 1',
            'shipping_address': 'Tech Park Phase 1',
            'city': 'Bengaluru',
            'state': 'Karnataka',
            'country': 'India',
            'postal_code': '560001',
            'payment_method': Order.PaymentMethod.BANK_TRANSFER,
            'payment_status': Order.PaymentStatus.PAID,
            'order_status': Order.Status.CONFIRMED,
            'admin_notes': 'Corporate bulk order placed by operational admin.'
        }, follow=True)

        self.assertEqual(post_res.status_code, 200)
        order = Order.objects.filter(company=company_user).first()
        self.assertIsNotNone(order)
        self.assertEqual(order.company_name, 'Target Tech Corp')
        self.assertEqual(order.assigned_collector, self.collector)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.items.first().quantity, 3)

        # Verify stock deducted
        product.refresh_from_db()
        self.assertEqual(product.quantity_available, Decimal("17.00"))

    def test_admin_recycled_product_detail_and_buyers_view(self):
        from company.models import RecycledProduct, Order, OrderItem
        # Create product
        product = RecycledProduct.objects.create(
            product_name="Recycled Copper Wire 99.9%",
            category=self.category,
            material_type="Pure Copper",
            quantity_available=Decimal("50.00"),
            unit="kg",
            price=Decimal("750.00"),
            status=RecycledProduct.Status.PUBLISHED,
            description="High quality recycled copper wire",
            specifications="Assay: 99.9% Cu"
        )

        # Create 2 orders purchasing this product
        buyer1 = User.objects.create_user(
            username="acme_corp", password="password123", role=User.Role.COMPANY,
            first_name="Acme Corp"
        )
        CompanyProfile.objects.create(
            user=buyer1,
            company_name="Acme Industries Ltd",
            corporate_address="Plot 10, Industrial Area",
            city="Pune",
            state="Maharashtra",
            postal_code="411001",
            verification_status=CompanyProfile.VerificationStatus.VERIFIED
        )
        order1 = Order.objects.create(
            company=buyer1,
            company_name="Acme Industries Ltd",
            contact_person="John Doe",
            contact_phone="9800112233",
            contact_email="john@acme.com",
            billing_address="Plot 10, Industrial Area",
            shipping_address="Plot 10, Industrial Area",
            city="Pune",
            state="Maharashtra",
            country="India",
            postal_code="411001",
            subtotal=Decimal("7500.00"),
            total_amount=Decimal("8850.00"),
            order_status=Order.Status.CONFIRMED,
            payment_status=Order.PaymentStatus.PAID,
            assigned_collector=self.collector
        )
        OrderItem.objects.create(
            order=order1,
            product=product,
            product_name=product.product_name,
            sku=product.sku,
            unit_price=product.price,
            quantity=10,
            total_price=Decimal("7500.00")
        )

        buyer2 = User.objects.create_user(
            username="citizen_rohit", password="password123", role=User.Role.USER,
            first_name="Rohit", last_name="Verma"
        )
        order2 = Order.objects.create(
            company=buyer2,
            company_name="Rohit Verma",
            contact_person="Rohit Verma",
            contact_phone="9877665544",
            contact_email="rohit@example.com",
            billing_address="Apt 201, Green Valley",
            shipping_address="Apt 201, Green Valley",
            city="Mumbai",
            state="Maharashtra",
            country="India",
            postal_code="400001",
            subtotal=Decimal("1500.00"),
            total_amount=Decimal("1770.00"),
            order_status=Order.Status.SHIPPED,
            payment_status=Order.PaymentStatus.PAID
        )
        OrderItem.objects.create(
            order=order2,
            product=product,
            product_name=product.product_name,
            sku=product.sku,
            unit_price=product.price,
            quantity=2,
            total_price=Decimal("1500.00")
        )

        # Login as Admin
        self.client.login(username="adminuser", password="password123")

        # 1. View Product Detail Page in Admin Panel
        response = self.client.get(reverse('admin_recycled_product_detail', args=[product.id]))
        self.assertEqual(response.status_code, 200)

        # Verify Core details & metrics
        self.assertContains(response, "Recycled Copper Wire 99.9%")
        self.assertContains(response, product.sku)
        self.assertContains(response, "50") # Quantity left
        self.assertContains(response, "12") # Total sold (10 + 2)
        self.assertContains(response, "9000.00") # Total revenue (7500 + 1500)
        self.assertContains(response, "Acme Industries Ltd")
        self.assertContains(response, "Rohit Verma")
        self.assertContains(response, order1.order_number)
        self.assertContains(response, order2.order_number)

        # 2. Test In-Page Quick Update of Stock and Price
        update_res = self.client.post(reverse('admin_recycled_product_detail', args=[product.id]), {
            'product_name': 'Recycled Copper Wire 99.9% (Premium Grade)',
            'category': self.category.id,
            'material_type': 'Pure Copper',
            'product_condition': RecycledProduct.Condition.INGOT_PELLET,
            'quantity_available': '45.00',
            'unit': 'kg',
            'price': '820.00',
            'discount_price': '800.00',
            'origin_recycling_center': 'Central Eco-Recovery Facility #1',
            'status': RecycledProduct.Status.PUBLISHED,
            'description': 'Updated premium copper description',
            'specifications': 'Purity 99.9% tested',
            'is_featured': True
        }, follow=True)

        self.assertEqual(update_res.status_code, 200)
        product.refresh_from_db()
        self.assertEqual(product.product_name, 'Recycled Copper Wire 99.9% (Premium Grade)')
        self.assertEqual(product.quantity_available, Decimal("45.00"))
        self.assertEqual(product.price, Decimal("820.00"))
        self.assertTrue(product.is_featured)

    def test_admin_delete_ewaste_submission(self):
        self.client.login(username="adminuser", password="password123")
        
        # Verify list page renders with delete button
        list_res = self.client.get(reverse('admin_ewaste_list'))
        self.assertEqual(list_res.status_code, 200)
        self.assertContains(list_res, f"/admin-panel/ewaste/{self.submission.id}/delete/")
        self.assertContains(list_res, self.submission.tracking_id)

        # Post delete request
        del_res = self.client.post(reverse('admin_delete_ewaste_submission', args=[self.submission.id]), follow=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertFalse(EWasteSubmission.objects.filter(id=self.submission.id).exists())

    def test_operational_admin_collector_list_view_and_no_post_creation(self):
        self.client.login(username="adminuser", password="password123")

        # GET operational admin collector list
        res = self.client.get(reverse('admin_collectors_list'))
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "collector1")
        self.assertNotContains(res, "Register Field Collector")

        # POST attempt to add collector by operational admin should be rejected
        post_res = self.client.post(reverse('admin_collectors_list'), {
            'username': 'fake_collector',
            'password': 'password123'
        }, follow=True)
        self.assertEqual(post_res.status_code, 200)
        self.assertContains(post_res, "Operational Admins are not permitted to add local collectors")
        self.assertFalse(User.objects.filter(username='fake_collector').exists())

    def test_super_admin_collector_creation_and_status_update(self):
        self.client.login(username="superadminuser", password="password123")

        # 1. Super Admin creates new collector directly (auto-verified)
        create_res = self.client.post(reverse('super_admin_collectors'), {
            'first_name': 'Karan',
            'last_name': 'Mehta',
            'username': 'karan_col',
            'email': 'karan@ecocycle.green',
            'phone': '9876599999',
            'password': 'collectorpassword123',
            'service_area': 'West Coast Zone',
            'vehicle_type': 'Electric Cargo Van',
            'vehicle_number': 'MH-01-EV-7788'
        }, follow=True)
        self.assertEqual(create_res.status_code, 200)
        self.assertTrue(User.objects.filter(username='karan_col').exists())
        karan = User.objects.get(username='karan_col')
        self.assertEqual(karan.collector_profile.verification_status, CollectorProfile.VerificationStatus.VERIFIED)

        # 2. Super Admin updates status of collector
        update_res = self.client.post(reverse('super_admin_collectors'), {
            'action': 'UPDATE_STATUS',
            'collector_profile_id': karan.collector_profile.id,
            'status': CollectorProfile.VerificationStatus.SUSPENDED,
            'rejection_reason': 'Temporary vehicle maintenance audit'
        }, follow=True)
        self.assertEqual(update_res.status_code, 200)
        karan.collector_profile.refresh_from_db()
        self.assertEqual(karan.collector_profile.verification_status, CollectorProfile.VerificationStatus.SUSPENDED)



