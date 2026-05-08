from locust import HttpUser, task, between
import random
import re


class TicketSystemUser(HttpUser):

    wait_time = between(0.1, 0.5)

    ticket_ids = []

    # =================================================
    # CREATE REAL TICKETS ON START
    # =================================================
    def on_start(self):

        # create multiple real tickets
        for _ in range(3):

            res = self.client.get("/create-ticket/")

            # extract ticket_id from response HTML
            match = re.search(
                r"ticket_id.*?([a-f0-9\-]{36})",
                res.text
            )

            if match:
                self.ticket_ids.append(match.group(1))

        # fallback safety (prevents crash)
        if not self.ticket_ids:
            self.ticket_ids = ["invalid-test-id"]

        self.name = f"User-{random.randint(1, 999999)}"
        self.phone = str(random.randint(7000000000, 9999999999))

    # =================================================
    # CREATE TICKET LOAD TEST
    # =================================================
    @task(2)
    def create_ticket(self):
        self.client.get("/create-ticket/")

    # =================================================
    # OPEN SCAN PAGE
    # =================================================
    @task(3)
    def open_scan_page(self):

        ticket_id = random.choice(self.ticket_ids)

        self.client.get(f"/scan/{ticket_id}/")

    # =================================================
    # SCAN / CHECK-IN
    # =================================================
    @task(5)
    def scan_ticket(self):

        ticket_id = random.choice(self.ticket_ids)

        self.client.post(
            f"/scan/{ticket_id}/",
            data={
                "name": self.name,
                "phone": self.phone
            }
        )

    # =================================================
    # DUPLICATE SCAN ATTACK (REAL RACE CONDITION TEST)
    # =================================================
    @task(1)
    def duplicate_scan_attack(self):

        ticket_id = random.choice(self.ticket_ids)

        # first scan
        self.client.post(
            f"/scan/{ticket_id}/",
            data={
                "name": self.name,
                "phone": self.phone
            }
        )

        # immediate second scan (stress Redis + DB)
        self.client.post(
            f"/scan/{ticket_id}/",
            data={
                "name": self.name,
                "phone": self.phone
            }
        )