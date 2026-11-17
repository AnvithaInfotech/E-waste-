from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from users.models import (
    User, UserProfile, CollectorProfile, CompanyProfile,
    EWasteCategory, EWasteSubmission, CollectorAssignment, PickupRecord
)


class UserModelAndRoleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.category = EWasteCategory.objects.create(name="Laptops", icon_class="bi-laptop")

    def test_user_creation_and_roles(self):
        user = User.objects.create_user(username="testuser", password="password123", role=User.Role.USER)
        self.assertTrue(user.is_normal_user)
        self.assertFalse(user.is_collector)
        self.assertFalse(user.is_admin_user)
        self.assertFalse(user.is_company)

        collector = User.objects.create_user(username="testcol", password="password123", role=User.Role.COLLECTOR)
        self.assertTrue(collector.is_collector)

        admin = User.objects.create_user(username="testadm", password="password123", role=User.Role.ADMIN)
        self.assertTrue(admin.is_admin_user)

    def test_ewaste_submission_lifecycle(self):
        user = User.objects.create_user(username="citizen", password="password123", role=User.Role.USER)
        submission = EWasteSubmission.objects.create(
            user=user,
            waste_name="Old Dell Latitude",
            category=self.category,
            description="Working but slow laptop",
            quantity=1,
            approximate_weight_kg=Decimal("2.50"),
            pickup_address="123 Green St",
            pickup_city="Mumbai",
            contact_phone="9876543210",
            preferred_date=timezone.now().date(),
            preferred_time_slot="MORNING"
        )
        self.assertTrue(submission.tracking_id.startswith("EW-"))
        self.assertEqual(submission.status, EWasteSubmission.Status.SUBMITTED)

    def test_company_registration_success(self):
        response = self.client.post(reverse('register_company'), {
            'company_name': 'New Tech Recyclers Ltd',
            'registration_number': 'CIN-U12345MH2022PTC999999',
            'business_type': CompanyProfile.BusinessType.MANUFACTURER,
            'gst_tax_id': '27AAACL9999P1Z1',
            'corporate_address': 'Plot 99, Tech Valley',
            'city': 'Pune',
            'state': 'Maharashtra',
            'country': 'India',
            'postal_code': '411057',
            'contact_person': 'Alok Gupta',
            'phone': '9876543210',
            'email': 'alok@newtech.com',
            'username': 'newtech_buyer',
            'password': 'companypassword123',
            'confirm_password': 'companypassword123',
            'business_description': 'Electronics assembly and recovery'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='newtech_buyer').exists())
        user = User.objects.get(username='newtech_buyer')
        self.assertEqual(user.role, User.Role.COMPANY)
        self.assertEqual(user.company_profile.company_name, 'New Tech Recyclers Ltd')
        self.assertEqual(user.company_profile.verification_status, CompanyProfile.VerificationStatus.PENDING)

        # Ensure login is blocked while pending
        login_res = self.client.post(reverse('login'), {'username': 'newtech_buyer', 'password': 'companypassword123'}, follow=True)
        self.assertContains(login_res, "pending Super Admin approval")

        # Once approved by Super Admin, login succeeds
        user.company_profile.verification_status = CompanyProfile.VerificationStatus.VERIFIED
        user.company_profile.save()
        login_success_res = self.client.post(reverse('login'), {'username': 'newtech_buyer', 'password': 'companypassword123'}, follow=True)
        self.assertEqual(login_success_res.status_code, 200)
        self.assertContains(login_success_res, "Welcome back")

    def test_collector_registration_pending_and_approval_flow(self):
        # 1. Self-register as local collector
        response = self.client.post(reverse('register_collector'), {
            'first_name': 'Suresh',
            'last_name': 'Patel',
            'username': 'suresh_collector',
            'email': 'suresh@collector.com',
            'phone': '9876500000',
            'password': 'collectorpassword123',
            'confirm_password': 'collectorpassword123',
            'service_area': 'East Zone & Tech Corridor',
            'vehicle_type': 'Electric Cargo Van',
            'vehicle_number': 'MH-03-EC-9900',
            'address': 'Depot 12, East Ring',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='suresh_collector').exists())
        collector_user = User.objects.get(username='suresh_collector')
        self.assertEqual(collector_user.role, User.Role.COLLECTOR)
        self.assertEqual(collector_user.collector_profile.verification_status, CollectorProfile.VerificationStatus.PENDING)

        # 2. Attempt login while pending -> blocked
        login_res = self.client.post(reverse('login'), {'username': 'suresh_collector', 'password': 'collectorpassword123'}, follow=True)
        self.assertContains(login_res, "pending Super Admin approval")

        # 3. Super Admin approves -> login succeeds
        collector_user.collector_profile.verification_status = CollectorProfile.VerificationStatus.VERIFIED
        collector_user.collector_profile.save()
        login_success_res = self.client.post(reverse('login'), {'username': 'suresh_collector', 'password': 'collectorpassword123'}, follow=True)
        self.assertEqual(login_success_res.status_code, 200)
        self.assertContains(login_success_res, "Welcome back")

    def test_company_registration_password_mismatch(self):
        response = self.client.post(reverse('register_company'), {
            'company_name': 'Bad Pass Corp',
            'registration_number': 'CIN-U99999',
            'business_type': CompanyProfile.BusinessType.MANUFACTURER,
            'corporate_address': 'Address',
            'city': 'City',
            'state': 'State',
            'country': 'India',
            'postal_code': '123456',
            'contact_person': 'Contact',
            'phone': '1234567890',
            'email': 'bad@pass.com',
            'username': 'bad_pass_user',
            'password': 'password1',
            'confirm_password': 'password2',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'confirm_password', 'Passwords do not match.')

    def test_user_registration_minimal_fields(self):
        response = self.client.post(reverse('register_user'), {
            'username': 'rahul_eco',
            'email': 'rahul@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(User.objects.filter(username='rahul_eco').exists())
        user = User.objects.get(username='rahul_eco')
        self.assertEqual(user.role, User.Role.USER)
        self.assertEqual(user.email, 'rahul@example.com')
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.address, None)

    def test_submit_ewaste_captures_and_updates_user_details(self):
        user = User.objects.create_user(
            username='anita_disposer',
            email='anita@example.com',
            password='password123',
            role=User.Role.USER
        )
        self.client.login(username='anita_disposer', password='password123')

        # Test GET loads initial form
        get_res = self.client.get(reverse('submit_ewaste'))
        self.assertEqual(get_res.status_code, 200)

        # Test POST with full contact and location info
        post_res = self.client.post(reverse('submit_ewaste'), {
            'first_name': 'Anita',
            'last_name': 'Menon',
            'contact_phone': '9847123456',
            'pickup_address': 'Flat 4B, Palm Grove Apts, Marine Drive',
            'pickup_city': 'Kochi',
            'pickup_state': 'Kerala',
            'pickup_pincode': '682011',
            'waste_name': 'Broken Lenovo ThinkPad & Printer',
            'category': self.category.id,
            'description': 'Laptop with broken screen, printer with faulty cartridge',
            'quantity': 2,
            'approximate_weight_kg': '4.5',
            'condition': EWasteSubmission.Condition.NON_FUNCTIONAL,
            'preferred_date': timezone.now().date(),
            'preferred_time_slot': 'MORNING',
            'additional_notes': 'Ring the bell at gate 2',
        }, follow=True)
        self.assertEqual(post_res.status_code, 200)

        # Check submission was created
        submission = EWasteSubmission.objects.filter(user=user).first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.waste_name, 'Broken Lenovo ThinkPad & Printer')
        self.assertEqual(submission.pickup_city, 'Kochi')
        self.assertEqual(submission.contact_phone, '9847123456')

        # Check user profile was updated with the details provided during pickup request
        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Anita')
        self.assertEqual(user.last_name, 'Menon')
        self.assertEqual(user.phone, '9847123456')
        self.assertEqual(user.city, 'Kochi')
        self.assertEqual(user.state, 'Kerala')
        self.assertEqual(user.pincode, '682011')
        self.assertEqual(user.address, 'Flat 4B, Palm Grove Apts, Marine Drive')

    def test_multi_portal_independent_sessions_and_isolated_logout(self):
        citizen = User.objects.create_user(username='citizen_tab', password='password123', role=User.Role.USER)
        admin = User.objects.create_user(username='admin_tab', password='password123', role=User.Role.ADMIN)
        collector = User.objects.create_user(username='collector_tab', password='password123', role=User.Role.COLLECTOR)
        CollectorProfile.objects.create(
            user=collector,
            service_area="Mumbai",
            verification_status=CollectorProfile.VerificationStatus.VERIFIED
        )

        client = Client()

        # Step 1: Citizen logs in (Tab 1)
        res1 = client.post(reverse('login'), {'username': 'citizen_tab', 'password': 'password123'}, follow=True)
        self.assertEqual(res1.status_code, 200)

        # Tab 1 accesses user dashboard
        res_user = client.get(reverse('user_dashboard'))
        self.assertEqual(res_user.status_code, 200)
        self.assertEqual(res_user.context['user'].username, 'citizen_tab')

        # Step 2: In Tab 2, Admin logs in without closing Tab 1
        res2 = client.post(reverse('login'), {'username': 'admin_tab', 'password': 'password123'}, follow=True)
        self.assertEqual(res2.status_code, 200)

        # Tab 2 accesses admin dashboard
        res_admin = client.get(reverse('admin_dashboard'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertEqual(res_admin.context['user'].username, 'admin_tab')

        # Tab 1 still has access to citizen dashboard without re-authenticating!
        res_user_again = client.get(reverse('user_dashboard'))
        self.assertEqual(res_user_again.status_code, 200)
        self.assertEqual(res_user_again.context['user'].username, 'citizen_tab')

        # Step 3: In Tab 3, Collector logs in
        res3 = client.post(reverse('login'), {'username': 'collector_tab', 'password': 'password123'}, follow=True)
        self.assertEqual(res3.status_code, 200)

        res_col = client.get(reverse('collector_dashboard'))
        self.assertEqual(res_col.status_code, 200)
        self.assertEqual(res_col.context['user'].username, 'collector_tab')

        # Step 4: Logout from Admin Portal ONLY (Tab 2 clicks logout)
        res_logout_admin = client.get(f"{reverse('logout')}?role=ADMIN", follow=True)
        self.assertEqual(res_logout_admin.status_code, 200)

        # Tab 1 (Citizen) and Tab 3 (Collector) remain fully authenticated
        res_user_after_logout = client.get(reverse('user_dashboard'))
        self.assertEqual(res_user_after_logout.status_code, 200, msg=f"Redirected to {getattr(res_user_after_logout, 'url', None)}")
        self.assertEqual(res_user_after_logout.context['user'].username, 'citizen_tab')

        res_col_after_logout = client.get(reverse('collector_dashboard'))
        self.assertEqual(res_col_after_logout.status_code, 200)
        self.assertEqual(res_col_after_logout.context['user'].username, 'collector_tab')

        # Tab 2 (Admin) cannot access admin dashboard without logging back in
        res_admin_after_logout = client.get(reverse('admin_dashboard'), follow=False)
        self.assertIn(res_admin_after_logout.status_code, [302, 403])


