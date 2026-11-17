import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from users.models import (
    User, UserProfile, CollectorProfile, CompanyProfile,
    EWasteCategory, EWasteSubmission, CollectorAssignment,
    PickupRecord, Notification
)
from users.decorators import (
    admin_required, super_admin_required, send_system_notification
)
from admin.models import RecyclingRecord, SystemAuditLog
from admin.forms import (
    EWasteVerificationForm, AssignCollectorForm, RecyclingRecordForm,
    ProductCreationForm, ProductEditForm, AdminOrderUpdateForm, CollectorCreationForm,
    CompanyVerificationForm, CategoryForm, AdminOrderPlacementForm
)
from company.models import RecycledProduct, Order, OrderItem


# -------------------------------------------------------------------
# OPERATIONAL ADMIN PANEL VIEWS
# -------------------------------------------------------------------

@login_required
@admin_required
def admin_dashboard(request):
    total_users = User.objects.filter(role=User.Role.USER).count()
    total_collectors = User.objects.filter(role=User.Role.COLLECTOR).count()
    total_companies = CompanyProfile.objects.filter(verification_status=CompanyProfile.VerificationStatus.VERIFIED).count()
    
    pending_submissions = EWasteSubmission.objects.filter(status__in=[
        EWasteSubmission.Status.SUBMITTED,
        EWasteSubmission.Status.UNDER_VERIFICATION
    ]).count()
    
    approved_submissions = EWasteSubmission.objects.filter(status=EWasteSubmission.Status.APPROVED).count()
    pending_pickups = CollectorAssignment.objects.filter(status__in=[
        CollectorAssignment.AssignmentStatus.ASSIGNED,
        CollectorAssignment.AssignmentStatus.ACCEPTED,
        CollectorAssignment.AssignmentStatus.ON_THE_WAY
    ]).count()
    
    collected_ewaste_kg = EWasteSubmission.objects.filter(
        status__in=[
            EWasteSubmission.Status.COLLECTED,
            EWasteSubmission.Status.AT_RECYCLING_CENTER,
            EWasteSubmission.Status.RECYCLING_IN_PROGRESS,
            EWasteSubmission.Status.RECYCLED,
            EWasteSubmission.Status.COMPLETED
        ]
    ).aggregate(total=Sum('approximate_weight_kg'))['total'] or Decimal('0.00')

    recycling_in_progress = RecyclingRecord.objects.filter(
        status__in=[RecyclingRecord.Status.RECEIVED, RecyclingRecord.Status.SORTING, RecyclingRecord.Status.PROCESSING]
    ).count()

    published_products = RecycledProduct.objects.filter(status=RecycledProduct.Status.PUBLISHED).count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.filter(
        payment_status__in=[Order.PaymentStatus.PAID, Order.PaymentStatus.PENDING]
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # Quick triage queues
    recent_submissions = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.SUBMITTED, EWasteSubmission.Status.UNDER_VERIFICATION]
    ).order_by('-created_at')[:6]

    ready_to_recycle_submissions = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.COLLECTED, EWasteSubmission.Status.AT_RECYCLING_CENTER]
    ).order_by('-updated_at')[:6]

    ready_to_recycle_count = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.COLLECTED, EWasteSubmission.Status.AT_RECYCLING_CENTER]
    ).count()

    recent_orders = Order.objects.order_by('-created_at')[:5]

    context = {
        'total_users': total_users,
        'total_collectors': total_collectors,
        'total_companies': total_companies,
        'pending_submissions': pending_submissions,
        'approved_submissions': approved_submissions,
        'pending_pickups': pending_pickups,
        'collected_ewaste_kg': collected_ewaste_kg,
        'ready_to_recycle_count': ready_to_recycle_count,
        'ready_to_recycle_submissions': ready_to_recycle_submissions,
        'recycling_in_progress': recycling_in_progress,
        'published_products': published_products,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'recent_submissions': recent_submissions,
        'recent_orders': recent_orders,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@login_required
@admin_required
def admin_ewaste_list_view(request):
    status_filter = request.GET.get('status', 'ALL')
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '')

    submissions = EWasteSubmission.objects.all().select_related('user', 'category', 'collector_assignment')

    if status_filter != 'ALL' and status_filter:
        submissions = submissions.filter(status=status_filter)
    if category_id:
        submissions = submissions.filter(category_id=category_id)
    if query:
        submissions = submissions.filter(
            Q(tracking_id__icontains=query) |
            Q(waste_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(pickup_city__icontains=query)
        )

    categories = EWasteCategory.objects.all()
    statuses = EWasteSubmission.Status.choices

    context = {
        'submissions': submissions,
        'categories': categories,
        'statuses': statuses,
        'selected_status': status_filter,
        'selected_category': category_id,
        'query': query,
    }
    return render(request, 'admin_panel/ewaste_list.html', context)


@login_required
@admin_required
def admin_ewaste_verify_view(request, submission_id):
    submission = get_object_or_404(EWasteSubmission, id=submission_id)

    if request.method == 'POST':
        form = EWasteVerificationForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            points = form.cleaned_data.get('reward_points') or 0
            admin_notes = form.cleaned_data.get('admin_notes')
            rejection_reason = form.cleaned_data.get('rejection_reason')

            submission.admin_notes = admin_notes

            if action == 'APPROVE':
                collector = form.cleaned_data.get('collector')
                scheduled_date = form.cleaned_data.get('scheduled_date') or submission.preferred_date
                collector_notes = form.cleaned_data.get('collector_notes')

                submission.reward_points_awarded = points

                # Credit user eco points
                user_profile, _ = UserProfile.objects.get_or_create(user=submission.user)
                user_profile.eco_points += points
                user_profile.total_recycled_items += submission.quantity
                user_profile.save()

                if collector:
                    # Optional collector assigned during verification
                    assignment, _ = CollectorAssignment.objects.update_or_create(
                        submission=submission,
                        defaults={
                            'collector': collector,
                            'assigned_by': request.user,
                            'scheduled_date': scheduled_date,
                            'scheduled_slot': submission.get_preferred_time_slot_display(),
                            'status': CollectorAssignment.AssignmentStatus.ASSIGNED,
                            'collector_notes': collector_notes
                        }
                    )
                    submission.status = EWasteSubmission.Status.COLLECTOR_ASSIGNED
                    submission.save()

                    # Notify collector
                    send_system_notification(
                        user=collector,
                        title="New Pickup Assigned!",
                        message=f"You have been assigned pickup {submission.tracking_id} for '{submission.waste_name}' at {submission.pickup_city}.",
                        link=f"/collector/pickups/{assignment.id}/",
                        notification_type="INFO"
                    )

                    # Notify user
                    send_system_notification(
                        user=submission.user,
                        title="E-Waste Request Approved & Collector Assigned!",
                        message=f"Your request '{submission.waste_name}' was approved (+{points} Eco-Points). Collector {collector.get_full_name() or collector.username} has been assigned for pickup on {scheduled_date}.",
                        link=f"/user/my-ewaste/{submission.id}/",
                        notification_type="SUCCESS"
                    )
                    messages.success(request, f"Submission {submission.tracking_id} approved and assigned to collector {collector.username}.")
                else:
                    # Approved without immediate collector assignment (optional)
                    submission.status = EWasteSubmission.Status.APPROVED
                    submission.save()

                    send_system_notification(
                        user=submission.user,
                        title="E-Waste Request Approved!",
                        message=f"Your request '{submission.waste_name}' was approved. +{points} Eco-Points credited to your account.",
                        link=f"/user/my-ewaste/{submission.id}/",
                        notification_type="SUCCESS"
                    )
                    messages.success(request, f"Submission {submission.tracking_id} approved. (Collector unassigned - can be assigned anytime).")

                return redirect('admin_ewaste_list')

            elif action == 'REJECT':
                submission.status = EWasteSubmission.Status.REJECTED
                submission.rejection_reason = rejection_reason or "Does not meet e-waste collection criteria."
                submission.save()

                send_system_notification(
                    user=submission.user,
                    title="E-Waste Request Declined",
                    message=f"Your request '{submission.waste_name}' could not be accepted. Reason: {submission.rejection_reason}",
                    link=f"/user/my-ewaste/{submission.id}/",
                    notification_type="DANGER"
                )
                messages.warning(request, f"Submission {submission.tracking_id} rejected.")
                return redirect('admin_ewaste_list')

            elif action == 'REQUEST_INFO':
                submission.status = EWasteSubmission.Status.UNDER_VERIFICATION
                submission.save()

                send_system_notification(
                    user=submission.user,
                    title="More Information Needed",
                    message=f"Our team is reviewing your item '{submission.waste_name}'. {admin_notes}",
                    link=f"/user/my-ewaste/{submission.id}/",
                    notification_type="WARNING"
                )
                messages.info(request, f"Submission {submission.tracking_id} marked as Under Verification.")
                return redirect('admin_ewaste_list')
    else:
        existing_assignment = getattr(submission, 'collector_assignment', None)
        initial_data = {
            'admin_notes': submission.admin_notes,
            'collector': existing_assignment.collector if existing_assignment else None,
            'scheduled_date': existing_assignment.scheduled_date if existing_assignment else submission.preferred_date,
            'collector_notes': existing_assignment.collector_notes if existing_assignment else ''
        }
        form = EWasteVerificationForm(initial=initial_data)

    return render(request, 'admin_panel/ewaste_verify.html', {'submission': submission, 'form': form})


@login_required
@admin_required
def admin_delete_ewaste_submission_view(request, submission_id):
    submission = get_object_or_404(EWasteSubmission, id=submission_id)
    if request.method == 'POST':
        waste_name = submission.waste_name
        tracking_id = submission.tracking_id
        submission.delete()
        messages.success(request, f"E-Waste submission '{waste_name}' ({tracking_id}) has been deleted successfully.")
    return redirect('admin_ewaste_list')


@login_required
@admin_required
def admin_collectors_list_view(request):
    collectors = User.objects.filter(role=User.Role.COLLECTOR).select_related('collector_profile').order_by('-date_joined')
    query = request.GET.get('q')

    if query:
        collectors = collectors.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(collector_profile__service_area__icontains=query)
        )

    if request.method == 'POST':
        messages.error(request, "Operational Admins are not permitted to add local collectors. Local collectors must be onboarded by the Super Admin.")
        return redirect('admin_collectors_list')

    total_count = collectors.count()
    available_count = collectors.filter(collector_profile__is_available=True).count()
    verified_count = collectors.filter(collector_profile__verification_status=CollectorProfile.VerificationStatus.VERIFIED).count()

    return render(request, 'admin_panel/collectors_list.html', {
        'collectors': collectors,
        'query': query,
        'total_count': total_count,
        'available_count': available_count,
        'verified_count': verified_count,
    })


