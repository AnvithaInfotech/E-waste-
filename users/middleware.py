from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

User = get_user_model()


class MultiPortalAuthMiddleware:
    """
    Enables independent, concurrent multi-tab sessions across platform portals:
    - /user/ -> Citizen User
    - /collector/ -> Local Collector
    - /admin-panel/ -> Operational Admin
    - /super-admin/ -> Super Admin
    - /company/ -> Corporate Buyer
    - /marketplace/ -> Current portal user or default active session user

    Allows logging out from one tab/portal without terminating other active tabs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        role_sessions = request.session.get('role_sessions', {})

        # 1. Sync standard Django session user into role_sessions if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = request.user.id
            user_role = getattr(request.user, 'role', None)
            if user_role:
                if user_role not in role_sessions:
                    role_sessions[user_role] = user_id
                if getattr(request.user, 'is_superuser', False) or user_role == 'SUPER_ADMIN':
                    role_sessions['SUPER_ADMIN'] = user_id
                    role_sessions['ADMIN'] = user_id
                request.session['role_sessions'] = role_sessions

        # 2. Identify the target portal requirement based on URL path prefix
        target_role = None
        target_user_id = None

        if path.startswith('/admin-panel/'):
            target_role = 'ADMIN'
            target_user_id = role_sessions.get('ADMIN') or role_sessions.get('SUPER_ADMIN')
        elif path.startswith('/super-admin/'):
            target_role = 'SUPER_ADMIN'
            target_user_id = role_sessions.get('SUPER_ADMIN')
        elif path.startswith('/collector/'):
            target_role = 'COLLECTOR'
            target_user_id = role_sessions.get('COLLECTOR')
        elif path.startswith('/user/'):
            target_role = 'USER'
            target_user_id = role_sessions.get('USER')
        elif path.startswith('/company/'):
            if path.startswith('/company/orders/'):
                # Orders can be viewed by COMPANY or citizen USER buyer
                target_role = 'COMPANY' if 'COMPANY' in role_sessions else ('USER' if 'USER' in role_sessions else None)
                target_user_id = role_sessions.get(target_role) if target_role else None
            else:
                target_role = 'COMPANY'
                target_user_id = role_sessions.get('COMPANY')

        # Allow explicit query parameter switch e.g. ?as_role=COLLECTOR
        as_role = request.GET.get('as_role')
        if as_role and as_role in role_sessions:
            target_user_id = role_sessions[as_role]
            target_role = as_role

        # 3. Resolve request.user for this specific portal request
        if target_user_id:
            try:
                portal_user = User.objects.get(id=target_user_id, is_active=True)
                request.user = portal_user
                request.portal_role = target_role or portal_user.role
            except User.DoesNotExist:
                # If user no longer exists, clean up from session
                if target_role and target_role in role_sessions:
                    del role_sessions[target_role]
                    request.session['role_sessions'] = role_sessions
                    request.session.modified = True
        elif target_role:
            # The portal specifically requires a particular role, but this role is not in role_sessions yet
            # If the current default user in standard auth does NOT match the required role:
            if hasattr(request, 'user') and request.user.is_authenticated:
                if request.user.role != target_role and not getattr(request.user, 'is_superuser', False):
                    # Set to AnonymousUser for this portal request so login redirect occurs cleanly for this tab
                    request.user = AnonymousUser()

        response = self.get_response(request)
        return response
