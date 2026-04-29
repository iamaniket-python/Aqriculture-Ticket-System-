from user.models import Ticket, TicketComment, StaffProfile


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

    # Pending staff count — sidebar badge ke liye
    pending_staff_count = StaffProfile.objects.filter(is_approved=False).count()

    return {
        'unread_messages':    unread_messages,
        'unread_count':       unread_count,
        'new_tickets':        new_tickets,
        'pending_staff_count': pending_staff_count,
    }