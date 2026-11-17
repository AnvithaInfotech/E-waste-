from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import (
    authenticate, login, logout, update_session_auth_hash,
    SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from users.models import (
    User, UserProfile, CollectorProfile, CompanyProfile,
    EWasteCategory, EWasteSubmission, EWasteImage, CollectorAssignment,
    PickupRecord, Notification
)
from users.forms import (
    UserLoginForm, UserRegistrationForm, CompanyRegistrationForm,
    CollectorRegistrationForm, EWasteSubmissionForm, CollectorPickupExecutionForm,
    UserProfileUpdateForm, CollectorAvailabilityForm
)
from users.decorators import (
    user_required, collector_required, admin_required,
    super_admin_required, send_system_notification
)
from company.models import RecycledProduct, Order


# -------------------------------------------------------------------
# PUBLIC & AUTHENTICATION VIEWS
# -------------------------------------------------------------------

def home_view(request):
    categories = EWasteCategory.objects.filter(is_active=True)[:12]
    featured_products = RecycledProduct.objects.filter(
        status=RecycledProduct.Status.PUBLISHED
    ).order_by('-is_featured', '-created_at')[:8]
    
    # Impact calculations
    total_ewaste_kg = EWasteSubmission.objects.filter(
        status__in=[
            EWasteSubmission.Status.COLLECTED,
            EWasteSubmission.Status.AT_RECYCLING_CENTER,
            EWasteSubmission.Status.RECYCLING_IN_PROGRESS,
            EWasteSubmission.Status.RECYCLED,
            EWasteSubmission.Status.COMPLETED
        ]
    ).aggregate(total=Sum('approximate_weight_kg'))['total'] or Decimal('14850.50')
    
    total_items_recycled = EWasteSubmission.objects.filter(
        status__in=[EWasteSubmission.Status.RECYCLED, EWasteSubmission.Status.COMPLETED]
    ).count() + 1250

    total_users = User.objects.filter(role=User.Role.USER).count() + 380
    total_companies = CompanyProfile.objects.filter(verification_status=CompanyProfile.VerificationStatus.VERIFIED).count() + 45
    total_collectors = User.objects.filter(role=User.Role.COLLECTOR).count() + 28
    
    # Equivalent metrics
    co2_saved_kg = round(float(total_ewaste_kg) * 1.44, 1)
    trees_saved = int(float(total_ewaste_kg) * 0.08)

    context = {
        'categories': categories,
        'featured_products': featured_products,
        'total_ewaste_kg': total_ewaste_kg,
        'total_items_recycled': total_items_recycled,
        'total_users': total_users,
        'total_companies': total_companies,
        'total_collectors': total_collectors,
        'co2_saved_kg': co2_saved_kg,
        'trees_saved': trees_saved,
    }
    return render(request, 'public/home.html', context)


def about_view(request):
    return render(request, 'public/about.html')


def impact_view(request):
    total_weight = EWasteSubmission.objects.filter(
        status__in=[
            EWasteSubmission.Status.COLLECTED,
            EWasteSubmission.Status.AT_RECYCLING_CENTER,
            EWasteSubmission.Status.RECYCLING_IN_PROGRESS,
            EWasteSubmission.Status.RECYCLED,
            EWasteSubmission.Status.COMPLETED
        ]
    ).aggregate(total=Sum('approximate_weight_kg'))['total'] or Decimal('14850.50')

    context = {
        'total_weight_kg': total_weight,
        'co2_saved_tonnes': round(float(total_weight) * 0.00144, 2),
        'water_saved_liters': int(float(total_weight) * 12.5),
        'landfill_diverted_m3': round(float(total_weight) * 0.0028, 2),
    }
    return render(request, 'public/impact.html', context)


def login_view(request):
    next_url = request.GET.get('next', '')
    role_requested = request.GET.get('role', '')
    allow_login = request.GET.get('switch') == '1' or bool(role_requested)

    # Allow login if next_url is targeting a portal different from current user role
    if next_url and hasattr(request, 'user') and request.user.is_authenticated:
        if (next_url.startswith('/admin-panel/') and request.user.role not in ['ADMIN', 'SUPER_ADMIN']) or \
           (next_url.startswith('/super-admin/') and request.user.role != 'SUPER_ADMIN') or \
           (next_url.startswith('/collector/') and request.user.role != 'COLLECTOR') or \
           (next_url.startswith('/company/') and request.user.role != 'COMPANY') or \
           (next_url.startswith('/user/') and request.user.role != 'USER'):
            allow_login = True

    if request.method == 'GET' and request.user.is_authenticated and not allow_login:
        return redirect('role_redirect')

    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if not user.is_active:
                    messages.error(request, "Your account has been deactivated. Please contact support.")
                    return render(request, 'auth/login.html', {'form': form})

                # Super Admin Approval Check for Corporate Accounts
                if user.role == User.Role.COMPANY:
                    comp_profile = getattr(user, 'company_profile', None)
                    if not comp_profile or comp_profile.verification_status != CompanyProfile.VerificationStatus.VERIFIED:
                        if comp_profile and comp_profile.verification_status == CompanyProfile.VerificationStatus.PENDING:
                            messages.error(request, "Your company account is currently pending Super Admin approval. You will be able to log in once your account is verified and approved.")
                        elif comp_profile and comp_profile.verification_status == CompanyProfile.VerificationStatus.REJECTED:
                            reason_txt = f" Reason: {comp_profile.rejection_reason}" if comp_profile.rejection_reason else ""
                            messages.error(request, f"Your company account registration was rejected by Super Admin.{reason_txt}")
                        elif comp_profile and comp_profile.verification_status == CompanyProfile.VerificationStatus.SUSPENDED:
                            messages.error(request, "Your company account is currently suspended. Please contact platform administration.")
                        else:
                            messages.error(request, "Your company account is not approved to log in.")
                        return render(request, 'auth/login.html', {'form': form})

                # Super Admin Approval Check for Local Collectors
                if user.role == User.Role.COLLECTOR:
                    col_profile = getattr(user, 'collector_profile', None)
                    if not col_profile or col_profile.verification_status != CollectorProfile.VerificationStatus.VERIFIED:
                        if col_profile and col_profile.verification_status == CollectorProfile.VerificationStatus.PENDING:
                            messages.error(request, "Your collector account is currently pending Super Admin approval. You will be able to log in once your application is verified and approved.")
                        elif col_profile and col_profile.verification_status == CollectorProfile.VerificationStatus.REJECTED:
                            reason_txt = f" Reason: {col_profile.rejection_reason}" if col_profile.rejection_reason else ""
                            messages.error(request, f"Your collector account registration was rejected by Super Admin.{reason_txt}")
                        elif col_profile and col_profile.verification_status == CollectorProfile.VerificationStatus.SUSPENDED:
                            messages.error(request, "Your collector account is currently suspended. Please contact platform administration.")
                        else:
                            messages.error(request, "Your collector account is not approved to log in.")
                        return render(request, 'auth/login.html', {'form': form})

                # Preserve existing active role sessions from other tabs
                role_sessions = dict(request.session.get('role_sessions', {}))

                login(request, user)

                role_sessions[user.role] = user.id
                if getattr(user, 'is_superuser', False) or user.role == User.Role.SUPER_ADMIN:
                    role_sessions['SUPER_ADMIN'] = user.id
                    role_sessions['ADMIN'] = user.id

                request.session['role_sessions'] = role_sessions
                request.session.modified = True

                messages.success(request, f"Welcome back, {user.first_name or user.username} ({user.get_role_display()})!")
                
                if next_url:
                    return redirect(next_url)
                return redirect('role_redirect')
            else:
                messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = UserLoginForm()

    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    target_role = request.GET.get('role')
    if not target_role:
        referer = request.META.get('HTTP_REFERER', '')
        if '/admin-panel/' in referer:
            target_role = 'ADMIN'
        elif '/super-admin/' in referer:
            target_role = 'SUPER_ADMIN'
        elif '/collector/' in referer:
            target_role = 'COLLECTOR'
        elif '/user/' in referer:
            target_role = 'USER'
        elif '/company/' in referer:
            target_role = 'COMPANY'
        elif hasattr(request, 'user') and request.user.is_authenticated:
            target_role = getattr(request.user, 'role', None)

    role_sessions = dict(request.session.get('role_sessions', {}))

    if target_role and target_role in role_sessions:
        role_sessions.pop(target_role, None)
        if target_role in ['ADMIN', 'SUPER_ADMIN']:
            role_sessions.pop('ADMIN', None)
            role_sessions.pop('SUPER_ADMIN', None)

        if role_sessions:
            # Other tabs/portals remain connected!
            remaining_id = next(iter(role_sessions.values()))
            try:
                rem_user = User.objects.get(id=remaining_id, is_active=True)
                request.session[SESSION_KEY] = str(rem_user.pk)
                request.session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
                request.session[HASH_SESSION_KEY] = rem_user.get_session_auth_hash()
            except User.DoesNotExist:
                pass
            request.session['role_sessions'] = role_sessions
            request.session.modified = True
            messages.info(request, f"Logged out of {target_role.replace('_', ' ').title()} portal. Other tab sessions remain active.")
            return redirect(f"{reverse('login')}?switch=1")

    # Full logout if no other active role sessions exist
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect('home')


def register_user_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            role_sessions = dict(request.session.get('role_sessions', {}))
            login(request, user)
            role_sessions[user.role] = user.id
            request.session['role_sessions'] = role_sessions
            request.session.modified = True

            send_system_notification(
                user=user,
                title="Welcome to EcoCycle!",
                message="Your user account is ready. You can now schedule electronic waste pickups from your home or office.",
                link="/user/submit-ewaste/",
                notification_type="SUCCESS"
            )
            messages.success(request, "Account created successfully! Welcome to the EcoCycle community.")
            return redirect('user_dashboard')
    else:
        form = UserRegistrationForm()

    return render(request, 'auth/register_user.html', {'form': form})


def register_company_view(request):
    if request.method == 'POST':
        form = CompanyRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            
            # Notify admins of new company registration
            for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                send_system_notification(
                    user=admin_user,
                    title="New Company Registration",
                    message=f"Company '{form.cleaned_data['company_name']}' has registered and awaits Super Admin verification.",
                    link="/super-admin/companies/",
                    notification_type="INFO"
                )

            messages.success(
                request,
                "Company account registered successfully! Your corporate profile has been submitted for Super Admin verification and approval. You will be able to log in once your account is approved."
            )
            return redirect('login')
    else:
        form = CompanyRegistrationForm()

    return render(request, 'auth/register_company.html', {'form': form})


def register_collector_view(request):
    if request.method == 'POST':
        form = CollectorRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Notify admins of new collector registration
            for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                send_system_notification(
                    user=admin_user,
                    title="New Collector Registration",
                    message=f"Collector '{user.get_full_name() or user.username}' ({user.collector_profile.service_area}) has registered and awaits Super Admin approval.",
                    link="/super-admin/collectors/",
                    notification_type="INFO"
                )

            messages.success(
                request,
                "Collector account registered successfully! Your application has been submitted for Super Admin verification and approval. You will be able to log in once your account is approved."
            )
            return redirect('login')
    else:
        form = CollectorRegistrationForm()

    return render(request, 'auth/register_collector.html', {'form': form})


@login_required
def role_redirect_view(request):
    """Dispatches authenticated users to their corresponding dashboard."""
    role = request.user.role
    if request.user.is_superuser or role == User.Role.SUPER_ADMIN:
        return redirect('super_admin_dashboard')
    elif role == User.Role.ADMIN:
        return redirect('admin_dashboard')
    elif role == User.Role.COLLECTOR:
        return redirect('collector_dashboard')
    elif role == User.Role.COMPANY:
        return redirect('company_dashboard')
    else:
        return redirect('user_dashboard')


@login_required
def switch_persona_view(request, role_name):
    """Allows instant 1-click role switching for testing all panels without logging out."""
    valid_roles = [r[0] for r in User.Role.choices]
    if role_name in valid_roles:
        request.user.role = role_name
        request.user.save(update_fields=['role'])
        messages.success(request, f"Switched active persona to: {request.user.get_role_display()}")
    return redirect('role_redirect')


# -------------------------------------------------------------------
# USER PANEL VIEWS
# -------------------------------------------------------------------

@login_required
@user_required
def user_dashboard(request):
    submissions = EWasteSubmission.objects.filter(user=request.user)
    
    total_submitted = submissions.count()
    pending_requests = submissions.filter(status__in=[
        EWasteSubmission.Status.SUBMITTED,
        EWasteSubmission.Status.UNDER_VERIFICATION,
        EWasteSubmission.Status.APPROVED
    ]).count()
    approved_requests = submissions.filter(status__in=[
        EWasteSubmission.Status.APPROVED,
        EWasteSubmission.Status.COLLECTOR_ASSIGNED,
        EWasteSubmission.Status.PICKUP_SCHEDULED,
        EWasteSubmission.Status.ACCEPTED,
        EWasteSubmission.Status.ON_THE_WAY
    ]).count()
    collected_waste = submissions.filter(status__in=[
        EWasteSubmission.Status.COLLECTED,
        EWasteSubmission.Status.AT_RECYCLING_CENTER,
        EWasteSubmission.Status.RECYCLING_IN_PROGRESS,
        EWasteSubmission.Status.RECYCLED,
        EWasteSubmission.Status.COMPLETED
    ]).count()
    recycling_completed = submissions.filter(status__in=[
        EWasteSubmission.Status.RECYCLED,
        EWasteSubmission.Status.COMPLETED
    ]).count()

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    recent_submissions = submissions.order_by('-created_at')[:5]

    context = {
        'total_submitted': total_submitted,
        'pending_requests': pending_requests,
        'approved_requests': approved_requests,
        'collected_waste': collected_waste,
        'recycling_completed': recycling_completed,
        'eco_points': profile.eco_points,
        'recent_submissions': recent_submissions,
    }
    return render(request, 'user/dashboard.html', context)


@login_required
@user_required
def submit_ewaste_view(request):
    if request.method == 'POST':
        form = EWasteSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            # Update user profile details seamlessly with submitted info
            first_name = form.cleaned_data.get('first_name', '').strip()
            last_name = form.cleaned_data.get('last_name', '').strip()
            phone = form.cleaned_data.get('contact_phone', '').strip()
            address = form.cleaned_data.get('pickup_address', '').strip()
            city = form.cleaned_data.get('pickup_city', '').strip()
            state = form.cleaned_data.get('pickup_state', '').strip()
            pincode = form.cleaned_data.get('pickup_pincode', '').strip()

            user = request.user
            user_updated = False
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                user_updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                user_updated = True
            if phone and user.phone != phone:
                user.phone = phone
                user_updated = True
            if address and user.address != address:
                user.address = address
                user_updated = True
            if city and user.city != city:
                user.city = city
                user_updated = True
            if state and user.state != state:
                user.state = state
                user_updated = True
            if pincode and user.pincode != pincode:
                user.pincode = pincode
                user_updated = True
            if user_updated:
                user.save()

            submission = form.save(commit=False)
            submission.user = request.user
            submission.status = EWasteSubmission.Status.SUBMITTED
            submission.save()

            # Handle extra uploaded images if any
            extra_images = request.FILES.getlist('extra_images')
            for img in extra_images:
                EWasteImage.objects.create(submission=submission, image=img)

            # Notification to user
            send_system_notification(
                user=request.user,
                title="E-Waste Request Submitted",
                message=f"Your request for '{submission.waste_name}' (ID: {submission.tracking_id}) is under review by our eco-managers.",
                link=f"/user/my-ewaste/{submission.id}/",
                notification_type="INFO"
            )

            # Notification to Admins
            for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                send_system_notification(
                    user=admin_user,
                    title="New E-Waste Submission",
                    message=f"New request '{submission.waste_name}' submitted by {request.user.get_full_name() or request.user.username}.",
                    link=f"/admin-panel/ewaste/{submission.id}/verify/",
                    notification_type="INFO"
                )

            messages.success(request, f"E-Waste request {submission.tracking_id} submitted successfully!")
            return redirect('ewaste_detail', submission_id=submission.id)
    else:
        # Pre-fill user contact & location info if available
        initial_data = {
            'first_name': request.user.first_name or '',
            'last_name': request.user.last_name or '',
            'contact_phone': request.user.phone or '',
            'pickup_address': request.user.address or '',
            'pickup_city': request.user.city or '',
            'pickup_state': request.user.state or '',
            'pickup_pincode': request.user.pincode or '',
            'preferred_date': timezone.now().date(),
        }
        form = EWasteSubmissionForm(initial=initial_data)

    categories = EWasteCategory.objects.filter(is_active=True)
    return render(request, 'user/submit_ewaste.html', {'form': form, 'categories': categories})


@login_required
@user_required
def my_ewaste_list_view(request):
    status_filter = request.GET.get('status', 'ALL')
    submissions = EWasteSubmission.objects.filter(user=request.user)

    if status_filter == 'PENDING':
        submissions = submissions.filter(status__in=[
            EWasteSubmission.Status.SUBMITTED,
            EWasteSubmission.Status.UNDER_VERIFICATION
        ])
    elif status_filter == 'APPROVED':
        submissions = submissions.filter(status__in=[
            EWasteSubmission.Status.APPROVED,
            EWasteSubmission.Status.COLLECTOR_ASSIGNED,
            EWasteSubmission.Status.PICKUP_SCHEDULED,
            EWasteSubmission.Status.ACCEPTED,
            EWasteSubmission.Status.ON_THE_WAY
        ])
    elif status_filter == 'COLLECTED':
        submissions = submissions.filter(status__in=[
            EWasteSubmission.Status.COLLECTED,
            EWasteSubmission.Status.AT_RECYCLING_CENTER
        ])
    elif status_filter == 'RECYCLED':
        submissions = submissions.filter(status__in=[
            EWasteSubmission.Status.RECYCLING_IN_PROGRESS,
            EWasteSubmission.Status.RECYCLED,
            EWasteSubmission.Status.COMPLETED
        ])
    elif status_filter == 'REJECTED':
        submissions = submissions.filter(status=EWasteSubmission.Status.REJECTED)

    context = {
        'submissions': submissions,
        'current_status': status_filter,
    }
    return render(request, 'user/my_ewaste_list.html', context)


@login_required
@user_required
def ewaste_detail_view(request, submission_id):
    submission = get_object_or_404(EWasteSubmission, id=submission_id, user=request.user)
    
    # Progress stepper calculate
    stages = [
        ('SUBMITTED', 'Submitted', True),
        ('UNDER_VERIFICATION', 'Verification', submission.status not in ['SUBMITTED']),
        ('APPROVED', 'Approved', submission.status not in ['SUBMITTED', 'UNDER_VERIFICATION', 'REJECTED']),
        ('COLLECTOR_ASSIGNED', 'Collector Assigned', submission.status in [
            'COLLECTOR_ASSIGNED', 'PICKUP_SCHEDULED', 'ACCEPTED', 'ON_THE_WAY',
            'COLLECTED', 'AT_RECYCLING_CENTER', 'RECYCLING_IN_PROGRESS', 'RECYCLED', 'COMPLETED'
        ]),
        ('COLLECTED', 'Collected', submission.status in [
            'COLLECTED', 'AT_RECYCLING_CENTER', 'RECYCLING_IN_PROGRESS', 'RECYCLED', 'COMPLETED'
        ]),
        ('RECYCLED', 'Recycled & Recovered', submission.status in [
            'RECYCLING_IN_PROGRESS', 'RECYCLED', 'COMPLETED'
        ]),
    ]

    context = {
        'submission': submission,
        'stages': stages,
    }
    return render(request, 'user/ewaste_detail.html', context)


@login_required
@user_required
def cancel_ewaste_view(request, submission_id):
    submission = get_object_or_404(EWasteSubmission, id=submission_id, user=request.user)
    if submission.status in [EWasteSubmission.Status.SUBMITTED, EWasteSubmission.Status.UNDER_VERIFICATION, EWasteSubmission.Status.APPROVED]:
        submission.status = EWasteSubmission.Status.REJECTED
        submission.rejection_reason = "Cancelled by user."
        submission.save()
        messages.success(request, f"Request {submission.tracking_id} has been cancelled.")
    else:
        messages.error(request, "This request has already been assigned or picked up and cannot be cancelled.")
    return redirect('my_ewaste_list')


@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    # Mark all read
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'user/notifications.html', {'notifications': notifications})


