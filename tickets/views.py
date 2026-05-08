# =========================
# IMPORTS
# =========================

import os
import qrcode
import secrets
import zipfile

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.db import transaction

from weasyprint import HTML

from .models import Ticket, Attendee
from .utils.redis_service import redis_client
from .utils.kafka_service import send_ticket_created, send_ticket_scanned


from django.contrib.auth.decorators import (
    login_required,
    user_passes_test
)


# =========================
# SUPERADMIN CHECK FUNCTION
# =========================

def is_superadmin(user):

    # allow only authenticated superuser
    return user.is_authenticated and user.is_superuser


# =========================
# 1. INDEX (SUPERADMIN ONLY)
# =========================


# =========================
# 1. INDEX (PAGINATION + FAST VIEW)
# =========================


@login_required
@user_passes_test(is_superadmin)
def index(request):

    # page number from URL
    page_number = request.GET.get("page", 1)

    # fetch tickets (latest first)
    tickets = Ticket.objects.all().order_by("-created_at")

    # paginate (important for 10K+ users)
    paginator = Paginator(tickets, 8)

    page_obj = paginator.get_page(page_number)

    ticket_list = []

    for ticket in page_obj:

        # check attendee (can be cached later if needed)
        attendee = getattr(ticket, "attendee", None)

        ticket_list.append({
            "ticket": ticket,
            "attendee": attendee,
            "is_assigned": attendee is not None,
            "qr_image": f"{settings.MEDIA_URL}qr_codes/{ticket.ticket_id}.png"
        })

    return render(request, "index.html", {
        "tickets": ticket_list,
        "page_obj": page_obj
    })


# =========================
# HOME PAGE
# =========================
# =========================
# HOME PAGE
# =========================
# =========================
# FAST HOME VIEW (OPTIMIZED)
# =========================

from django.db.models import Count
from django.shortcuts import render
from .models import Ticket, Attendee


def home(request):

    # ---------------------------------
    # SINGLE DATABASE QUERY (FAST)
    # ---------------------------------
    stats = Ticket.objects.aggregate(
        total_tickets=Count("id")
    )

    assigned_tickets = Attendee.objects.count()

    # ---------------------------------
    # EXTRACT VALUES (NO EXTRA QUERIES)
    # ---------------------------------
    total_tickets = stats["total_tickets"]

    available_tickets = total_tickets - assigned_tickets

    # ---------------------------------
    # RENDER RESPONSE
    # ---------------------------------
    return render(request, "home.html", {
        "total_tickets": total_tickets,
        "assigned_tickets": assigned_tickets,
        "available_tickets": available_tickets
    })
# =========================
# 2. CREATE SINGLE TICKET
# =========================
@login_required
@user_passes_test(is_superadmin)
def create_ticket(request):

    # create DB ticket
    ticket = Ticket.objects.create()

    # -----------------------------
    # REDIS CACHE (FAST LOOKUP)
    # -----------------------------
    redis_client.set(
        f"ticket:{ticket.ticket_number}",
        str(ticket.ticket_id),
        ex=86400
    )

    # -----------------------------
    # INCREMENT DASHBOARD COUNTER
    # -----------------------------
    redis_client.incr("total_tickets")

    # -----------------------------
    # QR GENERATION
    # -----------------------------
    qr_folder = os.path.join(settings.MEDIA_ROOT, "qr_codes")
    os.makedirs(qr_folder, exist_ok=True)

    qr_url = request.build_absolute_uri(f"/scan/{ticket.ticket_id}/")
    qr_img = qrcode.make(qr_url)

    qr_img.save(os.path.join(qr_folder, f"{ticket.ticket_id}.png"))

    # -----------------------------
    # KAFKA EVENT
    # -----------------------------
    send_ticket_created(ticket)

    return render(request, "ticket.html", {
        "ticket": ticket,
        "qr_image": f"{settings.MEDIA_URL}qr_codes/{ticket.ticket_id}.png"
    })


# =========================
# 3. SCAN TICKET (REDIS + KAFKA + ATOMIC SAFETY)
# =========================
@login_required
@user_passes_test(is_superadmin)
def scan_ticket(request, ticket_id):

    lock_key = f"scan:{ticket_id}"

    # -----------------------------
    # REDIS FAST CHECK
    # -----------------------------
    if redis_client.get(lock_key):
        return HttpResponse("❌ Ticket already scanned")

    ticket = get_object_or_404(Ticket, ticket_id=ticket_id)

    # DB safety check
    if Attendee.objects.filter(ticket=ticket).exists():
        redis_client.set(lock_key, "USED", ex=86400)
        return HttpResponse("❌ Ticket already used")

    if request.method == "POST":

        name = request.POST.get("name")
        phone = request.POST.get("phone")

        with transaction.atomic():

            # double check race condition
            if Attendee.objects.filter(ticket=ticket).exists():
                return HttpResponse("❌ Already assigned")

            attendee = Attendee.objects.create(
                ticket=ticket,
                name=name,
                phone=phone
            )

            # -----------------------------
            # REDIS UPDATE (REAL TIME)
            # -----------------------------
            redis_client.incr("assigned_tickets")
            redis_client.set(lock_key, "USED", ex=86400)

            # -----------------------------
            # KAFKA EVENT
            # -----------------------------
            send_ticket_scanned(attendee)

        return HttpResponse("✅ Check-in successful")

    return render(request, "scan.html", {"ticket": ticket})


