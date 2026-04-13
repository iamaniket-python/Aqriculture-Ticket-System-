from django.contrib import admin
from .models import Ticket,TrackingUser
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['title', 'user__username']

  

admin.site.register(TrackingUser)