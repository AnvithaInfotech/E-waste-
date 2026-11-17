from users.models import Notification, EWasteSubmission, CompanyProfile, CollectorProfile
from company.models import Cart

def global_context(request):
    context = {
        'unread_notifications_count': 0,
        'recent_notifications': [],
        'cart_item_count': 0,
        'pending_submissions_count': 0,
        'pending_pickups_count': 0,
        'pending_companies_count': 0,
        'pending_collectors_count': 0,
    }
    
    if request.user.is_authenticated:
        # Notifications
        user_notifications = Notification.objects.filter(user=request.user)
        context['unread_notifications_count'] = user_notifications.filter(is_read=False).count()
        context['recent_notifications'] = user_notifications.order_by('-created_at')[:5]
        
        # Cart for Company
        if request.user.role == 'COMPANY':
            cart, _ = Cart.objects.get_or_create(user=request.user)
            context['cart_item_count'] = cart.total_items
            
        # Collector specific badges
        if request.user.role == 'COLLECTOR':
            context['pending_pickups_count'] = EWasteSubmission.objects.filter(
                collector_assignment__collector=request.user,
                collector_assignment__status__in=['ASSIGNED', 'ACCEPTED', 'ON_THE_WAY']
            ).count()
            
        # Admin / Super Admin badges
        if request.user.role in ['ADMIN', 'SUPER_ADMIN'] or request.user.is_superuser:
            context['pending_submissions_count'] = EWasteSubmission.objects.filter(
                status__in=['SUBMITTED', 'UNDER_VERIFICATION']
            ).count()
            context['pending_companies_count'] = CompanyProfile.objects.filter(
                verification_status='PENDING'
            ).count()
            context['pending_collectors_count'] = CollectorProfile.objects.filter(
                verification_status='PENDING'
            ).count()

    return context
