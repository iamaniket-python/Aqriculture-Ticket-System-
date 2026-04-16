from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class Ticket(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()

    image = models.ImageField(upload_to='tickets/images/', blank=True, null=True)
    document = models.FileField(upload_to='tickets/docs/', blank=True, null=True)
    purchase = models.CharField(max_length=50,blank=True, null=True)
    category = models.CharField(max_length=50,blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending')
    
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



class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  