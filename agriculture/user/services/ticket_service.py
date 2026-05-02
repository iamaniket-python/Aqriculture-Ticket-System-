import logging
import os

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Q

from user.models import Purchase, Ticket, TicketComment, TicketImage

logger = logging.getLogger(__name__)

# ─── File Upload Config ───────────────────────────────────────
MAX_IMAGE_SIZE_MB   = 5
MAX_DOC_SIZE_MB     = 10
MAX_IMAGES_PER_TICKET = 5

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_DOC_TYPES   = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
}

DASHBOARD_CACHE_KEY    = "admin_dashboard_stats:{user_filter}"
DASHBOARD_CACHE_TIMEOUT = 60   # 1 minute


class TicketService:
    """
    Ticket se related sab business logic yahan.
    Views mein sirf request/response handling hogi.
    """

    @staticmethod
    def get_user_tickets(user, product="", date_from="", date_to=""):
        qs = (
            Ticket.objects
            .filter(user=user)
            .select_related('purchase', 'assigned_to')
            .prefetch_related('images')
        )

        if product:
            qs = qs.filter(purchase__product_name__icontains=product)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs.order_by('-created_at')

    @staticmethod
    def _validate_images(images: list) -> None:
        """Image files validate karo — size aur type check."""
        if len(images) > MAX_IMAGES_PER_TICKET:
            raise ValidationError(
                f"Maximum {MAX_IMAGES_PER_TICKET} images allowed per ticket."
            )
        for img in images:
            if img.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(
                    f"Image '{img.name}' exceeds {MAX_IMAGE_SIZE_MB}MB limit."
                )
            if img.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError(
                    f"'{img.name}' is not a supported image type. "
                    f"Allowed: JPEG, PNG, WebP, GIF."
                )

    @staticmethod
    def _validate_document(document) -> None:
        """Document file validate karo — size aur type check."""
        if document is None:
            return
        if document.size > MAX_DOC_SIZE_MB * 1024 * 1024:
            raise ValidationError(
                f"Document exceeds {MAX_DOC_SIZE_MB}MB limit."
            )
        if document.content_type not in ALLOWED_DOC_TYPES:
            raise ValidationError(
                "Unsupported document type. Allowed: PDF, DOC, DOCX, TXT."
            )

    @staticmethod
    def create_ticket(user: User, data: dict, images: list, document=None) -> Ticket:
        """
        Ticket create karo with full validation.
        Raises ValidationError on bad input, Purchase.DoesNotExist if purchase invalid.
        """
        # ✅ Validate required fields explicitly
        title       = data.get('title', '').strip()
        description = data.get('description', '').strip()
        category    = data.get('category', '').strip()
        purchase_id = data.get('purchase', '').strip()
        product     = data.get('product', '').strip()

        if not title:
            raise ValidationError("Title is required.")
        if not description:
            raise ValidationError("Description is required.")

        # ✅ Validate files before hitting DB
        TicketService._validate_images(images)
        TicketService._validate_document(document)

        # ✅ purchase_id optional — ticket without purchase allowed
        purchase = None
        if purchase_id and product:
            purchase = Purchase.objects.get(
                user=user,
                purchase_id=purchase_id,
                product_name=product,
            )

        ticket = Ticket.objects.create(
            user        = user,
            purchase    = purchase,
            title       = title,
            description = description,
            category    = category or None,
            other       = data.get('other', '').strip() or None,
            document    = document,
        )

        # ✅ bulk_create for efficiency
        if images:
            TicketImage.objects.bulk_create([
                TicketImage(ticket=ticket, image=img) for img in images
            ])

        # ✅ Invalidate dashboard cache — new ticket changes stats
        cache.delete_pattern("admin_dashboard_stats:*") \
            if hasattr(cache, 'delete_pattern') \
            else cache.delete(DASHBOARD_CACHE_KEY.format(user_filter=None))

        logger.info(
            "Ticket #%s created by user '%s' (id=%s)",
            ticket.id, user.username, user.id
        )
        return ticket

    @staticmethod
    def add_comment(
        ticket: Ticket,
        sender: User,
        message: str,
        image=None,          # ✅ now accepts image from ticket_chat view
    ) -> TicketComment:
        """Add a comment — optionally with an image attachment."""

        # ✅ Validate comment image if provided
        if image:
            if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(
                    f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit."
                )
            if image.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError("Unsupported image type.")

        comment = TicketComment.objects.create(
            ticket  = ticket,
            sender  = sender,
            message = message,
            image   = image,
            is_read = False,
        )
        logger.debug(
            "Comment added to Ticket #%s by '%s'",
            ticket.id, sender.username if sender else "anonymous"
        )
        return comment

    @staticmethod
    def mark_comments_read(ticket: Ticket, exclude_staff: bool = True) -> int:
        """
        Mark comments as read.
        Returns count of updated comments.
        """
        qs = TicketComment.objects.filter(ticket=ticket, is_read=False)
        if exclude_staff:
            qs = qs.filter(
                sender__is_staff=False,
                sender__is_superuser=False,
            )
        updated = qs.update(is_read=True)
        return updated   # ✅ return count so callers can log/check if needed

    @staticmethod
    def get_dashboard_stats(user_filter: str = None) -> dict:
        """
        Admin dashboard stats — cached for 1 minute.
        Prevents 4 COUNT queries on every page load.
        """
        cache_key = DASHBOARD_CACHE_KEY.format(user_filter=user_filter or "all")
        cached    = cache.get(cache_key)

        if cached:
            return cached

        qs = Ticket.objects.all()
        if user_filter:
            qs = qs.filter(user_id=user_filter)

        stats = qs.aggregate(
            total       = Count('id'),
            pending     = Count('id', filter=Q(status='pending')),
            resolved    = Count('id', filter=Q(status='resolved')),
            in_progress = Count('id', filter=Q(status='in_progress')),
        )

        cache.set(cache_key, stats, timeout=DASHBOARD_CACHE_TIMEOUT)
        return stats

    @staticmethod
    def assign_to_staff(ticket: Ticket, staff: User) -> None:
        """Assign ticket to staff — auto sets status to in_progress."""
        if not staff.is_staff:
            raise ValidationError("Selected user is not a staff member.")

        ticket.assigned_to = staff
        ticket.status      = 'in_progress'
        ticket.save(update_fields=['assigned_to', 'status'])

        logger.info(
            "Ticket #%s assigned to staff '%s' (id=%s)",
            ticket.id, staff.username, staff.id
        )

    @staticmethod
    def update_status(ticket: Ticket, status: str) -> bool:
        """
        Update ticket status.
        Returns True on success, False on invalid status.
        Raises ValueError so caller can handle it properly.
        """
        valid = ('pending', 'in_progress', 'resolved')
        if status not in valid:
            logger.warning(
                "Invalid status '%s' attempted on Ticket #%s",
                status, ticket.id
            )
            raise ValueError(f"Invalid status '{status}'. Must be one of: {valid}")

        old_status    = ticket.status
        ticket.status = status
        ticket.save(update_fields=['status'])

        # ✅ Invalidate dashboard cache on every status change
        cache.delete_pattern("admin_dashboard_stats:*") \
            if hasattr(cache, 'delete_pattern') \
            else cache.delete(DASHBOARD_CACHE_KEY.format(user_filter=None))

        logger.info(
            "Ticket #%s status: '%s' → '%s'",
            ticket.id, old_status, status
        )
        return True