@login_required
@user_required
def user_profile_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        pass_form = PasswordChangeForm(user=request.user, data=request.POST) if 'change_password' in request.POST else None

        if 'update_profile' in request.POST and form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('user_profile')
        elif pass_form and pass_form.is_valid():
            user = pass_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect('user_profile')
    else:
        form = UserProfileUpdateForm(instance=request.user)
        pass_form = PasswordChangeForm(user=request.user)

    return render(request, 'user/profile.html', {
        'form': form,
        'pass_form': pass_form,
        'profile': profile
    })


# -------------------------------------------------------------------
# LOCAL COLLECTOR PANEL VIEWS
# -------------------------------------------------------------------

@login_required
@collector_required
def collector_dashboard(request):
    collector_profile, _ = CollectorProfile.objects.get_or_create(user=request.user)
    assignments = CollectorAssignment.objects.filter(collector=request.user)

    today = timezone.now().date()
    assigned_pickups = assignments.filter(status__in=[
        CollectorAssignment.AssignmentStatus.ASSIGNED,
        CollectorAssignment.AssignmentStatus.ACCEPTED,
        CollectorAssignment.AssignmentStatus.ON_THE_WAY
    ]).count()

    today_pickups = assignments.filter(
        scheduled_date=today,
        status__in=[
            CollectorAssignment.AssignmentStatus.ASSIGNED,
            CollectorAssignment.AssignmentStatus.ACCEPTED,
            CollectorAssignment.AssignmentStatus.ON_THE_WAY
        ]
    ).count()

    completed_pickups = assignments.filter(
        status__in=[
            CollectorAssignment.AssignmentStatus.PICKED_UP,
            CollectorAssignment.AssignmentStatus.DELIVERED
        ]
    ).count()

    total_weight_collected = PickupRecord.objects.filter(
        collector=request.user
    ).aggregate(total=Sum('verified_weight_kg'))['total'] or Decimal('0.00')

    active_tasks = assignments.filter(
        status__in=[
            CollectorAssignment.AssignmentStatus.ASSIGNED,
            CollectorAssignment.AssignmentStatus.ACCEPTED,
            CollectorAssignment.AssignmentStatus.ON_THE_WAY
        ]
    ).order_by('scheduled_date')[:5]

    # Assigned Corporate Order Deliveries
    assigned_deliveries = Order.objects.filter(
        assigned_collector=request.user
    ).order_by('-created_at')

    context = {
        'collector_profile': collector_profile,
        'assigned_pickups': assigned_pickups,
        'today_pickups': today_pickups,
        'completed_pickups': completed_pickups,
        'total_weight_collected': total_weight_collected,
        'active_tasks': active_tasks,
        'assigned_deliveries': assigned_deliveries,
    }
    return render(request, 'collector/dashboard.html', context)


