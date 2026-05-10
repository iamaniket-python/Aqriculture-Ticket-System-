import logging

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Count, Q

from user.models import Purchase, Ticket, TicketComment, TicketImage

logger = logging.getLogger(__name__)


# ─── File Upload Config ───────────────────────────────────────
MAX_IMAGE_SIZE_MB     = 5
MAX_DOC_SIZE_MB       = 10
MAX_IMAGES_PER_TICKET = 5

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
ALLOWED_DOC_TYPES   = {
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
}


# ─── Cache Config ────────────────────────────────────────────
DASHBOARD_CACHE_KEY     = "admin_dashboard_stats:{user_filter}"
DASHBOARD_CACHE_TIMEOUT = 60    # 1 minute

USER_TICKETS_CACHE_KEY     = "tickets:user:{user_id}:{product}:{date_from}:{date_to}"
USER_TICKETS_CACHE_TIMEOUT = 30  # 30 seconds

TICKET_DETAIL_CACHE_KEY     = "ticket:detail:{ticket_id}"
TICKET_DETAIL_CACHE_TIMEOUT = 120  # 2 minutes

UNREAD_COUNT_CACHE_KEY     = "admin:unread_count"
UNREAD_COUNT_CACHE_TIMEOUT = 30   # 30 seconds


def _delete_pattern(pattern: str) -> None:
    """
    Delete all cache keys matching pattern.
    Uses Redis wildcard if available, else deletes known keys.
    """
    try:
        from django_redis import get_redis_connection
        redis = get_redis_connection('default')
        # ✅ get the full key with prefix
        keys = redis.keys(f"*{pattern.replace('*', '')}*")
        if keys:
            redis.delete(*keys)
    except Exception:
        # Fallback for non-Redis cache — delete exact key
        cache.delete(pattern.replace('*', ''))


