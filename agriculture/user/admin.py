from django.contrib import admin
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['title', 'user__username']