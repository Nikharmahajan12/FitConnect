
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Subscription, SubscriptionNotification


class Command(BaseCommand):
    help = "Generate subscription expiry reminders for clients"

    def handle(self, *args, **options):
        today = timezone.localdate()
        reminders_created = 0

        # Send reminders 5, 2, 1, and 0 days before/on expiry
        for days_left in (5, 2, 1, 0):
            expiry_date = today + timedelta(days=days_left)

            subscriptions = Subscription.objects.filter(
                status="active",
                start_date__lte=today,
                end_date=expiry_date,
            ).select_related(
                "client",
                "client__user",
            )

            for subscription in subscriptions:
                user = subscription.client.user
                client_name = user.first_name or user.username

                # Customize the title and message
                if days_left == 0:
                    title = "Your subscription expires today"

                    message = (
                        f"Hi {client_name}, your "
                        f"{subscription.plan_name} subscription "
                        f"expires today, "
                        f"{subscription.end_date:%d %b %Y}. "
                        "Please renew today to continue enjoying "
                        "your FitConnect services."
                    )
                else:
                    day_text = "day" if days_left == 1 else "days"

                    title = (
                        f"Subscription expires in "
                        f"{days_left} {day_text}"
                    )

                    message = (
                        f"Hi {client_name}, your "
                        f"{subscription.plan_name} subscription "
                        f"expires on "
                        f"{subscription.end_date:%d %b %Y}. "
                        "Please renew your subscription to continue "
                        "enjoying your FitConnect services."
                    )

                # Avoid creating duplicate reminders
                notification, created = (
                    SubscriptionNotification.objects.get_or_create(
                        subscription=subscription,
                        reminder_days=days_left,
                        defaults={
                            "title": title,
                            "message": message,
                        },
                    )
                )

                if created:
                    reminders_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Subscription reminders created: "
                f"{reminders_created}"
            )
        )
