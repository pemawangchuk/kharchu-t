from kafka import KafkaConsumer
import json

# -------------------------------------------------
# Kafka Consumer (LIVE LOG SYSTEM)
# -------------------------------------------------
consumer = KafkaConsumer(
    "ticket_created",
    "ticket_scanned",
    bootstrap_servers="localhost:9092",
    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    auto_offset_reset="latest",   # only new events
    enable_auto_commit=True
)

print("🚀 Kafka Live Log Started...\n")

# -------------------------------------------------
# LISTEN EVENTS IN REAL TIME
# -------------------------------------------------
for message in consumer:

    topic = message.topic
    data = message.value

    print("\n==============================")
    print(f"📡 EVENT: {topic}")
    print("------------------------------")

    if topic == "ticket_created":
        print("🎟 Ticket Created Event")
        print(f"ID      : {data['ticket_id']}")
        print(f"Number  : {data['ticket_number']}")

    elif topic == "ticket_scanned":
        print("📲 Ticket Scanned Event")
        print(f"Ticket  : {data['ticket']}")
        print(f"Name    : {data['name']}")
        print(f"Phone   : {data['phone']}")

    print("==============================\n")