@login_required
@admin_required
def admin_assign_collector_view(request, submission_id):
    submission = get_object_or_404(EWasteSubmission, id=submission_id)
    
    # Get available collectors with workload stats
    collectors = User.objects.filter(role=User.Role.COLLECTOR, is_active=True).select_related('collector_profile')

    if request.method == 'POST':
        form = AssignCollectorForm(request.POST)
        if form.is_valid():
            collector = form.cleaned_data['collector']
            scheduled_date = form.cleaned_data.get('scheduled_date') or submission.preferred_date
            scheduled_slot = form.cleaned_data.get('scheduled_slot') or submission.get_preferred_time_slot_display()
            notes = form.cleaned_data.get('collector_notes')

            # Create or update assignment
            assignment, created = CollectorAssignment.objects.update_or_create(
                submission=submission,
                defaults={
                    'collector': collector,
                    'assigned_by': request.user,
                    'scheduled_date': scheduled_date,
                    'scheduled_slot': scheduled_slot,
                    'status': CollectorAssignment.AssignmentStatus.ASSIGNED,
                    'collector_notes': notes
                }
            )

            submission.status = EWasteSubmission.Status.COLLECTOR_ASSIGNED
            submission.save()

            # Notify collector
            send_system_notification(
                user=collector,
                title="New Pickup Assigned!",
                message=f"You have been assigned pickup {submission.tracking_id} for '{submission.waste_name}' at {submission.pickup_city}.",
                link=f"/collector/pickups/{assignment.id}/",
                notification_type="INFO"
            )

            # Notify user
            send_system_notification(
                user=submission.user,
                title="Collector Assigned",
                message=f"Collector {collector.get_full_name() or collector.username} has been assigned for your pickup on {scheduled_date}.",
                link=f"/user/my-ewaste/{submission.id}/",
                notification_type="INFO"
            )

            messages.success(request, f"Collector {collector.username} successfully assigned to {submission.tracking_id}.")
            return redirect('admin_ewaste_list')
    else:
        form = AssignCollectorForm(initial={
            'scheduled_date': submission.preferred_date,
            'scheduled_slot': submission.get_preferred_time_slot_display()
        })

    return render(request, 'admin_panel/assign_collector.html', {
        'submission': submission,
        'form': form,
        'collectors': collectors
    })