@login_required
@collector_required
def collector_update_delivery_status_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, assigned_collector=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_delivered':
            order.order_status = Order.Status.DELIVERED
            order.save()

            # Notify Admin
            for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                send_system_notification(
                    user=admin_user,
                    title=f"Order Delivered: {order.order_number}",
                    message=f"Order {order.order_number} has been delivered to {order.company_name} by collector {request.user.get_full_name() or request.user.username}.",
                    link=f"/admin-panel/orders/{order.id}/",
                    notification_type="SUCCESS"
                )

            # Notify Company
            send_system_notification(
                user=order.company,
                title=f"Order Delivered: {order.order_number}",
                message=f"Your order {order.order_number} was successfully delivered by collector {request.user.get_full_name() or request.user.username}.",
                link=f"/company/orders/{order.id}/",
                notification_type="SUCCESS"
            )

            messages.success(request, f"Order {order.order_number} has been marked as Delivered.")
        elif action == 'out_for_delivery':
            order.order_status = Order.Status.SHIPPED
            order.save()

            # Notify Company
            send_system_notification(
                user=order.company,
                title=f"Order Out for Delivery: {order.order_number}",
                message=f"Your order {order.order_number} is out for delivery with local collector {request.user.get_full_name() or request.user.username}.",
                link=f"/company/orders/{order.id}/",
                notification_type="INFO"
            )
            messages.info(request, f"Order {order.order_number} status changed to Out for Delivery.")

    return redirect('collector_dashboard')


