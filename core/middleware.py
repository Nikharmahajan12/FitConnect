
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.utils import timezone

from core.models import ClientProfile, Subscription


class ClientSubscriptionAccessMiddleware:
    """
    Protect client dashboard pages when the client's
    latest subscription has expired.

    The public website home page remains accessible.
    """

    CLIENT_VIEW_NAMES = {
        "home",
        "schedule",
        "messages",
        "mark_attendance",
        "save_lifestyle",
        "progress",
        "profile",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        match = getattr(request, "resolver_match", None)

        if (
            not match
            or match.namespace != "core"
            or match.url_name not in self.CLIENT_VIEW_NAMES
        ):
            return None

        # An unauthenticated visitor cannot open client pages.
        # Send them to the public website home page.
        if not request.user.is_authenticated:
            return redirect("core:website_home")

        # This middleware only applies to client accounts.
        try:
            client = ClientProfile.objects.get(user=request.user)
        except ClientProfile.DoesNotExist:
            return None

        today = timezone.localdate()

        # A subscription is valid through its end date.
        has_valid_subscription = Subscription.objects.filter(
            client=client,
            status="active",
            start_date__lte=today,
            end_date__gte=today,
        ).exists()

        # Find the client's most recent subscription.
        latest_subscription = (
            Subscription.objects
            .filter(client=client)
            .order_by("-start_date", "-created_at")
            .first()
        )

        # Expire any active subscription that has ended.
        Subscription.objects.filter(
            client=client,
            status="active",
            end_date__lt=today,
        ).update(
            status="expired",
            updated_at=timezone.now(),
        )

        # Deactivate only if a subscription has ended and
        # there is no other currently valid subscription.
        if (
            latest_subscription
            and latest_subscription.end_date < today
            and not has_valid_subscription
        ):
            if request.user.is_active:
                request.user.is_active = False
                request.user.save(update_fields=["is_active"])

            logout(request)
            return redirect("core:website_home")

        # Never automatically reactivate an inactive account.
        if not request.user.is_active:
            logout(request)
            return redirect("core:website_home")

        return None