@login_required
@admin_required
def admin_recycling_list_view(request):
    records = RecyclingRecord.objects.all().select_related('submission', 'material_category', 'processed_by')
    status_filter = request.GET.get('status', 'ALL')
    if status_filter != 'ALL' and status_filter:
        records = records.filter(status=status_filter)

    # Submissions at center waiting for recycling record
    ready_for_recycling = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.AT_RECYCLING_CENTER, EWasteSubmission.Status.COLLECTED]
    ).exclude(recycling_records__isnull=False)

    return render(request, 'admin_panel/recycling_list.html', {
        'records': records,
        'ready_for_recycling': ready_for_recycling,
        'selected_status': status_filter
    })


@login_required
@admin_required
def admin_recycle_submission_view(request, submission_id):
    submission = get_object_or_404(EWasteSubmission, id=submission_id)
    categories = EWasteCategory.objects.filter(is_active=True)

    if request.method == 'POST':
        product_name = request.POST.get('product_name', f"Recycled {submission.waste_name}").strip()
        category_id = request.POST.get('category') or submission.category.id
        category = get_object_or_404(EWasteCategory, id=category_id)
        
        material_type = request.POST.get('material_type', f"Recovered {category.name} Material").strip()
        product_condition = request.POST.get('product_condition', RecycledProduct.Condition.REFURBISHED_A)
        
        try:
            quantity_available = Decimal(request.POST.get('quantity_available', submission.quantity or 1))
        except Exception:
            quantity_available = Decimal('1.00')
            
        unit = request.POST.get('unit', 'Units').strip()
        
        try:
            price = Decimal(request.POST.get('price', '500.00'))
        except Exception:
            price = Decimal('500.00')
            
        description = request.POST.get('description', f"Certified eco-recycled product extracted from {submission.waste_name}. Tested and processed for enterprise secondary reuse.").strip()
        specifications = request.POST.get('specifications', f"Origin E-Waste: {submission.waste_name}\nTracking ID: {submission.tracking_id}\nWeight: {submission.approximate_weight_kg} kg\nCertified Zero-Landfill Process").strip()

        # 1. Create or update RecyclingRecord
        recycling_record, _ = RecyclingRecord.objects.get_or_create(
            submission=submission,
            defaults={
                'waste_type': submission.waste_name,
                'original_weight_kg': submission.approximate_weight_kg,
                'recovered_material': material_type,
                'material_category': category,
                'recovered_quantity': quantity_available,
                'recovered_unit': unit,
                'processing_method': RecyclingRecord.ProcessingMethod.REFURBISHING if 'REFURBISHED' in product_condition else RecyclingRecord.ProcessingMethod.DISMANTLING,
                'processing_description': description,
                'status': RecyclingRecord.Status.PRODUCT_READY,
                'recycling_date': timezone.now().date(),
                'received_date': submission.created_at.date() if submission.created_at else timezone.now().date(),
                'processed_by': request.user
            }
        )

        product_image = request.FILES.get('product_image') or (submission.primary_image if submission.primary_image else None)

        # 2. Create and publish RecycledProduct directly
        product = RecycledProduct.objects.create(
            recycling_record=recycling_record,
            product_name=product_name,
            category=category,
            material_type=material_type,
            quantity_available=quantity_available,
            unit=unit,
            price=price,
            product_condition=product_condition,
            description=description,
            specifications=specifications,
            status=RecycledProduct.Status.PUBLISHED,
            primary_image=product_image,
            is_featured=True
        )

        # 3. Update EWasteSubmission status to RECYCLED
        submission.status = EWasteSubmission.Status.RECYCLED
        submission.save()

        # 4. Notify Citizen User
        send_system_notification(
            user=submission.user,
            title="E-Waste Recycled! 🌱",
            message=f"Great news! Your e-waste '{submission.waste_name}' has been successfully recycled into '{product.product_name}'. Thank you for protecting the environment!",
            link=f"/user/my-ewaste/{submission.id}/",
            notification_type="SUCCESS"
        )

        # 5. Notify Verified Companies
        for comp_user in User.objects.filter(role=User.Role.COMPANY):
            send_system_notification(
                user=comp_user,
                title=f"New Recycled Product: {product.product_name}",
                message=f"New recycled stock '{product.product_name}' ({product.quantity_available} {product.unit}) is now live in the marketplace for purchase.",
                link=f"/marketplace/products/{product.slug}/",
                notification_type="INFO"
            )

        messages.success(request, f"Item successfully recycled! Product '{product.product_name}' is now live on the Recycled Products catalog & Company Marketplace.")
        return redirect('admin_recycled_products_list')

    # Defaults for GET
    default_name = f"Recycled {submission.waste_name}"
    default_qty = submission.quantity if submission.quantity > 0 else 1
    default_unit = "Units" if submission.quantity > 1 else "kg"
    default_price = round(submission.approximate_weight_kg * Decimal('150.00'), 2) if submission.approximate_weight_kg > 0 else Decimal('500.00')

    context = {
        'submission': submission,
        'categories': categories,
        'conditions': RecycledProduct.Condition.choices,
        'default_name': default_name,
        'default_qty': default_qty,
        'default_unit': default_unit,
        'default_price': default_price,
    }
    return render(request, 'admin_panel/recycle_submission.html', context)


