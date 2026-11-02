
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    ClientProfile,
    Subscription,
    SubscriptionNotification,
)


class Command(BaseCommand):
    help = (
        "Process subscription reminders, expire subscriptions, "
        "and deactivate clients whose subscriptions have ended."
    )

    def handle(self, *args, **options):
        today = timezone.localdate()

        # =====================================================
        # 1. EXPIRE SUBSCRIPTIONS THAT HAVE ENDED
        # =====================================================

        expired_count = 0

        expired_subscriptions = (
            Subscription.objects
            .filter(
                status="active",
                end_date__lt=today,
            )
        )

        for subscription in expired_subscriptions.iterator():
            subscription.status = "expired"

            subscription.save(
                update_fields=["status", "updated_at"]
            )

            expired_count += 1

        # =====================================================
        # 2. DEACTIVATE CLIENTS WITHOUT A VALID SUBSCRIPTION
        # =====================================================

        deactivated_count = 0

        # Clients with a subscription that has already ended.
        expired_client_ids = (
            Subscription.objects
            .filter(end_date__lt=today)
            .values_list("client_id", flat=True)
            .distinct()
        )

        clients = (
            ClientProfile.objects
            .filter(id__in=expired_client_ids)
            .select_related("user")
        )

        for client in clients.iterator():

            has_valid_subscription = (
                Subscription.objects
                .filter(
                    client=client,
                    status="active",
                    start_date__lte=today,
                    end_date__gte=today,
                )
                .exists()
            )

            # Never automatically reactivate an account.
            # Only deactivate it when no valid subscription exists.
            if (
                not has_valid_subscription
                and client.user.is_active
            ):
                client.user.is_active = False

                client.user.save(
                    update_fields=["is_active"]
                )

                deactivated_count += 1

        # =====================================================
        # 3. CREATE RENEWAL REMINDERS
        # =====================================================

        reminder_days_list = (10, 5, 1)
        created_count = 0

        active_subscriptions = (
            Subscription.objects
            .filter(
                status="active",
                start_date__lte=today,
                end_date__gte=today,
            )
            .select_related("client__user")
        )

        for subscription in active_subscriptions.iterator():

            days_remaining = (
                subscription.end_date - today
            ).days

            if days_remaining not in reminder_days_list:
                continue

            if days_remaining == 10:
                title = "Subscription expires in 10 days"

            elif days_remaining == 5:
                title = "Subscription expires in 5 days"

            else:
                title = "Subscription expires tomorrow"

            client_name = (
                subscription.client.user.get_full_name()
                or subscription.client.user.username
            )

            message = (
                f"Hi {client_name}, your "
                f"{subscription.plan_name} subscription "
                f"expires on "
                f"{subscription.end_date:%d %B %Y}. "
                "Please contact your trainer to renew it."
            )

            notification, created = (
                SubscriptionNotification.objects.get_or_create(
                    subscription=subscription,
                    reminder_days=days_remaining,
                    defaults={
                        "title": title,
                        "message": message,
                    },
                )
            )

            if created:
                created_count += 1

        # =====================================================
        # 4. REPORT RESULTS
        # =====================================================

        self.stdout.write(
            self.style.SUCCESS(
                "Subscription processing complete.\n"
                f"Expired subscriptions: {expired_count}\n"
                f"Client accounts deactivated: {deactivated_count}\n"
                f"New renewal reminders: {created_count}"
            )
        )
