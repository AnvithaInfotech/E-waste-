from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from users.models import (
    User, UserProfile, CollectorProfile, CompanyProfile,
    EWasteCategory, EWasteSubmission, CollectorAssignment,
    PickupRecord, Notification
)
from admin.models import RecyclingRecord, SystemAuditLog
from company.models import RecycledProduct, Cart, CartItem, Order, OrderItem


class Command(BaseCommand):
    help = "Seeds comprehensive demo data for all 5 roles, workflows, categories, products, and orders."

    def handle(self, *args, **options):
        self.stdout.write("Starting EcoCycle database seeder...")

        # -------------------------------------------------------------
        # 1. CREATE USER ACCOUNTS FOR ALL 5 ROLES
        # -------------------------------------------------------------
        
        # Super Admin
        super_admin, _ = User.objects.get_or_create(
            username="superadmin",
            defaults={
                "email": "superadmin@ecocycle.green",
                "first_name": "Alexander",
                "last_name": "Vance",
                "role": User.Role.SUPER_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "phone": "+91 99000 11111",
                "city": "Metro Central"
            }
        )
        super_admin.set_password("admin123")
        super_admin.role = User.Role.SUPER_ADMIN
        super_admin.is_superuser = True
        super_admin.is_staff = True
        super_admin.save()

        # Operational Admin
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@ecocycle.green",
                "first_name": "Sarah",
                "last_name": "Jenkins",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "phone": "+91 99000 22222",
                "city": "Eco Logistics Hub #1"
            }
        )
        admin_user.set_password("admin123")
        admin_user.role = User.Role.ADMIN
        admin_user.is_staff = True
        admin_user.save()

        # Collector 1
        collector1, _ = User.objects.get_or_create(
            username="collector",
            defaults={
                "email": "rajesh.collector@ecocycle.green",
                "first_name": "Rajesh",
                "last_name": "Kumar",
                "role": User.Role.COLLECTOR,
                "phone": "+91 98111 33333",
                "city": "Metro North"
            }
        )
        collector1.set_password("collector123")
        collector1.role = User.Role.COLLECTOR
        collector1.save()
        CollectorProfile.objects.update_or_create(
            user=collector1,
            defaults={
                "service_area": "Metro North & Downtown Tech Park",
                "vehicle_type": "Electric Cargo Van (Zero Emission)",
                "vehicle_number": "MH-02-EV-8821",
                "is_available": True,
                "rating": Decimal("4.95"),
                "completed_pickups_count": 42
            }
        )

        # Collector 2
        collector2, _ = User.objects.get_or_create(
            username="collector2",
            defaults={
                "email": "vikram.collector@ecocycle.green",
                "first_name": "Vikram",
                "last_name": "Singh",
                "role": User.Role.COLLECTOR,
                "phone": "+91 98222 44444",
                "city": "South Cyber Zone"
            }
        )
        collector2.set_password("collector123")
        collector2.role = User.Role.COLLECTOR
        collector2.save()
        CollectorProfile.objects.update_or_create(
            user=collector2,
            defaults={
                "service_area": "South Cyber Zone & Industrial Estate",
                "vehicle_type": "Eco Light Freight Truck",
                "vehicle_number": "MH-04-EC-5510",
                "is_available": True,
                "rating": Decimal("4.85"),
                "completed_pickups_count": 29
            }
        )

        # Normal User 1
        user1, _ = User.objects.get_or_create(
            username="user",
            defaults={
                "email": "priya.sharma@example.com",
                "first_name": "Priya",
                "last_name": "Sharma",
                "role": User.Role.USER,
                "phone": "+91 98765 12345",
                "address": "Flat 402, Green Meadows, 5th Avenue",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400050"
            }
        )
        user1.set_password("user123")
        user1.role = User.Role.USER
        user1.save()
        UserProfile.objects.update_or_create(
            user=user1,
            defaults={"eco_points": 180, "total_recycled_items": 4}
        )

        # Normal User 2
        user2, _ = User.objects.get_or_create(
            username="user2",
            defaults={
                "email": "aravind.nair@example.com",
                "first_name": "Aravind",
                "last_name": "Nair",
                "role": User.Role.USER,
                "phone": "+91 98765 67890",
                "address": "Villa 12, Palm Residency",
                "city": "Bengaluru",
                "state": "Karnataka",
                "pincode": "560001"
            }
        )
        user2.set_password("user123")
        user2.role = User.Role.USER
        user2.save()
        UserProfile.objects.update_or_create(
            user=user2,
            defaults={"eco_points": 95, "total_recycled_items": 2}
        )

        # Company Buyer 1
        comp_user1, _ = User.objects.get_or_create(
            username="company",
            defaults={
                "email": "procurement@ecometal.com",
                "first_name": "Rohan (Procurement Head)",
                "last_name": "Mehta",
                "role": User.Role.COMPANY,
                "phone": "+91 22 2847 9000",
                "city": "Pune"
            }
        )
        comp_user1.set_password("company123")
        comp_user1.role = User.Role.COMPANY
        comp_user1.save()
        CompanyProfile.objects.update_or_create(
            user=comp_user1,
            defaults={
                "company_name": "EcoMetal Refining & Smelting Corp",
                "registration_number": "CIN-U27100PN2019PTC182736",
                "business_type": CompanyProfile.BusinessType.RECYCLER,
                "gst_tax_id": "27AAACE1234F1Z8",
                "corporate_address": "Plot 45-B, Hinjewadi Industrial Phase II",
                "city": "Pune",
                "state": "Maharashtra",
                "country": "India",
                "postal_code": "411057",
                "business_description": "Large-scale industrial smelting and recovery facility specializing in 99.8% copper wire drawing and high-grade precious metal extraction.",
                "verification_status": CompanyProfile.VerificationStatus.VERIFIED,
                "verified_at": timezone.now()
            }
        )

        # Company Buyer 2
        comp_user2, _ = User.objects.get_or_create(
            username="green_tech_corp",
            defaults={
                "email": "orders@apextech.com",
                "first_name": "Ananya (Sourcing Lead)",
                "last_name": "Deshmukh",
                "role": User.Role.COMPANY,
                "phone": "+91 80 4123 7890",
                "city": "Bengaluru"
            }
        )
        comp_user2.set_password("company123")
        comp_user2.role = User.Role.COMPANY
        comp_user2.save()
        CompanyProfile.objects.update_or_create(
            user=comp_user2,
            defaults={
                "company_name": "Apex Clean Electronics Manufacturing Ltd",
                "registration_number": "CIN-U32100KA2021PLC098234",
                "business_type": CompanyProfile.BusinessType.MANUFACTURER,
                "gst_tax_id": "29AABCA9876E1ZQ",
                "corporate_address": "Electronics City Phase 1, Hosur Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "country": "India",
                "postal_code": "560100",
                "business_description": "Green OEM electronics manufacturer integrating recovered secondary polymers and refurbished microchips into sustainable smart devices.",
                "verification_status": CompanyProfile.VerificationStatus.VERIFIED,
                "verified_at": timezone.now()
            }
        )

        self.stdout.write("Created all 5 role accounts successfully.")

        # -------------------------------------------------------------
        # 2. CREATE E-WASTE CATEGORIES
        # -------------------------------------------------------------
        categories_data = [
            ("Mobile Phones & Tablets", "bi-phone", "Smartphones, tablets, feature phones, touchscreens, and lithium battery modules.", "MEDIUM", 1),
            ("Laptops & Notebooks", "bi-laptop", "Ultrabooks, business laptops, gaming laptops, and notebook motherboards.", "MEDIUM", 2),
            ("Computers & Servers", "bi-pc-display-horizontal", "Desktop CPUs, enterprise blade servers, workstations, and high-density boards.", "HIGH", 3),
            ("Monitors & Displays", "bi-display", "IPS monitors, LCD/LED panels, touch displays, and power inverter boards.", "LOW", 4),
            ("Televisions & Home Audio", "bi-tv", "Smart TVs, amplifiers, subwoofers, soundbars, and consumer audio hardware.", "LOW", 5),
            ("Printers & Scanners", "bi-printer", "LaserJet printers, multi-function copiers, scanners, and toner cartridge assemblies.", "LOW", 6),
            ("Batteries & Power Banks", "bi-battery-charging", "Lithium-ion batteries, UPS lead-acid battery packs, and EV module cells.", "HIGH", 7),
            ("Circuit Boards & PCBs", "bi-motherboard", "Motherboards, RAM modules, graphics cards, IC chips, and gold-plated connectors.", "HIGH", 8),
            ("Cables, Adapters & Parts", "bi-plug", "High-purity copper cabling, LAN cables, power bricks, and adapters.", "LOW", 9),
            ("Hard Disks & Storage", "bi-device-hdd", "Enterprise SAS/SATA drives, SSDs, magnetic platters, and neodymium magnets.", "LOW", 10),
        ]

        cat_objects = {}
        for name, icon, desc, hazard, order in categories_data:
            cat, _ = EWasteCategory.objects.update_or_create(
                name=name,
                defaults={
                    "icon_class": icon,
                    "description": desc,
                    "hazard_level": hazard,
                    "display_order": order,
                    "is_active": True
                }
            )
            cat_objects[name] = cat

        self.stdout.write(f"Created {len(cat_objects)} E-Waste categories.")

        # -------------------------------------------------------------
        # 3. CREATE SAMPLE E-WASTE SUBMISSIONS IN VARIOUS WORKFLOW STAGES
        # -------------------------------------------------------------
        
        # 1. Submitted (Pending Review)
        sub1, _ = EWasteSubmission.objects.get_or_create(
            waste_name="Apple MacBook Pro 2017 & Charger (Damaged Screen)",
            user=user1,
            defaults={
                "category": cat_objects["Laptops & Notebooks"],
                "description": "Screen cracked, logic board still powers on. Includes original 87W USB-C power brick and charging cable.",
                "quantity": 1,
                "approximate_weight_kg": Decimal("2.10"),
                "condition": EWasteSubmission.Condition.PARTIALLY_WORKING,
                "pickup_address": "Flat 402, Green Meadows, 5th Avenue",
                "pickup_city": "Mumbai",
                "pickup_state": "Maharashtra",
                "pickup_pincode": "400050",
                "contact_phone": "+91 98765 12345",
                "preferred_date": timezone.now().date(),
                "preferred_time_slot": "MORNING",
                "status": EWasteSubmission.Status.SUBMITTED,
            }
        )

        # 2. Under Verification
        sub2, _ = EWasteSubmission.objects.get_or_create(
            waste_name="Lot of 12 Damaged Smartphone Motherboards & Cameras",
            user=user2,
            defaults={
                "category": cat_objects["Mobile Phones & Tablets"],
                "description": "Old repair shop discarded smartphone motherboards with gold pins and rear camera sensor assemblies.",
                "quantity": 12,
                "approximate_weight_kg": Decimal("1.45"),
                "condition": EWasteSubmission.Condition.SCRAP,
                "pickup_address": "Villa 12, Palm Residency",
                "pickup_city": "Bengaluru",
                "pickup_state": "Karnataka",
                "pickup_pincode": "560001",
                "contact_phone": "+91 98765 67890",
                "preferred_date": timezone.now().date(),
                "preferred_time_slot": "AFTERNOON",
                "status": EWasteSubmission.Status.UNDER_VERIFICATION,
                "admin_notes": "Awaiting photos of gold contacts."
            }
        )

        # 3. Approved & Collector Assigned
        sub3, _ = EWasteSubmission.objects.get_or_create(
            waste_name="2x Dell UltraSharp 24-inch Monitors & Power Inverters",
            user=user1,
            defaults={
                "category": cat_objects["Monitors & Displays"],
                "description": "Functional IPS panels from office upgrade. Fully working with minor stand scratches.",
                "quantity": 2,
                "approximate_weight_kg": Decimal("8.50"),
                "condition": EWasteSubmission.Condition.WORKING,
                "pickup_address": "Flat 402, Green Meadows, 5th Avenue",
                "pickup_city": "Mumbai",
                "pickup_state": "Maharashtra",
                "pickup_pincode": "400050",
                "contact_phone": "+91 98765 12345",
                "preferred_date": timezone.now().date(),
                "preferred_time_slot": "MORNING",
                "status": EWasteSubmission.Status.COLLECTOR_ASSIGNED,
                "reward_points_awarded": 75
            }
        )
        asgn3, _ = CollectorAssignment.objects.get_or_create(
            submission=sub3,
            defaults={
                "collector": collector1,
                "assigned_by": admin_user,
                "scheduled_date": timezone.now().date(),
                "scheduled_slot": "Morning (09:00 AM - 12:00 PM)",
                "status": CollectorAssignment.AssignmentStatus.ASSIGNED,
                "collector_notes": "Handle with care, panels are functional and reusable."
            }
        )

        # 4. Collected & Delivered to Facility
        sub4, _ = EWasteSubmission.objects.get_or_create(
            waste_name="Rack Server Power Supplies & Cat6 Heavy Copper Cabling (Lot)",
            user=user2,
            defaults={
                "category": cat_objects["Cables, Adapters & Parts"],
                "description": "50 meters high-density shielded copper ethernet cabling and 4x Titanium server power supplies.",
                "quantity": 5,
                "approximate_weight_kg": Decimal("18.60"),
                "condition": EWasteSubmission.Condition.NON_FUNCTIONAL,
                "pickup_address": "Villa 12, Palm Residency",
                "pickup_city": "Bengaluru",
                "pickup_state": "Karnataka",
                "pickup_pincode": "560001",
                "contact_phone": "+91 98765 67890",
                "preferred_date": timezone.now().date(),
                "preferred_time_slot": "AFTERNOON",
                "status": EWasteSubmission.Status.AT_RECYCLING_CENTER,
                "reward_points_awarded": 100
            }
        )
        asgn4, _ = CollectorAssignment.objects.get_or_create(
            submission=sub4,
            defaults={
                "collector": collector2,
                "assigned_by": admin_user,
                "scheduled_date": timezone.now().date(),
                "scheduled_slot": "Afternoon",
                "status": CollectorAssignment.AssignmentStatus.DELIVERED,
            }
        )
        PickupRecord.objects.get_or_create(
            assignment=asgn4,
            defaults={
                "submission": sub4,
                "collector": collector2,
                "collected_at": timezone.now(),
                "delivered_at": timezone.now(),
                "verified_weight_kg": Decimal("18.80"),
                "collector_remarks": "Loaded securely into eco transport van. Verified weight on scale."
            }
        )

        self.stdout.write("Created E-Waste submissions & pickup lifecycles.")

        # -------------------------------------------------------------
        # 4. CREATE RECYCLING PROCESSING RUNS
        # -------------------------------------------------------------
        rec1, _ = RecyclingRecord.objects.get_or_create(
            waste_type="High-Density Copper Cabling & Power Transformers",
            defaults={
                "submission": sub4,
                "facility_name": "Central Eco-Recovery Facility #1",
                "received_date": timezone.now().date(),
                "original_weight_kg": Decimal("18.80"),
                "recovered_material": "Electrolytic Pure Copper (99.8% Grade)",
                "material_category": cat_objects["Cables, Adapters & Parts"],
                "processing_method": RecyclingRecord.ProcessingMethod.DISMANTLING,
                "processing_description": "Mechanical stripping of PVC polymer sheath followed by magnetic separation and copper granule compaction.",
                "recovered_quantity": Decimal("14.50"),
                "recovered_unit": "kg",
                "status": RecyclingRecord.Status.PRODUCT_READY,
                "recycling_date": timezone.now().date(),
                "processed_by": admin_user,
                "notes": "High yield recovery run. Purity tested and certified for industrial wire drawing."
            }
        )

        rec2, _ = RecyclingRecord.objects.get_or_create(
            waste_type="Enterprise PCB Motherboards & Server Backplanes",
            defaults={
                "facility_name": "Central Eco-Recovery Facility #1",
                "received_date": timezone.now().date(),
                "original_weight_kg": Decimal("45.00"),
                "recovered_material": "Gold & Silver Contact Pins (Fine Concentrate)",
                "material_category": cat_objects["Circuit Boards & PCBs"],
                "processing_method": RecyclingRecord.ProcessingMethod.HYDROMETALLURGICAL,
                "processing_description": "Eco-friendly zero-emission hydrometallurgical leaching of gold plating from CPU sockets and RAM edge connectors.",
                "recovered_quantity": Decimal("240.00"),
                "recovered_unit": "grams",
                "status": RecyclingRecord.Status.PRODUCT_READY,
                "recycling_date": timezone.now().date(),
                "processed_by": admin_user,
            }
        )

        self.stdout.write("Created Recycling records.")

        # -------------------------------------------------------------
        # 5. CREATE MARKETPLACE RECYCLED PRODUCTS
        # -------------------------------------------------------------
        products_data = [
            (
                "Industrial High-Purity Copper Wire (99.8% Electrolytic Grade)",
                cat_objects["Cables, Adapters & Parts"],
                rec1,
                "Electrolytic Pure Copper",
                Decimal("150.00"),
                "kg",
                Decimal("820.00"),
                Decimal("780.00"),
                RecycledProduct.Condition.RAW_MATERIAL,
                True,
                "Premium refined copper wire extracted directly from certified electronic waste recycling. 100% recycled content with zero mining footprint.",
                "Purity: 99.8% Electrolytic Grade\nForm: Spooled 2mm Wire\nConductivity: Standard IACS\nOrigin: Server Cabling Recycled Batch REC-01\nCertification: ISO-14001 Compliant"
            ),
            (
                "Refined 24K Secondary Gold & Silver Precious Metal Concentrate",
                cat_objects["Circuit Boards & PCBs"],
                rec2,
                "Precious Metal Concentrate",
                Decimal("240.00"),
                "Grams",
                Decimal("6200.00"),
                Decimal("5950.00"),
                RecycledProduct.Condition.INGOT_PELLET,
                True,
                "Recovered fine precious metal concentrates extracted from enterprise CPU pins and gold-plated edge contacts via closed-loop hydrometallurgical processing.",
                "Purity: 99.5%+ Precious Concentrate\nMetal Composition: Au (82%), Ag (16%), Pd traces\nForm: Sintered Granules\nOrigin: PCB Recovery Batch"
            ),
            (
                "Refurbished Dell UltraSharp 24-inch IPS Professional Monitors",
                cat_objects["Monitors & Displays"],
                None,
                "Refurbished IT Hardware",
                Decimal("15.00"),
                "Units",
                Decimal("7500.00"),
                Decimal("6800.00"),
                RecycledProduct.Condition.REFURBISHED_A,
                True,
                "Fully tested, inspected, and refurbished Dell UltraSharp 24-inch FHD IPS panels with power cables and adjustable ergonomic stands.",
                "Model: U2419H IPS 1080p\nCondition: Grade A (Zero Dead Pixels, Tested Power Supply)\nPorts: HDMI, DisplayPort, USB 3.0 Hub\nWarranty: 6 Months Eco-Guarantee"
            ),
            (
                "Recycled Engineering ABS Polymer Granules (Black Pellet)",
                cat_objects["Computers & Servers"],
                None,
                "Recycled Polymer Resin",
                Decimal("400.00"),
                "kg",
                Decimal("145.00"),
                Decimal("130.00"),
                RecycledProduct.Condition.RAW_MATERIAL,
                False,
                "High-impact recycled ABS plastic pellets granulating discarded desktop PC and server casing enclosures. Excellent injection molding fluidity.",
                "Polymer: Acrylonitrile Butadiene Styrene (ABS)\nMFI: 18 g/10min at 220°C\nColor: Deep Matte Black\nForm: 3mm Pellets\nPackaging: 25kg Eco-Bags"
            ),
            (
                "Refurbished Intel Xeon E5-2680 v4 14-Core Server Processors",
                cat_objects["Computers & Servers"],
                None,
                "Tested Semiconductor",
                Decimal("20.00"),
                "Units",
                Decimal("4200.00"),
                Decimal("3900.00"),
                RecycledProduct.Condition.TESTED_WORKING,
                True,
                "100% stress-tested server microprocessors salvaged from decommissioning cloud datacenters. Thermal tested under full Prime95 load.",
                "Cores: 14 Cores / 28 Threads\nBase Clock: 2.40 GHz / Turbo: 3.30 GHz\nSocket: LGA 2011-3\nOrigin: Datacenter Cloud Migration"
            ),
        ]

        created_products = []
        for name, cat, rec, mat_type, qty, unit, price, disc_price, cond, feat, desc, specs in products_data:
            prod, _ = RecycledProduct.objects.get_or_create(
                product_name=name,
                defaults={
                    "category": cat,
                    "recycling_record": rec,
                    "material_type": mat_type,
                    "quantity_available": qty,
                    "unit": unit,
                    "price": price,
                    "discount_price": disc_price,
                    "product_condition": cond,
                    "is_featured": feat,
                    "status": RecycledProduct.Status.PUBLISHED,
                    "description": desc,
                    "specifications": specs,
                    "origin_recycling_center": "Central Eco-Recovery Facility #1"
                }
            )
            created_products.append(prod)

        self.stdout.write(f"Created {len(created_products)} marketplace recycled products.")

        # -------------------------------------------------------------
        # 6. CREATE SAMPLE MARKETPLACE ORDERS
        # -------------------------------------------------------------
        ord1, _ = Order.objects.get_or_create(
            order_number="ORD-2026-8812",
            defaults={
                "company": comp_user1,
                "company_name": "EcoMetal Refining & Smelting Corp",
                "contact_person": "Rohan Mehta",
                "contact_phone": "+91 22 2847 9000",
                "contact_email": "procurement@ecometal.com",
                "gst_tax_id": "27AAACE1234F1Z8",
                "billing_address": "Plot 45-B, Hinjewadi Industrial Phase II",
                "shipping_address": "Plot 45-B, Hinjewadi Industrial Phase II",
                "city": "Pune",
                "state": "Maharashtra",
                "postal_code": "411057",
                "subtotal": Decimal("15600.00"),
                "tax_amount": Decimal("2808.00"),
                "shipping_fee": Decimal("0.00"),
                "total_amount": Decimal("18408.00"),
                "payment_method": Order.PaymentMethod.BANK_TRANSFER,
                "payment_status": Order.PaymentStatus.PAID,
                "payment_transaction_id": "RTGS-HDFC-991283401",
                "order_status": Order.Status.SHIPPED,
                "shipping_carrier": "Green Freight Express Logistics",
                "tracking_number": "TRK-2026-GF-98124",
                "admin_notes": "Palletized with certified Zero-Landfill manifest."
            }
        )
        OrderItem.objects.get_or_create(
            order=ord1,
            product=created_products[0],
            defaults={
                "product_name": created_products[0].product_name,
                "sku": created_products[0].sku,
                "unit_price": created_products[0].effective_price,
                "quantity": 20,
                "total_price": Decimal("15600.00")
            }
        )

        # Order 2: Placed
        ord2, _ = Order.objects.get_or_create(
            order_number="ORD-2026-9930",
            defaults={
                "company": comp_user2,
                "company_name": "Apex Clean Electronics Manufacturing Ltd",
                "contact_person": "Ananya Deshmukh",
                "contact_phone": "+91 80 4123 7890",
                "contact_email": "orders@apextech.com",
                "gst_tax_id": "29AABCA9876E1ZQ",
                "billing_address": "Electronics City Phase 1, Hosur Road",
                "shipping_address": "Electronics City Phase 1, Hosur Road",
                "city": "Bengaluru",
                "state": "Karnataka",
                "postal_code": "560100",
                "subtotal": Decimal("13600.00"),
                "tax_amount": Decimal("2448.00"),
                "shipping_fee": Decimal("0.00"),
                "total_amount": Decimal("16048.00"),
                "payment_method": Order.PaymentMethod.INVOICE_ON_DELIVERY,
                "payment_status": Order.PaymentStatus.PENDING,
                "order_status": Order.Status.CONFIRMED,
                "shipping_carrier": "BlueDart Apex Express",
                "tracking_number": "BD-88219401"
            }
        )
        OrderItem.objects.get_or_create(
            order=ord2,
            product=created_products[2],
            defaults={
                "product_name": created_products[2].product_name,
                "sku": created_products[2].sku,
                "unit_price": created_products[2].effective_price,
                "quantity": 2,
                "total_price": Decimal("13600.00")
            }
        )

        # -------------------------------------------------------------
        # 7. CREATE SYSTEM NOTIFICATIONS
        # -------------------------------------------------------------
        Notification.objects.get_or_create(
            user=user1,
            title="E-Waste Approved & +75 Points Awarded!",
            defaults={
                "message": "Your submission 'Dell UltraSharp Monitors' has been approved. Collector Rajesh Kumar has been dispatched.",
                "link": f"/user/my-ewaste/{sub3.id}/",
                "notification_type": Notification.NotificationType.SUCCESS,
                "is_read": False
            }
        )

        Notification.objects.get_or_create(
            user=collector1,
            title="New Doorstep Pickup Assigned",
            defaults={
                "message": f"Pickup task {sub3.tracking_id} at Mumbai assigned to your vehicle schedule.",
                "link": f"/collector/pickups/{asgn3.id}/",
                "notification_type": Notification.NotificationType.INFO,
                "is_read": False
            }
        )

        Notification.objects.get_or_create(
            user=comp_user1,
            title="Order #ORD-2026-8812 Shipped!",
            defaults={
                "message": "Your recycled copper wire lot has been shipped via Green Freight Express (AWB: TRK-2026-GF-98124).",
                "link": f"/company/orders/{ord1.id}/",
                "notification_type": Notification.NotificationType.SUCCESS,
                "is_read": False
            }
        )

        self.stdout.write(self.style.SUCCESS("EcoCycle platform database successfully seeded!"))