@login_required
@admin_required
def admin_recycled_products_list_view(request):
    products = RecycledProduct.objects.all().select_related('category', 'recycling_record').order_by('-created_at')
    category_id = request.GET.get('category')
    query = request.GET.get('q')

    if category_id:
        products = products.filter(category_id=category_id)
    if query:
        products = products.filter(
            Q(product_name__icontains=query) |
            Q(sku__icontains=query) |
            Q(material_type__icontains=query)
        )

    categories = EWasteCategory.objects.filter(is_active=True)

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_id,
        'query': query,
        'total_count': products.count(),
    }
    return render(request, 'admin_panel/recycled_products_list.html', context)


@login_required
@admin_required
def admin_recycled_product_detail_view(request, product_id):
    product = get_object_or_404(
        RecycledProduct.objects.select_related(
            'category',
            'recycling_record',
            'recycling_record__submission',
            'recycling_record__submission__user'
        ),
        id=product_id
    )

    # Order items containing this product
    order_items = OrderItem.objects.filter(product=product).select_related(
        'order',
        'order__company',
        'order__assigned_collector'
    ).order_by('-order__created_at')

    # Aggregated metrics for Admin
    total_sold = sum(item.quantity for item in order_items)
    total_revenue = sum(item.total_price for item in order_items)
    total_orders_count = order_items.values('order_id').distinct().count()
    distinct_buyers_count = order_items.values('order__company').distinct().count()
    initial_produced_quantity = product.quantity_available + Decimal(str(total_sold))

    # In-page edit / stock adjustment
    if request.method == 'POST':
        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            updated_product = form.save()
            if updated_product.quantity_available <= 0 and updated_product.status == RecycledProduct.Status.PUBLISHED:
                updated_product.status = RecycledProduct.Status.OUT_OF_STOCK
                updated_product.save()
            messages.success(request, f"Product '{updated_product.product_name}' details & stock updated successfully.")
            return redirect('admin_recycled_product_detail', product_id=product.id)
        else:
            messages.error(request, "Please correct the errors in the update form.")
    else:
        form = ProductEditForm(instance=product)

    context = {
        'product': product,
        'order_items': order_items,
        'total_sold': total_sold,
        'total_revenue': total_revenue,
        'total_orders_count': total_orders_count,
        'distinct_buyers_count': distinct_buyers_count,
        'initial_produced_quantity': initial_produced_quantity,
        'form': form,
    }
    return render(request, 'admin_panel/product_detail.html', context)


