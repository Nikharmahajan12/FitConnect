
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from core.models import ClientProfile, Subscription


class _RollbackTest(Exception):
    pass


try:
    with transaction.atomic():

        # Create a temporary client account.
        username = f"expiry_test_{uuid4().hex[:8]}"

        user = User.objects.create_user(
            username=username,
            password="Temporary-Test-12345",
        )

        client, _ = ClientProfile.objects.get_or_create(
            user=user,
            defaults={"gender": "other"},
        )

        today = timezone.localdate()

        # Create a subscription that expired yesterday.
        subscription = Subscription.objects.create(
            client=client,
            plan_name="Temporary Expiry Test",
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=1),
            status="active",
        )

        # Run the actual management command.
        call_command("process_subscription_reminders")

        # Reload records to check their updated database state.
        user.refresh_from_db()
        subscription.refresh_from_db()

        print("Test client active:", user.is_active)
        print("Subscription status:", subscription.status)

        assert user.is_active is False, (
            "FAIL: The expired client's account was not deactivated."
        )

        assert subscription.status == "expired", (
            "FAIL: The subscription was not marked as expired."
        )

        print("PASS: Expired subscription processed successfully.")

        # Roll back the temporary records and database changes.
        raise _RollbackTest()

except _RollbackTest:
    print("Temporary test records and database changes were rolled back.")
