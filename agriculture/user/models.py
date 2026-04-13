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

    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title