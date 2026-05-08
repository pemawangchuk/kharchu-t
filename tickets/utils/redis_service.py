# utils/redis_service.py

import redis

# -----------------------------
# Redis connection (FAST cache layer)
# -----------------------------
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)


# -----------------------------
# Increment dashboard counters
# -----------------------------
def increment_ticket_counter():
    redis_client.incr("total_tickets")


def increment_assigned_counter():
    redis_client.incr("assigned_tickets")


# -----------------------------
# Get dashboard stats (FAST O(1))
# -----------------------------
def get_dashboard_stats():

    return {
        "total": redis_client.get("total_tickets") or 0,
        "assigned": redis_client.get("assigned_tickets") or 0
    }