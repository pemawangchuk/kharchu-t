# utils/kafka_service.py

import json
import os
from kafka import KafkaProducer

producer = None

KAFKA_ENABLED = os.getenv("KAFKA_ENABLED", "true") == "true"


def get_producer():
    global producer

    if not KAFKA_ENABLED:
        return None

    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=os.getenv("KAFKA_BROKER", "kafka:9092"),

                value_serializer=lambda v: json.dumps(v).encode("utf-8"),

                # safer production defaults
                acks=1,              # safer than 0
                linger_ms=10,
                retries=3
            )
        except Exception as e:
            print("Kafka not available:", e)
            producer = None

    return producer


# -----------------------------
# Ticket Created Event
# -----------------------------
def send_ticket_created(ticket):
    p = get_producer()
    if not p:
        return

    p.send("ticket_created", {
        "ticket_id": str(ticket.ticket_id),
        "ticket_number": ticket.ticket_number
    })


# -----------------------------
# Ticket Scanned Event
# -----------------------------
def send_ticket_scanned(attendee):
    p = get_producer()
    if not p:
        return

    p.send("ticket_scanned", {
        "ticket_number": attendee.ticket.ticket_number,
        "name": attendee.name,
        "phone": attendee.phone
    })