@login_required
@admin_required
def admin_delete_recycled_product_view(request, product_id):
    product = get_object_or_404(RecycledProduct, id=product_id)
    if request.method == 'POST':
        p_name = product.product_name
        product.delete()
        messages.success(request, f"Product '{p_name}' has been deleted from the catalog.")
    return redirect('admin_recycled_products_list')


@login_required
@admin_required
def admin_create_recycling_record_view(request):
    submission_id = request.GET.get('submission_id')
    submission = None
    initial_data = {'received_date': timezone.now().date()}

    if submission_id:
        submission = get_object_or_404(EWasteSubmission, id=submission_id)
        initial_data.update({
            'submission': submission,
            'waste_type': submission.waste_name,
            'original_weight_kg': submission.approximate_weight_kg,
            'material_category': submission.category,
        })

    if request.method == 'POST':
        form = RecyclingRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.processed_by = request.user
            record.save()

            if record.submission:
                record.submission.status = EWasteSubmission.Status.RECYCLING_IN_PROGRESS
                record.submission.save()

                send_system_notification(
                    user=record.submission.user,
                    title="Recycling Process Started",
                    message=f"Your e-waste '{record.submission.waste_name}' has entered recycling processing (Batch: {record.batch_code}).",
                    link=f"/user/my-ewaste/{record.submission.id}/",
                    notification_type="INFO"
                )

            messages.success(request, f"Recycling record {record.batch_code} created.")
            return redirect('admin_recycling_list')
    else:
        form = RecyclingRecordForm(initial=initial_data)

    return render(request, 'admin_panel/recycling_create.html', {'form': form, 'submission': submission})


@login_required
@admin_required
def admin_update_recycling_record_view(request, record_id):
    record = get_object_or_404(RecyclingRecord, id=record_id)
    if request.method == 'POST':
        form = RecyclingRecordForm(request.POST, instance=record)
        if form.is_valid():
            rec = form.save()
            if rec.status in [RecyclingRecord.Status.RECOVERED, RecyclingRecord.Status.PRODUCT_READY]:
                if rec.submission:
                    rec.submission.status = EWasteSubmission.Status.RECYCLED
                    rec.submission.save()
                    send_system_notification(
                        user=rec.submission.user,
                        title="Recycling Completed! 🌿",
                        message=f"Your discarded electronics have been completely recycled into reusable secondary raw materials.",
                        link=f"/user/my-ewaste/{rec.submission.id}/",
                        notification_type="SUCCESS"
                    )

            messages.success(request, f"Recycling batch {record.batch_code} updated.")
            return redirect('admin_recycling_list')
    else:
        form = RecyclingRecordForm(instance=record)

    return render(request, 'admin_panel/recycling_create.html', {'form': form, 'record': record, 'is_edit': True})


@login_required
@admin_required
def admin_publish_product_view(request):
    record_id = request.GET.get('record_id')
    recycling_record = None
    initial_data = {'status': RecycledProduct.Status.PUBLISHED}

    if record_id:
        recycling_record = get_object_or_404(RecyclingRecord, id=record_id)
        initial_data.update({
            'recycling_record': recycling_record,
            'product_name': f"Recovered {recycling_record.recovered_material}",
            'category': recycling_record.material_category,
            'material_type': recycling_record.recovered_material,
            'quantity_available': recycling_record.recovered_quantity,
            'unit': recycling_record.recovered_unit,
            'description': f"High-grade recovered materials extracted from eco-friendly electronic waste recycling. {recycling_record.processing_description}",
            'specifications': f"Purity/Grade: Industrial Standard\nOriginal Waste Type: {recycling_record.waste_type}\nBatch Code: {recycling_record.batch_code}\nCertified Zero-Landfill Process",
        })

    if request.method == 'POST':
        form = ProductCreationForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            if recycling_record:
                recycling_record.status = RecyclingRecord.Status.PRODUCT_READY
                recycling_record.save()

            messages.success(request, f"Product '{product.product_name}' published to Marketplace successfully!")
            return redirect('admin_dashboard')
    else:
        form = ProductCreationForm(initial=initial_data)

    return render(request, 'admin_panel/publish_product.html', {'form': form, 'recycling_record': recycling_record})


@login_required
@admin_required
def admin_order_list_view(request):
    orders = Order.objects.all().select_related('company').order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        orders = orders.filter(order_status=status_filter)

    return render(request, 'admin_panel/order_list.html', {'orders': orders, 'selected_status': status_filter})


