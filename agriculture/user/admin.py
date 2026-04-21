from django.contrib import admin
from .models import Purchase, Ticket,TrackingUser,TicketComment
# @admin.register(Ticket)
# class TicketAdmin(admin.ModelAdmin):
#     list_display = ['id', 'title', 'user', 'status', 'created_at']
#     list_filter = ['status']
#     search_fields = ['title', 'user__username']



class TicketCommentInline(admin.TabularInline):
    model = TicketComment
    extra = 1
    # 'sender' ko include karein lekin readonly rakhein taaki admin ise change na kare
    fields = ("sender", "message", "image", "created_at")  
    readonly_fields = ("sender", "created_at")

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "created_at")
    inlines = [TicketCommentInline]

    def save_formset(self, request, form, formset, change):
        # Jab Inline form save ho raha ho
        instances = formset.save(commit=False)

        for obj in instances:
            if isinstance(obj, TicketComment): # Check karein ki ye TicketComment ka object hai
                if not obj.pk:  # Sirf naye comments par admin set karein
                    obj.sender = request.user
                obj.save()
        
        # Deleted objects ko handle karne ke liye (agar koi remove kiya admin ne)
        for obj in formset.deleted_objects:
            obj.delete()

        formset.save_m2m()


admin.site.register(TrackingUser)
admin.site.register(Purchase)
admin.site.register(TicketComment)