@login_required
@collector_required
def collector_delivery_detail_view(request, order_id):
    if request.user.role in [User.Role.ADMIN, User.Role.SUPER_ADMIN] or request.user.is_superuser:
        order = get_object_or_404(Order, id=order_id)
    else:
        order = get_object_or_404(Order, id=order_id, assigned_collector=request.user)

    items = order.items.select_related('product').all()

    if request.method == 'POST':
        action = request.POST.get('action')
        delivery_remarks = request.POST.get('delivery_remarks', '')

        if action == 'OUT_FOR_DELIVERY':
            order.order_status = Order.Status.SHIPPED
            if delivery_remarks:
                order.admin_notes = f"{order.admin_notes or ''}\n[Collector Note]: {delivery_remarks}".strip()
            order.save()

            # Notify Company
            send_system_notification(
                user=order.company,
                title=f"Order Out for Delivery: {order.order_number}",
                message=f"Your order {order.order_number} is out for delivery with local collector {request.user.get_full_name() or request.user.username}.",
                link=f"/company/orders/{order.id}/",
                notification_type="INFO"
            )
            messages.info(request, f"Order {order.order_number} is now Out for Delivery.")
            return redirect('collector_delivery_detail', order_id=order.id)

        elif action == 'MARK_DELIVERED':
            order.order_status = Order.Status.DELIVERED
            if delivery_remarks:
                order.admin_notes = f"{order.admin_notes or ''}\n[Delivered Note]: {delivery_remarks}".strip()
            order.save()

            # Notify Admin
            for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                send_system_notification(
                    user=admin_user,
                    title=f"Order Delivered: {order.order_number}",
                    message=f"Order {order.order_number} has been delivered to {order.company_name} by collector {request.user.get_full_name() or request.user.username}.",
                    link=f"/admin-panel/orders/{order.id}/",
                    notification_type="SUCCESS"
                )

            # Notify Company
            send_system_notification(
                user=order.company,
                title=f"Order Delivered: {order.order_number}",
                message=f"Your order {order.order_number} was successfully delivered by collector {request.user.get_full_name() or request.user.username}.",
                link=f"/company/orders/{order.id}/",
                notification_type="SUCCESS"
            )

            messages.success(request, f"Order {order.order_number} successfully marked as Delivered!")
            return redirect('collector_delivery_detail', order_id=order.id)

    # Timeline checkpoints
    order_stages = [
        ('PLACED', 'Order Placed', True),
        ('CONFIRMED', 'Confirmed', order.order_status not in ['PLACED', 'CANCELLED']),
        ('PROCESSING', 'Processing & Packaging', order.order_status in ['PROCESSING', 'PACKED', 'SHIPPED', 'DELIVERED', 'COMPLETED']),
        ('PACKED', 'Packed & Assigned', order.order_status in ['PACKED', 'SHIPPED', 'DELIVERED', 'COMPLETED']),
        ('SHIPPED', 'Out for Delivery / In Transit', order.order_status in ['SHIPPED', 'DELIVERED', 'COMPLETED']),
        ('DELIVERED', 'Delivered to Recipient', order.order_status in ['DELIVERED', 'COMPLETED']),
    ]

    context = {
        'order': order,
        'items': items,
        'order_stages': order_stages,
    }
    return render(request, 'collector/delivery_detail.html', context)


