
from kafka import KafkaProducer

import json


producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)


def send_ticket_created(ticket):

    data = {
        "ticket_id": str(ticket.ticket_id),
        "ticket_number": ticket.ticket_number
    }

    producer.send(
        'ticket_created',
        data
    )

    producer.flush()
