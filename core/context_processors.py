
from django.utils import timezone

from core.models import (
    ClientProfile,
    SubscriptionNotification,
    TrainingPlanNotification,
)


def client_subscription_notifications(request):
    context = {
        "client_subscription_notifications": [],
        "unread_client_notification_count": 0,
    }

    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        return context

    try:
        client = user.client_profile
    except ClientProfile.DoesNotExist:
        return context

    today = timezone.localdate()

    # Subscription reminders
    subscription_notifications = (
        SubscriptionNotification.objects.filter(
            subscription__client=client,
            subscription__status="active",
            subscription__start_date__lte=today,
            subscription__end_date__gte=today,
        )
        .select_related("subscription")
        .order_by("-created_at")
    )

    # Workout and nutrition notifications
    training_notifications = (
        TrainingPlanNotification.objects.filter(
            client=client,
        )
        .select_related("training_plan")
        .order_by("-created_at")
    )

    # Combine notifications while identifying their types
    combined = []

    for notification in subscription_notifications[:8]:
        combined.append({
            "notification": notification,
            "notification_type": "subscription",
        })

    for notification in training_notifications[:8]:
        combined.append({
            "notification": notification,
            "notification_type": "training",
        })

    combined.sort(
        key=lambda item: item["notification"].created_at,
        reverse=True,
    )

    context["client_subscription_notifications"] = combined[:8]

    context["unread_client_notification_count"] = (
        subscription_notifications.filter(is_read=False).count()
        + training_notifications.filter(is_read=False).count()
    )

    return context