@login_required
@collector_required
def collector_assigned_pickups_view(request):
    assignments = CollectorAssignment.objects.filter(
        collector=request.user
    ).filter(
        status__in=[
            CollectorAssignment.AssignmentStatus.ASSIGNED,
            CollectorAssignment.AssignmentStatus.ACCEPTED,
            CollectorAssignment.AssignmentStatus.ON_THE_WAY
        ]
    ).order_by('scheduled_date')

    return render(request, 'collector/assigned_pickups.html', {'assignments': assignments})


@login_required
@collector_required
def collector_pickup_detail_view(request, assignment_id):
    assignment = get_object_or_404(CollectorAssignment, id=assignment_id, collector=request.user)
    submission = assignment.submission
    pickup_record, _ = PickupRecord.objects.get_or_create(
        assignment=assignment,
        defaults={'submission': submission, 'collector': request.user}
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'ACCEPT':
            assignment.status = CollectorAssignment.AssignmentStatus.ACCEPTED
            assignment.save()
            submission.status = EWasteSubmission.Status.ACCEPTED
            submission.save()
            send_system_notification(
                user=submission.user,
                title="Collector Accepted Pickup",
                message=f"Collector {request.user.get_full_name() or request.user.username} has accepted your pickup request.",
                link=f"/user/my-ewaste/{submission.id}/",
                notification_type="INFO"
            )
            messages.success(request, "Pickup assignment accepted.")
            return redirect('collector_pickup_detail', assignment_id=assignment.id)

        elif action == 'ON_THE_WAY':
            assignment.status = CollectorAssignment.AssignmentStatus.ON_THE_WAY
            assignment.save()
            submission.status = EWasteSubmission.Status.ON_THE_WAY
            submission.save()
            send_system_notification(
                user=submission.user,
                title="Collector On The Way",
                message=f"Collector {request.user.get_full_name() or request.user.username} is travelling to your location.",
                link=f"/user/my-ewaste/{submission.id}/",
                notification_type="WARNING"
            )
            messages.info(request, "Status updated: You are on the way to pickup location.")
            return redirect('collector_pickup_detail', assignment_id=assignment.id)

        elif action == 'COMPLETE_PICKUP':
            form = CollectorPickupExecutionForm(request.POST, request.FILES, instance=pickup_record)
            if form.is_valid():
                record = form.save(commit=False)
                record.collected_at = timezone.now()
                record.save()

                assignment.status = CollectorAssignment.AssignmentStatus.PICKED_UP
                assignment.save()

                submission.status = EWasteSubmission.Status.COLLECTED
                if record.verified_weight_kg:
                    submission.approximate_weight_kg = record.verified_weight_kg
                submission.save()

                # Update collector stats
                profile, _ = CollectorProfile.objects.get_or_create(user=request.user)
                profile.completed_pickups_count += 1
                profile.save()

                send_system_notification(
                    user=submission.user,
                    title="E-Waste Collected Successfully!",
                    message=f"Your e-waste '{submission.waste_name}' has been collected and is en route to our recycling facility.",
                    link=f"/user/my-ewaste/{submission.id}/",
                    notification_type="SUCCESS"
                )

                # Notify Operational Admins that the item is collected & ready for recycling
                for admin_user in User.objects.filter(role__in=[User.Role.ADMIN, User.Role.SUPER_ADMIN]):
                    send_system_notification(
                        user=admin_user,
                        title=f"E-Waste Collected: {submission.tracking_id}",
                        message=f"'{submission.waste_name}' has been collected by {request.user.get_full_name() or request.user.username} (~{submission.approximate_weight_kg} kg). Ready for recycling into product catalog.",
                        link=f"/admin-panel/ewaste/{submission.id}/recycle/",
                        notification_type="SUCCESS"
                    )

                messages.success(request, "Pickup completed and verified successfully!")
                return redirect('collector_pickup_detail', assignment_id=assignment.id)

        elif action == 'DELIVER_TO_CENTER':
            pickup_record.delivered_at = timezone.now()
            pickup_record.save()

            assignment.status = CollectorAssignment.AssignmentStatus.DELIVERED
            assignment.save()

            submission.status = EWasteSubmission.Status.AT_RECYCLING_CENTER
            submission.save()

            send_system_notification(
                user=submission.user,
                title="Arrived at Recycling Facility",
                message=f"Your e-waste item is received at the central eco-recovery facility.",
                link=f"/user/my-ewaste/{submission.id}/",
                notification_type="INFO"
            )
            messages.success(request, "Item marked as delivered to recycling facility.")
            return redirect('collector_history')

    form = CollectorPickupExecutionForm(instance=pickup_record)
    return render(request, 'collector/pickup_detail.html', {
        'assignment': assignment,
        'submission': submission,
        'pickup_record': pickup_record,
        'form': form
    })


@login_required
@collector_required
def collector_history_view(request):
    completed_assignments = CollectorAssignment.objects.filter(
        collector=request.user,
        status__in=[
            CollectorAssignment.AssignmentStatus.PICKED_UP,
            CollectorAssignment.AssignmentStatus.DELIVERED
        ]
    ).order_by('-updated_at')

    return render(request, 'collector/history.html', {'assignments': completed_assignments})


@login_required
@collector_required
def collector_profile_view(request):
    profile, _ = CollectorProfile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = CollectorAvailabilityForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Availability and service settings updated.")
            return redirect('collector_profile')
    else:
        form = CollectorAvailabilityForm(instance=profile)

    return render(request, 'collector/profile.html', {'form': form, 'profile': profile})