@login_required
@admin_required
def admin_order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    prev_collector = order.assigned_collector
    if request.method == 'POST':
        form = AdminOrderUpdateForm(request.POST, instance=order)
        if form.is_valid():
            ord_obj = form.save()

            # If collector is assigned / updated, notify collector
            if ord_obj.assigned_collector and ord_obj.assigned_collector != prev_collector:
                send_system_notification(
                    user=ord_obj.assigned_collector,
                    title=f"New Delivery Assignment: {ord_obj.order_number}",
                    message=f"You have been assigned to deliver order {ord_obj.order_number} to {ord_obj.company_name} at {ord_obj.shipping_address}, {ord_obj.city} (Phone: {ord_obj.contact_phone}).",
                    link="/collector/dashboard/",
                    notification_type="INFO"
                )

            # Notify purchasing company
            collector_msg = f" Assigned Collector: {ord_obj.assigned_collector.get_full_name() or ord_obj.assigned_collector.username} ({ord_obj.assigned_collector.phone})." if ord_obj.assigned_collector else ""
            send_system_notification(
                user=ord_obj.company,
                title=f"Order Status Update: {ord_obj.order_number}",
                message=f"Your order status has changed to '{ord_obj.get_order_status_display()}'.{collector_msg} Carrier: {ord_obj.shipping_carrier or 'Standard'}.",
                link=f"/company/orders/{ord_obj.id}/",
                notification_type="INFO"
            )

            messages.success(request, f"Order {order.order_number} details & collector assignment updated.")
            return redirect('admin_order_detail', order_id=order.id)
    else:
        form = AdminOrderUpdateForm(instance=order)

    return render(request, 'admin_panel/order_detail.html', {'order': order, 'form': form})


@login_required
@admin_required
def admin_create_order_view(request):
    companies = User.objects.filter(role=User.Role.COMPANY).select_related('company_profile')
    products = RecycledProduct.objects.filter(status=RecycledProduct.Status.PUBLISHED, quantity_available__gt=0).select_related('category')
    
    # Prepare JSON data for client-side instant auto-population and calculations
    companies_data = {}
    for comp in companies:
        profile = getattr(comp, 'company_profile', None)
        companies_data[comp.id] = {
            'company_name': (profile.company_name if profile else '') or comp.first_name or comp.username,
            'contact_person': comp.get_full_name() or comp.username,
            'contact_phone': comp.phone or '',
            'contact_email': comp.email or '',
            'gst_tax_id': (profile.gst_tax_id if profile else '') or '',
            'billing_address': (profile.corporate_address if profile else '') or comp.address or '',
            'shipping_address': (profile.corporate_address if profile else '') or comp.address or '',
            'city': (profile.city if profile else '') or comp.city or '',
            'state': (profile.state if profile else '') or comp.state or '',
            'country': (profile.country if profile else '') or comp.country or 'India',
            'postal_code': (profile.postal_code if profile else '') or comp.pincode or '',
        }
        
    products_data = {}
    for prod in products:
        products_data[prod.id] = {
            'name': prod.product_name,
            'sku': prod.sku,
            'unit': prod.unit,
            'price': float(prod.effective_price),
            'stock': float(prod.quantity_available),
            'image_url': prod.primary_image.url if prod.primary_image else '',
            'condition': prod.get_product_condition_display(),
        }
        
    if request.method == 'POST':
        form = AdminOrderPlacementForm(request.POST)
        if form.is_valid():
            company_user = form.cleaned_data['company']
            product = form.cleaned_data['product']
            quantity = form.cleaned_data['quantity']
            
            # Validate inventory availability
            if quantity > product.quantity_available:
                messages.error(
                    request,
                    f"Cannot place order: '{product.product_name}' only has {int(product.quantity_available)} {product.unit} available in stock!"
                )
                return render(request, 'admin_panel/order_create.html', {
                    'form': form,
                    'companies_json': json.dumps(companies_data),
                    'products_json': json.dumps(products_data),
                    'companies_count': companies.count(),
                    'products_count': products.count()
                })
                
            unit_price = product.effective_price
            subtotal = unit_price * quantity
            tax_amount = round(subtotal * Decimal('0.18'), 2)
            shipping_fee = Decimal('0.00') if subtotal > Decimal('50000.00') else Decimal('1500.00')
            total_amount = subtotal + tax_amount + shipping_fee
            
            assigned_collector = form.cleaned_data.get('assigned_collector')
            
            order = Order.objects.create(
                company=company_user,
                company_name=form.cleaned_data['company_name'],
                contact_person=form.cleaned_data['contact_person'],
                contact_phone=form.cleaned_data['contact_phone'],
                contact_email=form.cleaned_data['contact_email'],
                gst_tax_id=form.cleaned_data.get('gst_tax_id', ''),
                billing_address=form.cleaned_data['billing_address'],
                shipping_address=form.cleaned_data['shipping_address'],
                city=form.cleaned_data['city'],
                state=form.cleaned_data['state'],
                country=form.cleaned_data.get('country') or 'India',
                postal_code=form.cleaned_data['postal_code'],
                subtotal=subtotal,
                tax_amount=tax_amount,
                shipping_fee=shipping_fee,
                total_amount=total_amount,
                payment_method=form.cleaned_data['payment_method'],
                payment_status=form.cleaned_data['payment_status'],
                order_status=form.cleaned_data['order_status'],
                assigned_collector=assigned_collector,
                admin_notes=form.cleaned_data.get('admin_notes', '')
            )
            
            OrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.product_name,
                sku=product.sku,
                unit_price=unit_price,
                quantity=quantity,
                total_price=subtotal
            )
            
            # Deduct inventory
            product.quantity_available -= quantity
            if product.quantity_available == 0:
                product.status = RecycledProduct.Status.OUT_OF_STOCK
            product.save()
            
            # Send notification to purchasing company
            send_system_notification(
                user=company_user,
                title=f"New Order Created: {order.order_number}",
                message=f"A new corporate order for ₹{order.total_amount} ({quantity}x {product.product_name}) was placed for your company by the administration.",
                link=f"/company/orders/{order.id}/",
                notification_type="SUCCESS"
            )
            
            # If collector is assigned, notify collector
            if assigned_collector:
                send_system_notification(
                    user=assigned_collector,
                    title=f"New Delivery Assignment: {order.order_number}",
                    message=f"You have been assigned to deliver order {order.order_number} to {order.company_name} at {order.shipping_address}, {order.city} (Phone: {order.contact_phone}).",
                    link="/collector/dashboard/",
                    notification_type="INFO"
                )
                
            messages.success(request, f"Order {order.order_number} successfully placed for '{order.company_name}'!")
            return redirect('admin_order_detail', order_id=order.id)
        else:
            messages.error(request, "Please correct the highlighted errors in the order form.")
    else:
        form = AdminOrderPlacementForm()
        
    return render(request, 'admin_panel/order_create.html', {
        'form': form,
        'companies_json': json.dumps(companies_data),
        'products_json': json.dumps(products_data),
        'companies_count': companies.count(),
        'products_count': products.count()
    })


