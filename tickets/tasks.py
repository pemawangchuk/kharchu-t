
import os
import qrcode

from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from django.db import transaction

from weasyprint import HTML
from .models import Ticket
from .utils.kafka_producer import send_ticket_created

import redis

# tasks.py
redis_client = redis.Redis(
    host='redis',
    port=6379,
    db=0,
    decode_responses=True
)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_ticket(self, ticket_id, base_url):

    try:
        ticket = Ticket.objects.get(ticket_id=ticket_id)

    except Ticket.DoesNotExist:
        return f"Ticket {ticket_id} not found"

    # -----------------------------
    # REDIS CACHE
    # -----------------------------
    redis_client.set(
        f"ticket:{ticket.ticket_number}",
        str(ticket.ticket_id),
        ex=86400
    )

    # -----------------------------
    # PATHS (created once per worker process)
    # -----------------------------
    qr_folder = os.path.join(settings.MEDIA_ROOT, "qr_codes")
    output_folder = os.path.join(settings.MEDIA_ROOT, "tickets")

    os.makedirs(qr_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)

    # -----------------------------
    # QR GENERATION
    # -----------------------------
    qr_url = f"{base_url}scan/{ticket.ticket_id}/"
    qr_img = qrcode.make(qr_url)

    qr_path = os.path.join(qr_folder, f"{ticket.ticket_id}.png")
    qr_img.save(qr_path)

    # -----------------------------
    # PDF GENERATION
    # -----------------------------
    html_string = render_to_string(
        "ticket.html",
        {
            "ticket": ticket,
            "qr_image": f"{settings.MEDIA_URL}qr_codes/{ticket.ticket_id}.png"
        }
    )

    pdf_path = os.path.join(output_folder, f"{ticket.ticket_number}.pdf")

    HTML(
        string=html_string,
        base_url=base_url
    ).write_pdf(pdf_path)

    # -----------------------------
    # KAFKA EVENT
    # -----------------------------
    send_ticket_created(ticket)

    return "SUCCESS"
