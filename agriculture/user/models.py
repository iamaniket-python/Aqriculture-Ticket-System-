from django.db import models
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField


class Purchase(models.Model):
    mobile = models.CharField(max_length=15, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchases')
    product_name = models.CharField(max_length=200)
    purchase_id = models.CharField(max_length=100, unique=True)  # unique to avoid duplicates
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['purchase_id']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"{self.product_name} ({self.purchase_id})"


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]

    CATEGORY_CHOICES = [
        ('billing', 'Billing'),
        ('technical', 'Technical'),
        ('delivery', 'Delivery'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets')
    title = models.CharField(max_length=255)
    description = models.TextField()

    # Removed image from here — use TicketImage model instead (cleaner)
    document = CloudinaryField(resource_type='raw', blank=True, null=True)
    purchase = models.ForeignKey(
        Purchase, on_delete=models.SET_NULL,  # SET_NULL is safer than CASCADE
        blank=True, null=True, related_name='tickets'
    )
    other = models.CharField(max_length=255, blank=True, null=True)
    assigned_to = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'is_staff': True},
        related_name='assigned_tickets'
    )
    category = models.CharField(
        max_length=50, blank=True, null=True,
        choices=CATEGORY_CHOICES  # controlled choices, not free text
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True) 
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['user']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"[{self.status.upper()}] {self.title}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    mobile = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username


class TrackingUser(models.Model):
    mobile = models.CharField(max_length=15)
    tracking_id = models.CharField(max_length=50, unique=True)

    class Meta:
        indexes = [
            models.Index(fields=['tracking_id']),
        ]

    def __str__(self):
        return self.tracking_id


class TicketImage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')
    uploaded_at = models.DateTimeField(auto_now_add=True) 

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Image for Ticket #{self.ticket.id}"


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='chats')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    image = CloudinaryField('image', blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['ticket']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.sender} - {self.message[:20]}"


class AdminChat(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_msgs')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_msgs')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['is_read']),
        ]

    def __str__(self):
        return f"{self.sender} → {self.receiver}"


class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username