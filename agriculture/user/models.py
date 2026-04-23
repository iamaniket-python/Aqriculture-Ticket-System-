from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User


class Purchase(models.Model):
    mobile = models.CharField(max_length=15, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    purchase_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} ({self.purchase_id})"
class Ticket(models.Model):
      

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ]
      
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()

    image = models.ImageField(upload_to='tickets/images/', blank=True, null=True)
    document = models.FileField(upload_to='tickets/docs/', blank=True, null=True)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, blank=True, null=True)
    other = models.CharField(max_length=255, blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, limit_choices_to={'is_staff': True}, related_name='assigned_tickets')
    category = models.CharField(max_length=50,blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return self.title


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15)

    def __str__(self):
        return self.user.username

class TrackingUser(models.Model):
    mobile = models.CharField(max_length=15)
    tracking_id = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.tracking_id


class TicketImage(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to='tickets/images/')




class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="chats")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    image = models.ImageField(upload_to="chat_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    is_read = models.BooleanField(default=False)
    def __str__(self):
        return f"{self.sender} - {self.message[:20]}"
    

class AdminChat(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_msgs")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_msgs")

    message = models.TextField()
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} → {self.receiver}"