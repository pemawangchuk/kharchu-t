from django.urls import path
from .views import create_ticket, dashboard, home, download_all_tickets, camera_scan, scan_ticket,  generate_40_tickets, index, ticket_lookup

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path("", home),
    path("index/", index),
    path("create/", create_ticket),
    path("camera/", camera_scan),
    path("scan/<uuid:ticket_id>/", scan_ticket),
     path(
        'generate-tickets/',
        generate_40_tickets,
        name='generate_tickets'
    ),
    path("ticket/lookup/", ticket_lookup, name="ticket_lookup"),
    path("tickets/download-all/", download_all_tickets, name="download_all_tickets"),
    path("dashboard/", dashboard, name="dashboard"),
]
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)