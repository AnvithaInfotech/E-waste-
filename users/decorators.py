from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from users.models import Notification

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Please log in to access this portal.")
                return redirect(f"{reverse('login')}?next={request.path}")
            
            # Master access for Superuser, Super Admin, and Operational Admin across tabs/portals
            if request.user.is_superuser or request.user.role in ['SUPER_ADMIN', 'ADMIN']:
                return view_func(request, *args, **kwargs)
                
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, f"Access Denied: You do not have permissions for this portal. You are logged in as {request.user.get_role_display()}.")
            return redirect('role_redirect')
        return _wrapped_view
    return decorator


def user_required(view_func):
    return role_required('USER')(view_func)


def collector_required(view_func):
    return role_required('COLLECTOR')(view_func)


def admin_required(view_func):
    return role_required('ADMIN', 'SUPER_ADMIN')(view_func)


def company_required(view_func):
    return role_required('COMPANY')(view_func)


def super_admin_required(view_func):
    return role_required('SUPER_ADMIN')(view_func)


def send_system_notification(user, title, message, link="", notification_type='INFO'):
    """Helper to dispatch in-app notifications to users across the platform."""
    if user:
        return Notification.objects.create(
            user=user,
            title=title,
            message=message,
            link=link,
            notification_type=notification_type
        )
    return None
