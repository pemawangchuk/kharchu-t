from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Ticket, Attendee

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "ticket_id", "created_at")
    search_fields = ("ticket_number", "ticket_id",)
    readonly_fields = ("ticket_number", "ticket_id", "created_at")


@admin.register(Attendee)
class AttendeeAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "ticket", "scanned_at")
    search_fields = ("name", "phone")
    readonly_fields = ("ticket", "scanned_at")
