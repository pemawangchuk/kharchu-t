from django.db import models
import uuid
import secrets
class Seller(models.Model):

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
   

class Ticket(models.Model):

    ticket_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    ticket_number = models.CharField(
        max_length=10,
        unique=True,
        db_index=True
    )
    seller = models.ForeignKey(
        "Seller",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return str(self.ticket_number)

    @staticmethod
    def generate_ticket_number():

        while True:

            number = ''.join(
                str(secrets.randbelow(10))
                for _ in range(10)
            )

            if not Ticket.objects.filter(
                ticket_number=number
            ).exists():
                return number

    def save(self, *args, **kwargs):

        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()

        super().save(*args, **kwargs)


class Attendee(models.Model):

    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attendee"
    )

    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

