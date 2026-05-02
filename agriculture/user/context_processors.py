from user.models import  TicketComment, StaffProfile,Ticket


def admin_notifications(request):
    """
    Har admin page pe notification data available rahega.
    Base template mein automatically inject hoga.
    """
    # Sirf authenticated admin ke liye
    if not request.user.is_authenticated:
        return {}
    if not request.user.is_superuser:
        return {}
    if request.session.get('role') != 'admin':
        return {}

    unread_messages = TicketComment.objects.filter(
        is_read=False,
        sender__is_staff=False,
        sender__is_superuser=False
    ).select_related('ticket', 'ticket__user', 'sender').order_by('-created_at')[:5]

    unread_count = TicketComment.objects.filter(
        is_read=False,
        sender__is_staff=False,
        sender__is_superuser=False
    ).count()

    new_tickets = Ticket.objects.filter(
        status='pending'
    ).select_related('user').order_by('-created_at')[:5]

    
    pending_staff_count = StaffProfile.objects.filter(is_approved=False).count()

    return {
        'unread_messages':    unread_messages,
        'unread_count':       unread_count,
        'new_tickets':        new_tickets,
        'pending_staff_count': pending_staff_count,
    }
# -----------------------------------------------------------
# for staff
def staff_notifications(request):
    if not request.user.is_authenticated:
        return {}

    if not request.user.is_staff:
        return {}

    # 🔔 Assigned tickets
    assigned_tickets = Ticket.objects.filter(
        assigned_to=request.user,
        status='pending'
    ).order_by('-created_at')[:5]

    # 💬 Recent messages (TicketComment use karo)
    recent_messages = TicketComment.objects.filter(
        ticket__assigned_to=request.user
    ).select_related('ticket', 'ticket__user').order_by('-created_at')[:5]

    # 🔢 Unread messages
    unread_messages_count = TicketComment.objects.filter(
        ticket__assigned_to=request.user,
        is_read=False
    ).count()

    return {
        'assigned_tickets': assigned_tickets,
        'assigned_count': assigned_tickets.count(),
        'recent_messages': recent_messages,
        'unread_messages_count': unread_messages_count,
    }