# =========================
# 4. BULK TICKET GENERATION (FAST + SAFE + UNIQUE)
# =========================
@login_required
@user_passes_test(is_superadmin)
def generate_40_tickets(request):

    output_folder = os.path.join(settings.MEDIA_ROOT, "tickets")
    qr_folder = os.path.join(settings.MEDIA_ROOT, "qr_codes")

    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(qr_folder, exist_ok=True)

    existing_numbers = set(
        Ticket.objects.values_list("ticket_number", flat=True)
    )

    ticket_objects = []

    # generate unique tickets
    for _ in range(50):

        while True:
            number = ''.join(str(secrets.randbelow(10)) for _ in range(10))

            if number not in existing_numbers:
                existing_numbers.add(number)
                break

        ticket_objects.append(Ticket(ticket_number=number))

    # FAST bulk insert
    Ticket.objects.bulk_create(ticket_objects)

    tickets = Ticket.objects.order_by("-created_at")[:50]

    for ticket in tickets:

        # REDIS CACHE
        redis_client.set(
            f"ticket:{ticket.ticket_number}",
            str(ticket.ticket_id),
            ex=86400
        )

        # QR GENERATION
        qr_url = request.build_absolute_uri(f"/scan/{ticket.ticket_id}/")
        qr_img = qrcode.make(qr_url)

        qr_img.save(os.path.join(qr_folder, f"{ticket.ticket_id}.png"))

        # PDF GENERATION
        html_string = render_to_string("ticket.html", {
            "ticket": ticket,
            "qr_image": f"{settings.MEDIA_URL}qr_codes/{ticket.ticket_id}.png"
        })

        pdf_path = os.path.join(output_folder, f"{ticket.ticket_number}.pdf")

        HTML(
            string=html_string,
            base_url=request.build_absolute_uri("/")
        ).write_pdf(pdf_path)

        # KAFKA EVENT
        send_ticket_created(ticket)

    return HttpResponse("✅ 50 Tickets Generated Successfully")


# =========================
# 5. CAMERA SCAN
# =========================
@login_required
@user_passes_test(is_superadmin)
def camera_scan(request):
    return render(request, "camera_scan.html")


# =========================
# 6. LOOKUP (TICKET / PHONE SEARCH)
# =========================
@login_required
@user_passes_test(is_superadmin)
def ticket_lookup(request):

    query = request.GET.get("q", "").strip()

    ticket = Ticket.objects.filter(ticket_number=query).first()

    attendee = None

    if not ticket:
        attendee = Attendee.objects.filter(phone=query).first()
        if attendee:
            ticket = attendee.ticket

    if not ticket:
        return render(request, "ticket_lookup.html", {
            "error": "No ticket found"
        })

    attendee = getattr(ticket, "attendee", None)

    return render(request, "ticket_lookup.html", {
        "ticket": ticket,
        "attendee": attendee,
        "status": "ASSIGNED" if attendee else "AVAILABLE"
    })


# =========================
# 7. DOWNLOAD ALL TICKETS (ZIP)
# =========================

def download_all_tickets(request):

    pdf_folder = os.path.join(settings.MEDIA_ROOT, "tickets")
    zip_path = os.path.join(settings.MEDIA_ROOT, "all_tickets.zip")

    with zipfile.ZipFile(zip_path, "w") as zipf:

        for ticket in Ticket.objects.all():

            pdf_file = f"{ticket.ticket_number}.pdf"
            pdf_path = os.path.join(pdf_folder, pdf_file)

            if os.path.exists(pdf_path):
                zipf.write(pdf_path, pdf_file)

    with open(zip_path, "rb") as f:
        response = HttpResponse(f.read(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="all_tickets.zip"'
        return response


# =========================
# 8. DASHBOARD (REDIS LIVE COUNTERS)
# =========================
@login_required
@user_passes_test(is_superadmin)
def dashboard(request):

   # ---------------------------------
    # SINGLE DATABASE QUERY (FAST)
    # ---------------------------------
    stats = Ticket.objects.aggregate(
        total_tickets=Count("id")
    )

    assigned_tickets = Attendee.objects.count()

    # ---------------------------------
    # EXTRACT VALUES (NO EXTRA QUERIES)
    # ---------------------------------
    total_tickets = stats["total_tickets"]

    available_tickets = total_tickets - assigned_tickets

    # ---------------------------------
    # RENDER RESPONSE
    # ---------------------------------
    return render(request, "dashboard.html", {
        "total_tickets": total_tickets,
        "assigned_tickets": assigned_tickets,
        "available_tickets": available_tickets
    })
   