# -------------------------------------------------------------------
# SUPER ADMIN GOVERNANCE PANEL VIEWS
# -------------------------------------------------------------------

@login_required
@super_admin_required
def super_admin_dashboard(request):
    users_by_role = User.objects.values('role').annotate(count=Count('id'))
    role_counts = {item['role']: item['count'] for item in users_by_role}

    total_revenue = Order.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    total_ewaste_kg = EWasteSubmission.objects.aggregate(total=Sum('approximate_weight_kg'))['total'] or Decimal('0.00')
    
    # E-Waste stats across platform
    total_submissions_count = EWasteSubmission.objects.count()
    pending_submissions_count = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.SUBMITTED, EWasteSubmission.Status.UNDER_VERIFICATION]
    ).count()
    collected_submissions_count = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.COLLECTED, EWasteSubmission.Status.AT_RECYCLING_CENTER]
    ).count()
    recycled_submissions_count = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.RECYCLING_IN_PROGRESS, EWasteSubmission.Status.RECYCLED, EWasteSubmission.Status.COMPLETED]
    ).count()

    recent_submissions = EWasteSubmission.objects.select_related(
        'user', 'category', 'collector_assignment', 'collector_assignment__collector'
    ).order_by('-created_at')[:8]

    pending_companies = CompanyProfile.objects.filter(verification_status=CompanyProfile.VerificationStatus.PENDING).select_related('user')
    pending_collectors = CollectorProfile.objects.filter(verification_status=CollectorProfile.VerificationStatus.PENDING).select_related('user')
    recent_users = User.objects.order_by('-date_joined')[:6]
    audit_logs = SystemAuditLog.objects.order_by('-created_at')[:8]

    context = {
        'role_counts': role_counts,
        'total_revenue': total_revenue,
        'total_ewaste_kg': total_ewaste_kg,
        'total_submissions_count': total_submissions_count,
        'pending_submissions_count': pending_submissions_count,
        'collected_submissions_count': collected_submissions_count,
        'recycled_submissions_count': recycled_submissions_count,
        'recent_submissions': recent_submissions,
        'pending_companies': pending_companies,
        'pending_collectors': pending_collectors,
        'recent_users': recent_users,
        'audit_logs': audit_logs,
    }
    return render(request, 'super_admin/dashboard.html', context)


@login_required
@super_admin_required
def super_admin_ewaste_view(request):
    status_filter = request.GET.get('status', 'ALL')
    category_id = request.GET.get('category', '')
    query = request.GET.get('q', '')

    submissions = EWasteSubmission.objects.all().select_related(
        'user', 'category', 'collector_assignment', 'collector_assignment__collector'
    ).order_by('-created_at')

    if status_filter != 'ALL' and status_filter:
        submissions = submissions.filter(status=status_filter)
    if category_id:
        submissions = submissions.filter(category_id=category_id)
    if query:
        submissions = submissions.filter(
            Q(tracking_id__icontains=query) |
            Q(waste_name__icontains=query) |
            Q(user__username__icontains=query) |
            Q(user__email__icontains=query) |
            Q(pickup_city__icontains=query)
        )

    categories = EWasteCategory.objects.all()
    statuses = EWasteSubmission.Status.choices

    context = {
        'submissions': submissions,
        'categories': categories,
        'statuses': statuses,
        'selected_status': status_filter,
        'selected_category': category_id,
        'query': query,
        'total_count': submissions.count(),
    }
    return render(request, 'super_admin/all_ewaste.html', context)