class TicketService:
    """
    All ticket business logic here.
    Views only handle request/response — no logic.
    """

    # =========================================================
    # 📋 TICKET QUERIES — Optimized
    # =========================================================

    @staticmethod
    def get_user_tickets(user, product="", date_from="", date_to=""):
        """
        Fetch user tickets with only needed fields.
        Uses select_related + only() to minimize DB data transfer.
        """
        qs = (
            Ticket.objects
            .filter(user=user)
            .select_related('purchase', 'assigned_to')
            .only(                              # ✅ fetch ONLY what profile page needs
                'id', 'title', 'status', 'created_at', 'updated_at',
                'purchase__product_name',
                'assigned_to__username',
            )
            .prefetch_related('images')
            .order_by('-created_at')
        )

        if product:
            qs = qs.filter(purchase__product_name__icontains=product)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    @staticmethod
    def get_user_tickets_cached(user, product="", date_from="", date_to=""):
        """
        Cached version of get_user_tickets.
        Cache invalidated on ticket create/update.
        Use this in profile view for best performance.
        """
        cache_key = USER_TICKETS_CACHE_KEY.format(
            user_id=user.id,
            product=product or '',
            date_from=date_from or '',
            date_to=date_to or '',
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        # Cache miss — fetch from DB
        qs     = TicketService.get_user_tickets(user, product, date_from, date_to)
        result = list(qs)   # ✅ evaluate queryset once, store list
        cache.set(cache_key, result, timeout=USER_TICKETS_CACHE_TIMEOUT)
        logger.debug("Cache MISS for user tickets: user_id=%s", user.id)
        return result

    @staticmethod
    def get_dashboard_tickets(user_filter=None):
        """
        Optimized ticket list for admin dashboard.
        Fetches only columns needed for the table — no heavy fields.
        """
        qs = (
            Ticket.objects
            .select_related('user', 'assigned_to', 'purchase')
            .only(                            
                'id', 'title', 'status', 'category', 'created_at', 'updated_at',
                'user__id', 'user__username',
                'assigned_to__id', 'assigned_to__username',
                'purchase__product_name',
            )
            .order_by('-created_at')
        )
        if user_filter:
            qs = qs.filter(user_id=user_filter)
        return qs

    @staticmethod
    def get_ticket_detail_cached(ticket_id: int) -> Ticket | None:
        """
        Cache individual ticket detail page — invalidated on any update.
        """
        cache_key = TICKET_DETAIL_CACHE_KEY.format(ticket_id=ticket_id)
        cached    = cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            ticket = (
                Ticket.objects
                .select_related('user', 'purchase', 'assigned_to')
                .prefetch_related('images', 'chats__sender')
                .get(id=ticket_id)
            )
            cache.set(cache_key, ticket, timeout=TICKET_DETAIL_CACHE_TIMEOUT)
            return ticket
        except Ticket.DoesNotExist:
            return None

    # =========================================================
    # 📊 DASHBOARD STATS — Cached
    # =========================================================

    @staticmethod
    def get_dashboard_stats(user_filter=None) -> dict:
        """
        All stats in ONE aggregate query — cached for 1 minute.
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
    def get_unread_count_cached() -> int:
        """
        Cache unread message count — recalculated every 30 seconds.
        Saves a COUNT query on every admin page load.
        """
        cached = cache.get(UNREAD_COUNT_CACHE_KEY)
        if cached is not None:
            return cached

        count = TicketComment.objects.filter(
            is_read=False,
            sender__is_staff=False,
            sender__is_superuser=False,
        ).count()

        cache.set(UNREAD_COUNT_CACHE_KEY, count, timeout=UNREAD_COUNT_CACHE_TIMEOUT)
        return count

    # =========================================================
    # 🗑️ CACHE INVALIDATION
    # =========================================================

    @staticmethod
    def invalidate_user_cache(user_id: int) -> None:
        """
        Clear all ticket cache for a specific user.
        Call whenever a ticket is created or updated for this user.
        """
        try:
            from django_redis import get_redis_connection
            redis = get_redis_connection('default')
            keys  = redis.keys(f"*tickets:user:{user_id}*")
            if keys:
                redis.delete(*keys)
                logger.debug("Invalidated %d cache keys for user_id=%s", len(keys), user_id)
        except Exception:
            # Fallback — delete the most common key pattern
            cache.delete(USER_TICKETS_CACHE_KEY.format(
                user_id=user_id, product='', date_from='', date_to=''
            ))

    @staticmethod
    def invalidate_ticket_cache(ticket_id: int) -> None:
        """Clear cached ticket detail."""
        cache.delete(TICKET_DETAIL_CACHE_KEY.format(ticket_id=ticket_id))

    @staticmethod
    def invalidate_dashboard_cache() -> None:
        """Clear all dashboard stat caches."""
        cache.delete(UNREAD_COUNT_CACHE_KEY)
        _delete_pattern("admin_dashboard_stats")

    # =========================================================
    # ✅ VALIDATION
    # =========================================================

    @staticmethod
    def _validate_images(images: list) -> None:
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

    # =========================================================
    # 🎫 TICKET CRUD
    # =========================================================

    @staticmethod
    def create_ticket(user: User, data: dict, images: list, document=None) -> Ticket:
        """
        Create ticket with full validation.
        Invalidates user + dashboard cache on success.
        """
        title       = data.get('title', '').strip()
        description = data.get('description', '').strip()
        category    = data.get('category', '').strip()
        purchase_id = data.get('purchase', '').strip()
        product     = data.get('product', '').strip()

        if not title:
            raise ValidationError("Title is required.")
        if not description:
            raise ValidationError("Description is required.")

        # Validate files before DB hit
        TicketService._validate_images(images)
        TicketService._validate_document(document)

        purchase = None
        if purchase_id and product:
            purchase = Purchase.objects.get(
                user=user,
                purchase_id=purchase_id,
                product_name=product,
            )

        # ✅ Pending ticket check
        if purchase:
            pending_exists = Ticket.objects.filter(
                user=user,
                purchase=purchase,
                status='pending'
            ).exists()
            if pending_exists:
                raise ValidationError("You already have a pending ticket for this order. Please wait for it to be resolved.")

        ticket = Ticket.objects.create(
            user        = user,
            purchase    = purchase,
            title       = title,
            description = description,
            category    = category or None,
            other       = data.get('other', '').strip() or None,
            document    = document,
        )

        if images:
            TicketImage.objects.bulk_create([
                TicketImage(ticket=ticket, image=img) for img in images
            ])

        # ✅ Invalidate all related caches
        TicketService.invalidate_user_cache(user.id)
        TicketService.invalidate_dashboard_cache()

        logger.info(
            "Ticket #%s created by user '%s' (id=%s)",
            ticket.id, user.username, user.id,
        )
        return ticket

    @staticmethod
    def add_comment(
        ticket: Ticket,
        sender: User,
        message: str,
        image=None,
    ) -> TicketComment:
        """Add comment — optionally with image. Invalidates ticket cache."""
        if image:
            if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"Image exceeds {MAX_IMAGE_SIZE_MB}MB limit.")
            if image.content_type not in ALLOWED_IMAGE_TYPES:
                raise ValidationError("Unsupported image type.")

        comment = TicketComment.objects.create(
            ticket  = ticket,
            sender  = sender,
            message = message,
            image   = image,
            is_read = False,
        )

        # ✅ Invalidate ticket detail + unread count cache
        TicketService.invalidate_ticket_cache(ticket.id)
        cache.delete(UNREAD_COUNT_CACHE_KEY)

        logger.debug(
            "Comment on Ticket #%s by '%s'",
            ticket.id, sender.username if sender else "anonymous",
        )
        return comment

    @staticmethod
    def mark_comments_read(ticket: Ticket, exclude_staff: bool = True) -> int:
        qs = TicketComment.objects.filter(ticket=ticket, is_read=False)
        if exclude_staff:
            qs = qs.filter(
                sender__is_staff=False,
                sender__is_superuser=False,
            )
        updated = qs.update(is_read=True)

        # ✅ Invalidate unread count cache
        if updated:
            cache.delete(UNREAD_COUNT_CACHE_KEY)

        return updated

    @staticmethod
    def assign_to_staff(ticket: Ticket, staff: User) -> None:
        if not staff.is_staff:
            raise ValidationError("Selected user is not a staff member.")

        ticket.assigned_to = staff
        ticket.status      = 'in_progress'
        ticket.save(update_fields=['assigned_to', 'status'])

        # ✅ Invalidate all related caches
        TicketService.invalidate_ticket_cache(ticket.id)
        TicketService.invalidate_user_cache(ticket.user.id)
        TicketService.invalidate_dashboard_cache()

        logger.info(
            "Ticket #%s assigned to staff '%s' (id=%s)",
            ticket.id, staff.username, staff.id,
        )

    @staticmethod
    def update_status(ticket: Ticket, status: str) -> bool:
        valid = ('pending', 'in_progress', 'resolved')
        if status not in valid:
            logger.warning(
                "Invalid status '%s' on Ticket #%s", status, ticket.id
            )
            raise ValueError(f"Invalid status '{status}'. Must be one of: {valid}")

        old_status    = ticket.status
        ticket.status = status
        ticket.save(update_fields=['status'])

        # ✅ Invalidate all related caches
        TicketService.invalidate_ticket_cache(ticket.id)
        TicketService.invalidate_user_cache(ticket.user.id)
        TicketService.invalidate_dashboard_cache()

        logger.info(
            "Ticket #%s: '%s' → '%s'", ticket.id, old_status, status
        )
        return True