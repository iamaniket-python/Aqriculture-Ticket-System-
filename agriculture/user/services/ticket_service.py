from django.contrib.auth.models import User
from django.db.models import Count, Q, QuerySet
from user.models import Ticket, TicketComment, TicketImage, Purchase


class TicketService:
    """
    Ticket se related sab business logic yahan — views mein sirf
    request/response handling hogi, logic nahi.
    """

    @staticmethod
    def get_user_tickets(user, product="", date_from="", date_to=""):
        qs = Ticket.objects.filter(user=user)\
        .select_related('purchase', 'assigned_to')\
        .prefetch_related('images')

        if product:
         qs = qs.filter(purchase__product_name__icontains=product)
        if date_from:
         qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
         qs = qs.filter(created_at__date__lte=date_to)

        return qs.order_by('-created_at') 

    @staticmethod
    def create_ticket(user: User, data: dict, images: list, document=None) -> Ticket:
        purchase = Purchase.objects.get(
            user=user,
            purchase_id=data.get('purchase'),
            product_name=data['product']
        )
        ticket = Ticket.objects.create(
            user=user,
            purchase=purchase,
            title=data['title'],
            description=data['description'],
            category=data['category'],
            other=data.get('other', ''),
            document=document,
        )
        TicketImage.objects.bulk_create([
            TicketImage(ticket=ticket, image=img) for img in images
        ])
        return ticket

    @staticmethod
    def add_comment(ticket: Ticket, sender: User, message: str) -> TicketComment:
        return TicketComment.objects.create(
            ticket=ticket,
            sender=sender,
            message=message,
            is_read=False,
        )

    @staticmethod
    def mark_comments_read(ticket: Ticket, exclude_staff: bool = True) -> None:
        qs = TicketComment.objects.filter(ticket=ticket, is_read=False)
        if exclude_staff:
            qs = qs.filter(sender__is_staff=False, sender__is_superuser=False)
        qs.update(is_read=True)

    @staticmethod
    def get_dashboard_stats(user_filter: str = None) -> dict:
        """Admin dashboard ke liye — ek hi query mein sab stats."""
        qs = Ticket.objects.all()
        if user_filter:
            qs = qs.filter(user_id=user_filter)

        return qs.aggregate(
            total      = Count('id'),
            pending    = Count('id', filter=Q(status='pending')),
            resolved   = Count('id', filter=Q(status='resolved')),
            in_progress= Count('id', filter=Q(status='in_progress')),
        )

    @staticmethod
    def assign_to_staff(ticket: Ticket, staff: User) -> None:
        ticket.assigned_to = staff
        ticket.status = 'in_progress'
        ticket.save(update_fields=['assigned_to', 'status'])

    @staticmethod
    def update_status(ticket: Ticket, status: str) -> bool:
        if status not in ('pending', 'in_progress', 'resolved'):
            return False
        ticket.status = status
        ticket.save(update_fields=['status'])
        return True