@login_required
@super_admin_required
def super_admin_users_view(request):
    users = User.objects.all().order_by('-date_joined')
    role_filter = request.GET.get('role')
    query = request.GET.get('q')

    if role_filter:
        users = users.filter(role=role_filter)
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query))

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')
        target_user = get_object_or_404(User, id=user_id)

        if action == 'TOGGLE_ACTIVE':
            target_user.is_active = not target_user.is_active
            target_user.save()
            messages.success(request, f"User {target_user.username} {'activated' if target_user.is_active else 'deactivated'}.")
        elif action == 'DELETE' and not target_user.is_superuser:
            target_user.delete()
            messages.success(request, f"User {target_user.username} deleted.")
        return redirect('super_admin_users')

    return render(request, 'super_admin/user_management.html', {
        'users': users,
        'roles': User.Role.choices,
        'selected_role': role_filter,
        'query': query
    })


@login_required
@super_admin_required
def super_admin_collectors_view(request):
    status_filter = request.GET.get('status', 'ALL')
    query = request.GET.get('q', '')

    collectors = User.objects.filter(role=User.Role.COLLECTOR).select_related('collector_profile').order_by('-date_joined')

    if status_filter != 'ALL' and status_filter:
        collectors = collectors.filter(collector_profile__verification_status=status_filter)

    if query:
        collectors = collectors.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone__icontains=query) |
            Q(collector_profile__service_area__icontains=query) |
            Q(collector_profile__vehicle_number__icontains=query)
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'UPDATE_STATUS':
            collector_profile_id = request.POST.get('collector_profile_id')
            new_status = request.POST.get('status')
            reason = request.POST.get('rejection_reason', '')

            col_profile = get_object_or_404(CollectorProfile, id=collector_profile_id)
            col_profile.verification_status = new_status
            col_profile.rejection_reason = reason
            if new_status == CollectorProfile.VerificationStatus.VERIFIED:
                col_profile.verified_at = timezone.now()
            col_profile.save()

            send_system_notification(
                user=col_profile.user,
                title=f"Collector Account Verification: {col_profile.get_verification_status_display()}",
                message=f"Your local collector account has been {col_profile.get_verification_status_display().lower()}. {reason}",
                link="/collector/dashboard/",
                notification_type="SUCCESS" if new_status == CollectorProfile.VerificationStatus.VERIFIED else "WARNING"
            )

            messages.success(request, f"Collector '{col_profile.user.username}' status updated to {col_profile.get_verification_status_display()}.")
            return redirect('super_admin_collectors')
        else:
            form = CollectorCreationForm(request.POST)
            if form.is_valid():
                new_collector = form.save()
                messages.success(request, f"Collector '{new_collector.username}' created and verified successfully.")
                return redirect('super_admin_collectors')
            else:
                messages.error(request, "Please correct the errors in the onboarding form.")
    else:
        form = CollectorCreationForm()

    pending_count = CollectorProfile.objects.filter(verification_status=CollectorProfile.VerificationStatus.PENDING).count()
    verified_count = CollectorProfile.objects.filter(verification_status=CollectorProfile.VerificationStatus.VERIFIED).count()
    rejected_count = CollectorProfile.objects.filter(verification_status=CollectorProfile.VerificationStatus.REJECTED).count()

    return render(request, 'super_admin/collector_management.html', {
        'collectors': collectors,
        'form': form,
        'selected_status': status_filter,
        'query': query,
        'pending_count': pending_count,
        'verified_count': verified_count,
        'rejected_count': rejected_count,
        'total_count': collectors.count(),
    })


@login_required
@super_admin_required
def super_admin_companies_view(request):
    companies = CompanyProfile.objects.all().select_related('user').order_by('-created_at')

    if request.method == 'POST':
        company_id = request.POST.get('company_id')
        status = request.POST.get('status')
        reason = request.POST.get('rejection_reason', '')

        company = get_object_or_404(CompanyProfile, id=company_id)
        company.verification_status = status
        company.rejection_reason = reason
        if status == CompanyProfile.VerificationStatus.VERIFIED:
            company.verified_at = timezone.now()
        company.save()

        send_system_notification(
            user=company.user,
            title=f"Corporate Account Verification: {company.get_verification_status_display()}",
            message=f"Your company account has been {company.get_verification_status_display().lower()}. {reason}",
            link="/marketplace/",
            notification_type="SUCCESS" if status == CompanyProfile.VerificationStatus.VERIFIED else "WARNING"
        )

        messages.success(request, f"Company {company.company_name} status updated to {company.get_verification_status_display()}.")
        return redirect('super_admin_companies')

    return render(request, 'super_admin/company_management.html', {'companies': companies})


@login_required
@super_admin_required
def super_admin_categories_view(request):
    categories = EWasteCategory.objects.all()

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f"Category '{cat.name}' created.")
            return redirect('super_admin_categories')
    else:
        form = CategoryForm()

    return render(request, 'super_admin/categories.html', {'categories': categories, 'form': form})
