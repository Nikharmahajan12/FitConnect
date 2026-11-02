from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages as django_messages
from core.models import Subscription, SubscriptionNotification
from django.contrib.auth.models import User
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.http import JsonResponse , HttpResponse
from .models import (
    ClientProfile,
    DailyLog,
    TrainingPlan,
    Query,
    Subscription,
    BodyMeasurement,
    BodyCompositionTest,
    DailyStepCount,
    TrainingPlanNotification
)
from django.utils import timezone
from datetime import timedelta, datetime
import calendar
from django.contrib.auth.decorators import login_required
from io import BytesIO
from decimal import Decimal, InvalidOperation
from decimal import Decimal, InvalidOperation
from datetime import date   
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from functools import wraps
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone


def active_subscription_required(view_func):

    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):

        # Find the logged-in client's profile
        client = ClientProfile.objects.filter(
            user=request.user
        ).first()

        # Trainers and other users should not be logged out
        if client is None:
            return view_func(request, *args, **kwargs)

        today = timezone.localdate()

        # Check whether the client has a valid subscription
        has_valid_subscription = Subscription.objects.filter(
            client=client,
            status="active",
            start_date__lte=today,
            end_date__gte=today
        ).exists()

        # Log out clients who have no valid subscription
        if not has_valid_subscription:
            logout(request)
            return redirect("/website/")

        return view_func(request, *args, **kwargs)

    return wrapper

@login_required
def trainer_connect_client(request):
    trainer = request.user.trainer_profile

    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        if not username:
            django_messages.error(
                request,
                "Please enter the client's username."
            )
            return redirect("core:trainer_clients")

        try:
            client = ClientProfile.objects.select_related(
                "user",
                "trainer"
            ).get(
                user__username__iexact=username
            )
        except ClientProfile.DoesNotExist:
            django_messages.error(
                request,
                "No registered client was found with that username."
            )
            return redirect("core:trainer_clients")

        if client.trainer == trainer:
            django_messages.info(
                request,
                f"{client.user.username} is already connected to you."
            )
            return redirect("core:trainer_clients")

        if client.trainer is not None:
            django_messages.error(
                request,
                "This client is already connected to another trainer."
            )
            return redirect("core:trainer_clients")

        client.trainer = trainer
        client.save(update_fields=["trainer"])

        django_messages.success(
            request,
            f"{client.user.username} has been connected to your trainer account."
        )

    return redirect("core:trainer_clients")
# =============================================================
# CLIENT DASHBOARD
# =============================================================



@active_subscription_required
def home(request):
    # Get the currently logged-in client's profile
    client = get_object_or_404(
        ClientProfile,
        user=request.user
    )

    # =========================================================
    # DAILY STEP COUNTER FORM
    # =========================================================
    step_count_error = ""

    if (
        request.method == "POST"
        and request.POST.get("action") == "save_daily_steps"
    ):
        try:
            step_date = date.fromisoformat(
                request.POST.get("step_date", "")
            )
            steps = int(request.POST.get("steps", ""))
            today_date = timezone.localdate()

            if step_date > today_date:
                raise ValueError("Future dates are not allowed.")

            if steps < 0 or steps > 1000000:
                raise ValueError("Invalid step count.")

            DailyStepCount.objects.update_or_create(
                client=client,
                date=step_date,
                defaults={"steps": steps}
            )

            return redirect("core:home")

        except (ValueError, TypeError):
            step_count_error = (
                "Please enter a valid date and a step count "
                "between 0 and 1,000,000. Future dates are not allowed."
            )

    # =========================================================
    # BODY COMPOSITION TEST FORM
    # =========================================================
    body_composition_error = ""

    if (
        request.method == "POST"
        and request.POST.get("action") == "save_body_composition"
    ):
        try:
            test_date = date.fromisoformat(
                request.POST.get("test_date", "")
            )
            body_fat = Decimal(
                request.POST.get("body_fat_percent", "")
            )
            muscle_mass = Decimal(
                request.POST.get("muscle_mass_kg", "")
            )
            body_water = Decimal(
                request.POST.get("body_water_percent", "")
            )
            bmi_value = Decimal(
                request.POST.get("bmi", "")
            )

            today_date = timezone.localdate()

            if test_date > today_date:
                raise ValueError("Future dates are not allowed.")

            if not (Decimal("0") <= body_fat <= Decimal("100")):
                raise ValueError("Invalid body fat percentage.")

            if muscle_mass <= 0:
                raise ValueError("Muscle mass must be greater than zero.")

            if not (Decimal("0") <= body_water <= Decimal("100")):
                raise ValueError("Invalid body water percentage.")

            if bmi_value <= 0:
                raise ValueError("BMI must be greater than zero.")

            BodyCompositionTest.objects.create(
                client=client,
                test_date=test_date,
                body_fat_percent=body_fat,
                muscle_mass_kg=muscle_mass,
                body_water_percent=body_water,
                bmi=bmi_value,
                notes=request.POST.get("notes", "").strip()
            )

            return redirect("core:home")

        except (ValueError, InvalidOperation, TypeError):
            body_composition_error = (
                "Please enter a valid test date and numeric values. "
                "Body fat and body water must be between 0 and 100; "
                "muscle mass and BMI must be greater than zero."
            )

    today = timezone.localdate()

    # =========================================================
    # DAILY STEP COUNTER DATA
    # =========================================================
    today_step_count = DailyStepCount.objects.filter(
        client=client,
        date=today
    ).first()

    today_steps = (
        today_step_count.steps
        if today_step_count
        else 0
    )

    step_goal = 10000

    step_progress = min(
        round((today_steps / step_goal) * 100),
        100
    )

    recent_step_counts = DailyStepCount.objects.filter(
        client=client
    )[:3]

    # =========================================================
    # TODAY'S LOG
    # =========================================================
    daily_log, created = DailyLog.objects.get_or_create(
        client=client,
        date=today
    )

    # =========================================================
    # LAST 7 DAYS
    # =========================================================
    week_logs = DailyLog.objects.filter(
        client=client,
        date__range=[
            today - timedelta(days=6),
            today
        ]
    )

    # =========================================================
    # WEEKLY TREND DATA
    # =========================================================
    nutrition_map = {
        "poor": 1,
        "average": 2,
        "good": 3,
        "excellent": 4,
    }

    trend_data = []

    for i in range(7):
        log_date = today - timedelta(days=6 - i)

        log = week_logs.filter(
            date=log_date
        ).first()

        nutrition_value = None

        if log and log.nutrition:
            nutrition_value = nutrition_map.get(log.nutrition)

        trend_data.append({
            "day": log_date.strftime("%a"),
            "sleep": (
                float(log.sleep_hours)
                if log and log.sleep_hours is not None
                else None
            ),
            "water": (
                float(log.water_liters)
                if log and log.water_liters is not None
                else None
            ),
            "nutrition": nutrition_value,
        })

    # =========================================================
    # SLEEP
    # =========================================================
    sleep_logs = [
        log.sleep_hours
        for log in week_logs
        if log.sleep_hours is not None
    ]

    avg_sleep = (
        sum(sleep_logs) / len(sleep_logs)
        if sleep_logs
        else None
    )

    # =========================================================
    # WATER
    # =========================================================
    water_logs = [
        log.water_liters
        for log in week_logs
        if log.water_liters is not None
    ]

    avg_water = (
        sum(water_logs) / len(water_logs)
        if water_logs
        else None
    )

    # =========================================================
    # CALORIES
    # =========================================================
    calorie_logs = [
        log.calories
        for log in week_logs
        if log.calories is not None
    ]

    avg_calories = (
        sum(calorie_logs) / len(calorie_logs)
        if calorie_logs
        else None
    )

    # =========================================================
    # PROTEIN
    # =========================================================
    protein_logs = [
        log.protein
        for log in week_logs
        if log.protein is not None
    ]

    avg_protein = (
        sum(protein_logs) / len(protein_logs)
        if protein_logs
        else None
    )

    # =========================================================
    # CARBOHYDRATES
    # =========================================================
    carb_logs = [
        log.carbs
        for log in week_logs
        if log.carbs is not None
    ]

    avg_carbs = (
        sum(carb_logs) / len(carb_logs)
        if carb_logs
        else None
    )

    # =========================================================
    # FIBER
    # =========================================================
    fiber_logs = [
        log.fiber
        for log in week_logs
        if log.fiber is not None
    ]

    avg_fiber = (
        sum(fiber_logs) / len(fiber_logs)
        if fiber_logs
        else None
    )

    # =========================================================
    # WEEKLY ATTENDANCE
    # =========================================================
    attendance_count = week_logs.filter(
        attendance=True
    ).count()

    # =========================================================
    # WEEKLY NUTRITION CONSISTENCY
    # =========================================================
    nutrition_logs = [
        log.nutrition
        for log in week_logs
        if log.nutrition
    ]

    good_nutrition_days = sum(
        1
        for nutrition in nutrition_logs
        if nutrition in ["good", "excellent"]
    )

    nutrition_days = len(nutrition_logs)

    if nutrition_days == 0:
        nutrition_consistency = None
    elif good_nutrition_days >= 6:
        nutrition_consistency = "Excellent"
    elif good_nutrition_days >= 4:
        nutrition_consistency = "Good"
    elif good_nutrition_days >= 2:
        nutrition_consistency = "Needs Improvement"
    else:
        nutrition_consistency = "Poor"

    # =========================================================
    # BODY COMPOSITION RESULTS
    # =========================================================
    latest_body_composition = (
        BodyCompositionTest.objects.filter(
            client=client
        ).order_by("-test_date").first()
    )

    recent_body_composition_tests = (
        BodyCompositionTest.objects.filter(
            client=client
        ).order_by("-test_date")[:3]
    )
    
    
    # =========================================================
    # SUBSCRIPTION RENEWAL NOTIFICATIONS
    # =========================================================

    subscription_notifications = (
        SubscriptionNotification.objects.filter(
            subscription__client=client,
            is_read=False,
        )
        .select_related("subscription")
        .order_by("-created_at")[:10]
    )

    unread_subscription_notification_count = (
        SubscriptionNotification.objects.filter(
            subscription__client=client,
            is_read=False,
        ).count()
    )

    # Find the currently valid subscription
    active_subscription = (
        Subscription.objects.filter(
            client=client,
            status="active",
            start_date__lte=today,
            end_date__gte=today,
        )
        .order_by("-end_date")
        .first()
    )

    days_until_expiry = None
    subscription_expiry_alert = False

    if active_subscription:
        days_until_expiry = (
            active_subscription.end_date - today
        ).days

        if days_until_expiry in (5, 2, 1, 0):
            subscription_expiry_alert = True


    # =========================================================
    # CONTEXT
    # =========================================================
    context = {
        "daily_log": daily_log,

        "avg_sleep": avg_sleep,
        "avg_water": avg_water,
        "avg_calories": avg_calories,
        "avg_protein": avg_protein,
        "avg_carbs": avg_carbs,
        "avg_fiber": avg_fiber,

        "attendance_count": attendance_count,
        "nutrition_consistency": nutrition_consistency,
        "nutrition_days": nutrition_days,
        "trend_data": trend_data,

        # BODY COMPOSITION
        "latest_body_composition": latest_body_composition,
        "recent_body_composition_tests": recent_body_composition_tests,
        "body_composition_error": body_composition_error,

        # DAILY STEP COUNTER
        "today_step_count": today_step_count,
        "today_steps": today_steps,
        "step_goal": step_goal,
        "step_progress": step_progress,
        "recent_step_counts": recent_step_counts,
        "step_count_error": step_count_error,
        
                # SUBSCRIPTION NOTIFICATIONS
        "subscription_notifications": subscription_notifications,
        "unread_subscription_notification_count": (
            unread_subscription_notification_count
        ),
        "active_subscription": active_subscription,
        "days_until_expiry": days_until_expiry,
        "subscription_expiry_alert": subscription_expiry_alert,
    }

    return render(
        request,
        "core/home.html",
        context
    )


# =============================================================
# CLIENT MARK ATTENDANCE
# =============================================================

# =============================================================
# CLIENT MARK ATTENDANCE
# =============================================================

@login_required
def mark_attendance(request):
    if request.method != "POST":
        return redirect("core:home")

    client = get_object_or_404(
        ClientProfile,
        user=request.user
    )

    today = timezone.localdate()

    daily_log, created = DailyLog.objects.get_or_create(
        client=client,
        date=today
    )

    daily_log.client_attendance_marked = True
    daily_log.attendance = True
    daily_log.attendance_marked_by = "client"

    daily_log.save()

    print("\n===== CLIENT ATTENDANCE DEBUG =====")
    print("Logged-in user:", request.user.username)
    print("Client ID:", client.id)
    print("Date:", daily_log.date)
    print("Client marked:", daily_log.client_attendance_marked)
    print("Trainer marked:", daily_log.trainer_attendance_marked)
    print("==================================\n")

    return redirect("core:home")

# =============================================================
# SAVE LIFESTYLE DATA
# =============================================================

def save_lifestyle(request):

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False
            },
            status=405
        )

    # ---------------------------------------------------------
    # TEMPORARY DEVELOPMENT USER
    # ---------------------------------------------------------

    user = User.objects.get(
        username="testclient"
    )

    client = ClientProfile.objects.get(
        user=user
    )

    today = timezone.localdate()

    daily_log, created = DailyLog.objects.get_or_create(
        client=client,
        date=today
    )

    # ---------------------------------------------------------
    # Sleep
    # ---------------------------------------------------------

    daily_log.sleep_hours = (
        request.POST.get("sleep") or None
    )

    # ---------------------------------------------------------
    # Water
    # ---------------------------------------------------------

    daily_log.water_liters = (
        request.POST.get("water") or None
    )

    # ---------------------------------------------------------
    # Calories
    # ---------------------------------------------------------

    daily_log.calories = (
        request.POST.get("calories") or None
    )

    # ---------------------------------------------------------
    # Protein
    # ---------------------------------------------------------

    daily_log.protein = (
        request.POST.get("protein") or None
    )

    # ---------------------------------------------------------
    # Carbohydrates
    # ---------------------------------------------------------

    daily_log.carbs = (
        request.POST.get("carbs") or None
    )

    # ---------------------------------------------------------
    # Fiber
    # ---------------------------------------------------------

    daily_log.fiber = (
        request.POST.get("fiber") or None
    )

    # ---------------------------------------------------------
    # Nutrition quality
    # ---------------------------------------------------------

    daily_log.nutrition = request.POST.get(
        "nutrition",
        ""
    )

    # ---------------------------------------------------------
    # Save
    # ---------------------------------------------------------

    daily_log.save()

    return JsonResponse({
        "success": True
    })
    
# =============================================================
# CLIENT PROGRESS
# =============================================================

@login_required
def progress(request):

    client = get_object_or_404(
        ClientProfile,
        user=request.user
    )

    today = timezone.localdate()

    # Last 30 days
    period_start = today - timedelta(days=29)

    logs = list(
        DailyLog.objects
        .filter(
            client=client,
            date__range=[period_start, today]
        )
        .order_by("date")
    )

    # =========================================================
    # ATTENDANCE
    # =========================================================

    tracked_days = len(logs)

    attendance_count = sum(
        1
        for log in logs
        if log.attendance
    )

    attendance_rate = (
        round(
            (attendance_count / tracked_days) * 100
        )
        if tracked_days
        else None
    )

    # =========================================================
    # SLEEP
    # =========================================================

    sleep_values = [
        float(log.sleep_hours)
        for log in logs
        if log.sleep_hours is not None
    ]

    avg_sleep = (
        sum(sleep_values) / len(sleep_values)
        if sleep_values
        else None
    )

    # =========================================================
    # WATER
    # =========================================================

    water_values = [
        float(log.water_liters)
        for log in logs
        if log.water_liters is not None
    ]

    avg_water = (
        sum(water_values) / len(water_values)
        if water_values
        else None
    )

    # =========================================================
    # NUTRITION
    # =========================================================

    nutrition_map = {
        "poor": 1,
        "average": 2,
        "good": 3,
        "excellent": 4,
    }

    nutrition_values = [
        nutrition_map[log.nutrition]
        for log in logs
        if log.nutrition in nutrition_map
    ]

    nutrition_days = len(nutrition_values)

    good_nutrition_days = sum(
        1
        for value in nutrition_values
        if value >= 3
    )

    if not nutrition_values:
        nutrition_consistency = None

    elif good_nutrition_days >= 6:
        nutrition_consistency = "Excellent"

    elif good_nutrition_days >= 4:
        nutrition_consistency = "Good"

    elif good_nutrition_days >= 2:
        nutrition_consistency = "Needs Improvement"

    else:
        nutrition_consistency = "Poor"

    # =========================================================
    # NUTRITION AVERAGES
    # =========================================================

    calorie_values = [
        float(log.calories)
        for log in logs
        if log.calories is not None
    ]

    protein_values = [
        float(log.protein)
        for log in logs
        if log.protein is not None
    ]

    carb_values = [
        float(log.carbs)
        for log in logs
        if log.carbs is not None
    ]

    fiber_values = [
        float(log.fiber)
        for log in logs
        if log.fiber is not None
    ]

    avg_calories = (
        sum(calorie_values) / len(calorie_values)
        if calorie_values
        else None
    )

    avg_protein = (
        sum(protein_values) / len(protein_values)
        if protein_values
        else None
    )

    avg_carbs = (
        sum(carb_values) / len(carb_values)
        if carb_values
        else None
    )

    avg_fiber = (
        sum(fiber_values) / len(fiber_values)
        if fiber_values
        else None
    )

    # =========================================================
    # GRAPH DATA
    # =========================================================

    trend_data = []

    for log in logs:

        trend_data.append({
            "date": log.date.strftime("%d %b"),

            "sleep": (
                float(log.sleep_hours)
                if log.sleep_hours is not None
                else None
            ),

            "water": (
                float(log.water_liters)
                if log.water_liters is not None
                else None
            ),

            "nutrition": (
                nutrition_map.get(log.nutrition)
                if log.nutrition
                else None
            ),
        })

    # =========================================================
    # RECENT ACTIVITY
    # =========================================================

    recent_logs = list(
        reversed(logs[-7:])
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "client": client,

        "today": today,

        "period_start": period_start,

        "period_end": today,

        "tracked_days": tracked_days,

        "attendance_count": attendance_count,

        "attendance_rate": attendance_rate,

        "avg_sleep": avg_sleep,

        "avg_water": avg_water,

        "nutrition_consistency":
            nutrition_consistency,

        "nutrition_days":
            nutrition_days,

        "avg_calories":
            avg_calories,

        "avg_protein":
            avg_protein,

        "avg_carbs":
            avg_carbs,

        "avg_fiber":
            avg_fiber,

        "trend_data":
            trend_data,

        "recent_logs":
            recent_logs,
    }

    return render(
        request,
        "core/progress.html",
        context
    )


# =============================================================
# CLIENT SCHEDULE
# =============================================================
@login_required
def schedule(request):

    client = get_object_or_404(
        ClientProfile,
        user=request.user
    )

    today = timezone.localdate()

    # -----------------------------------------
    # SELECTED DATE
    # -----------------------------------------

    selected_date_string = request.GET.get("date")

    if selected_date_string:
        try:
            selected_date = datetime.strptime(
                selected_date_string,
                "%Y-%m-%d"
            ).date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    # -----------------------------------------
    # CURRENT WEEK
    # Monday → Sunday
    # -----------------------------------------

    week_start = selected_date - timedelta(
        days=selected_date.weekday()
    )

    week_days = []

    for i in range(7):

        day = week_start + timedelta(days=i)

        week_days.append({
            "date": day,
            "name": day.strftime("%a"),
            "number": day.day,
            "is_today": day == today,
            "is_selected": day == selected_date,
        })

    week_end = week_start + timedelta(days=6)

    # -----------------------------------------
    # PLANS FOR SELECTED DAY
    # -----------------------------------------

    selected_day_plans = (
        TrainingPlan.objects
        .filter(
            client=client,
            date=selected_date
        )
        .order_by("plan_type", "id")
    )

    # -----------------------------------------
    # UPCOMING PLANS
    # -----------------------------------------

    upcoming_plans = (
        TrainingPlan.objects
        .filter(
            client=client,
            date__gt=selected_date
        )
        .order_by("date", "id")
    )

    return render(
        request,
        "core/schedule.html",
        {
            "client": client,
            "today": today,
            "selected_date": selected_date,
            "week_start": week_start,
            "week_end": week_end,
            "week_days": week_days,
            "selected_day_plans": selected_day_plans,
            "upcoming_plans": upcoming_plans,
        }
    )    
    # =============================================================
# CLIENT QUERIES
# =============================================================

def messages(request):

    # ---------------------------------------------------------
    # TEMPORARY DEVELOPMENT USER
    # ---------------------------------------------------------

    user = User.objects.get(
        username="testclient"
    )

    client = ClientProfile.objects.get(
        user=user
    )

    # =========================================================
    # SUBMIT NEW QUERY
    # =========================================================

    if request.method == "POST":

        subject = request.POST.get(
            "subject"
        )

        category = request.POST.get(
            "category"
        )

        message = request.POST.get(
            "message"
        )

        if subject and category and message:

            Query.objects.create(
                client=client,
                subject=subject,
                category=category,
                message=message
            )

        return redirect(
            "core:messages"
        )

    # =========================================================
    # GET CLIENT'S PREVIOUS QUERIES
    # =========================================================

    queries = Query.objects.filter(
        client=client
    )

    return render(
        request,
        "core/messages.html",
        {
            "queries": queries
        }
    )


# =============================================================
# TRAINER DASHBOARD
# =============================================================


# =============================================================
# TRAINER DASHBOARD
# =============================================================

@login_required
def trainer_dashboard(request):

    # ---------------------------------------------------------
    # GET LOGGED-IN TRAINER
    # ---------------------------------------------------------

    trainer = get_object_or_404(
        TrainerProfile,
        user=request.user
    )

    # ---------------------------------------------------------
    # GET TRAINER'S CLIENTS
    # ---------------------------------------------------------

    clients = trainer.clients.select_related("user").all()

    # ---------------------------------------------------------
    # TODAY
    # ---------------------------------------------------------

    today = timezone.localdate()

    # ---------------------------------------------------------
    # SELECTED DATE
    # ---------------------------------------------------------

    selected_date_string = request.GET.get("date")

    if selected_date_string:
        try:
            selected_date = datetime.strptime(
                selected_date_string,
                "%Y-%m-%d"
            ).date()
        except (ValueError, TypeError):
            selected_date = today
    else:
        selected_date = today

    # Never allow future dates
    if selected_date > today:
        selected_date = today

    # ---------------------------------------------------------
    # PREVIOUS / NEXT DAY
    # ---------------------------------------------------------

    previous_date = selected_date - timedelta(days=1)

    next_date = (
        selected_date + timedelta(days=1)
        if selected_date < today
        else None
    )

    # ---------------------------------------------------------
    # CALENDAR DATA
    # ---------------------------------------------------------

    calendar_year = selected_date.year
    calendar_month = selected_date.month

    cal = calendar.Calendar(firstweekday=0)

    calendar_weeks = cal.monthdatescalendar(
        calendar_year,
        calendar_month
    )

    # ---------------------------------------------------------
    # PREVIOUS MONTH
    # ---------------------------------------------------------

    if calendar_month == 1:
        previous_month_year = calendar_year - 1
        previous_month = 12
    else:
        previous_month_year = calendar_year
        previous_month = calendar_month - 1

    previous_month_date = (
        f"{previous_month_year:04d}-"
        f"{previous_month:02d}-01"
    )

    # ---------------------------------------------------------
    # NEXT MONTH
    # ---------------------------------------------------------

    current_month_start = today.replace(day=1)
    selected_month_start = selected_date.replace(day=1)

    if selected_month_start < current_month_start:

        if calendar_month == 12:
            next_month_year = calendar_year + 1
            next_month = 1
        else:
            next_month_year = calendar_year
            next_month = calendar_month + 1

        next_month_start = datetime(
            next_month_year,
            next_month,
            1
        ).date()

        if next_month_start <= current_month_start:
            next_month_date = (
                f"{next_month_year:04d}-"
                f"{next_month:02d}-01"
            )
        else:
            next_month_date = None

    else:
        next_month_date = None

    # ---------------------------------------------------------
    # CLIENT ATTENDANCE
    # ---------------------------------------------------------

    client_data = []

    # Fetch all attendance records for the selected date
    # in one query instead of querying inside the loop.
    daily_logs = DailyLog.objects.filter(
        client__in=clients,
        date=selected_date
    ).select_related(
        "client__user"
    )

    # Map each client's attendance record by client ID
    logs_by_client = {
        log.client_id: log
        for log in daily_logs
    }

    for client in clients:

        daily_log = logs_by_client.get(client.id)

        # -----------------------------------------------------
        # DEFAULT VALUES
        # -----------------------------------------------------

        attendance_marked = False
        attendance_marked_by = None
        client_marked = False
        trainer_marked = False

        # -----------------------------------------------------
        # READ ATTENDANCE RECORD
        # -----------------------------------------------------

        if daily_log:

            client_marked = bool(
                daily_log.client_attendance_marked
            )

            trainer_marked = bool(
                daily_log.trainer_attendance_marked
            )

            attendance_marked_by = (
                daily_log.attendance_marked_by
            )

            # Backward compatibility for older records
            # that used attendance_marked_by only.
            if attendance_marked_by == "client":
                client_marked = True

            elif attendance_marked_by == "trainer":
                trainer_marked = True

            # Overall attendance is true if either party
            # marked it or an older record has attendance=True.
            attendance_marked = (
                bool(daily_log.attendance)
                or client_marked
                or trainer_marked
            )

        # -----------------------------------------------------
        # MARKED-BY DISPLAY
        # -----------------------------------------------------

        if client_marked and trainer_marked:
            attendance_marked_by_display = "Client & Trainer"

        elif client_marked:
            attendance_marked_by_display = "Client"

        elif trainer_marked:
            attendance_marked_by_display = "Trainer"

        else:
            attendance_marked_by_display = None

        # -----------------------------------------------------
        # ATTENDANCE STATUS
        # -----------------------------------------------------

        if client_marked and trainer_marked:
            attendance_status = "Client & Trainer marked"

        elif client_marked:
            attendance_status = "Client marked"

        elif trainer_marked:
            attendance_status = "Trainer marked"

        elif attendance_marked:
            attendance_status = "Present (legacy record)"

        else:
            attendance_status = "Not marked"

        # -----------------------------------------------------
        # TRAINER ACTION
        # Only today's attendance can be marked.
        # Client marking must not block the trainer.
        # -----------------------------------------------------

        can_mark_attendance = (
            selected_date == today
            and not trainer_marked
        )

        # -----------------------------------------------------
        # TEMPLATE DATA
        # -----------------------------------------------------

        client_data.append({
            "client": client,
            "daily_log": daily_log,
            "attendance": attendance_marked,
            "client_marked": client_marked,
            "trainer_marked": trainer_marked,
            "attendance_marked_by": attendance_marked_by,
            "attendance_marked_by_display":
                attendance_marked_by_display,
            "attendance_status": attendance_status,
            "can_mark_attendance": can_mark_attendance,
        })

    # ---------------------------------------------------------
    # MEMBERSHIP STATUS
    # ---------------------------------------------------------

    for item in client_data:

        client = item["client"]

        if client.membership_end:
            days_remaining = (
                client.membership_end - today
            ).days
        else:
            days_remaining = None

        item["days_remaining"] = days_remaining

    # ---------------------------------------------------------
    # PENDING QUERIES
    # ---------------------------------------------------------

    pending_queries = Query.objects.filter(
        client__trainer=trainer,
        status="pending"
    ).select_related(
        "client__user"
    ).order_by(
        "-created_at"
    )

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {
        "today": today,
        "selected_date": selected_date,
        "previous_date": previous_date,
        "next_date": next_date,
        "calendar_year": calendar_year,
        "calendar_month": calendar_month,
        "calendar_weeks": calendar_weeks,
        "previous_month_date": previous_month_date,
        "next_month_date": next_month_date,
        "clients": client_data,
        "pending_queries": pending_queries,
        "pending_query_count": pending_queries.count(),
    }

    return render(
        request,
        "core/trainer_dashboard.html",
        context
    )

# =============================================================
# =============================================================
# TRAINER MARK ATTENDANCE

@login_required
def trainer_mark_attendance(request, client_id):

    # Allow only POST requests
    if request.method != "POST":
        return redirect("core:trainer_dashboard")

    # Get the logged-in trainer
    trainer = get_object_or_404(
        TrainerProfile,
        user=request.user
    )

    # Allow the trainer to mark only their assigned clients
    client = get_object_or_404(
        ClientProfile,
        id=client_id,
        trainer=trainer
    )

    # Use today's local date
    today = timezone.localdate()

    # Get or create today's attendance record
    log, created = DailyLog.objects.get_or_create(
        client=client,
        date=today
    )

    # Mark the trainer's attendance
    log.trainer_attendance_marked = True
    log.attendance = True

    # Preserve existing client attendance
    if log.client_attendance_marked:
        log.attendance_marked_by = "client"
    else:
        log.attendance_marked_by = "trainer"

    # Save all attendance fields
    log.save(update_fields=[
        "trainer_attendance_marked",
        "client_attendance_marked",
        "attendance",
        "attendance_marked_by",
    ])

    # Verify the saved record
    log.refresh_from_db()

    print("\n===== TRAINER ATTENDANCE DEBUG =====")
    print("View called: YES")
    print("Trainer:", request.user.username)
    print("Client:", client.user.username)
    print("Date:", log.date)
    print("Attendance:", log.attendance)
    print("Client marked:", log.client_attendance_marked)
    print("Trainer marked:", log.trainer_attendance_marked)
    print("Legacy marker:", log.attendance_marked_by)
    print("====================================\n")

    # Return to today's trainer dashboard
    return redirect(
        f"/trainer/?date={today.strftime('%Y-%m-%d')}"
    )

# =============================================================
# TRAINER QUERY DETAIL
# =============================================================

# =============================================================
# TRAINER QUERY DETAIL
# =============================================================

@login_required
def trainer_query_detail(
    request,
    query_id
):

    # =========================================================
    # GET LOGGED-IN TRAINER
    # =========================================================

    trainer = request.user.trainer_profile

    # =========================================================
    # GET QUERY
    # =========================================================
    #
    # Important:
    # The trainer can only access queries belonging to
    # clients assigned to this trainer.
    #
    # =========================================================

    query = get_object_or_404(
        Query,
        id=query_id,
        client__trainer=trainer
    )

    # =========================================================
    # HANDLE POST ACTIONS
    # =========================================================

    if request.method == "POST":

        action = request.POST.get(
            "action",
            ""
        ).strip()

        # =====================================================
        # RESPOND TO QUERY
        # =====================================================

        if action == "respond":

            response = request.POST.get(
                "response",
                ""
            ).strip()

            # Do not save an empty response
            if response:

                query.response = response

                query.status = "answered"

                query.answered_at = timezone.now()

                query.save(
                    update_fields=[
                        "response",
                        "status",
                        "answered_at"
                    ]
                )

        # =====================================================
        # CLOSE QUERY
        # =====================================================

        elif action == "close":

            # A query can only be closed after
            # the trainer has answered it.

            if query.status == "answered":

                query.status = "closed"

                query.save(
                    update_fields=[
                        "status"
                    ]
                )

        # =====================================================
        # RETURN TO SAME QUERY
        # =====================================================

        return redirect(
            "core:trainer_query_detail",
            query_id=query.id
        )

    # =========================================================
    # PAGE
    # =========================================================

    return render(
        request,
        "core/trainer_query_detail.html",
        {
            "query": query,
        }
    )


# =============================================================
# TRAINER QUERIES
# =============================================================

@login_required    
def trainer_queries(request):

    trainer = request.user.trainer_profile

    queries = Query.objects.filter(
        client__trainer=trainer
    ).select_related(
        "client__user"
    )

    pending_queries = queries.filter(
        status="pending"
    )

    answered_queries = queries.filter(
        status="answered"
    )

    closed_queries = queries.filter(
        status="closed"
    )

    context = {
        "pending_queries": pending_queries,
        "answered_queries": answered_queries,
        "closed_queries": closed_queries,
    }

    return render(
        request,
        "core/trainer_queries.html",
        context
    )
# =============================================================
# TRAINER CLIENT LIST
# =============================================================

# =============================================================
# TRAINER CLIENT LIST
# =============================================================

@login_required
def trainer_clients(request):

    # ---------------------------------------------------------
    # GET LOGGED-IN TRAINER
    # ---------------------------------------------------------

    trainer = request.user.trainer_profile

    # ---------------------------------------------------------
    # GET ONLY THIS TRAINER'S CLIENTS
    # ---------------------------------------------------------

    clients = trainer.clients.select_related(
        "user"
    ).all()

    # ---------------------------------------------------------
    # TODAY
    # ---------------------------------------------------------

    today = timezone.localdate()

    # ---------------------------------------------------------
    # CLIENT DATA
    # ---------------------------------------------------------

    client_data = []

    # Count clients whose current legacy membership
    # has not ended yet.
    active_memberships_count = 0

    for client in clients:

        daily_log = DailyLog.objects.filter(
            client=client,
            date=today
        ).first()

        # -----------------------------------------------------
        # MEMBERSHIP
        # -----------------------------------------------------

        if client.membership_end:

            days_remaining = (
                client.membership_end - today
            ).days

            if days_remaining >= 0:
                active_memberships_count += 1

        else:

            days_remaining = None

      
        # -----------------------------------------------------
        # ATTENDANCE
        # -----------------------------------------------------

        attendance_marked = (
            daily_log.attendance
            if daily_log
            else False
        )

        client_marked = (
            daily_log.client_attendance_marked
            if daily_log
            else False
        )

        trainer_marked = (
            daily_log.trainer_attendance_marked
            if daily_log
            else False
        )

        # Backward compatibility with older records
        if daily_log:

            if daily_log.attendance_marked_by == "client":
                client_marked = True

            elif daily_log.attendance_marked_by == "trainer":
                trainer_marked = True

        # -----------------------------------------------------
        # ATTENDANCE STATUS
        # -----------------------------------------------------

        if client_marked and trainer_marked:

            attendance_marked_by = "Client & Trainer"
            attendance_status = "Client & Trainer marked"

        elif client_marked:

            attendance_marked_by = "Client"
            attendance_status = "Client marked"

        elif trainer_marked:

            attendance_marked_by = "Trainer"
            attendance_status = "Trainer marked"

        else:

            attendance_marked_by = None
            attendance_status = "Not marked"

        # -----------------------------------------------------
        # ADD CLIENT
        # -----------------------------------------------------

        client_data.append({

            "client": client,

            "daily_log": daily_log,

            "attendance": attendance_marked,

            "attendance_marked_by": attendance_marked_by,

            "attendance_status": attendance_status,

            "client_marked": client_marked,

            "trainer_marked": trainer_marked,

            "can_mark_attendance": not trainer_marked,

            "days_remaining": days_remaining,

        })


    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "core/trainer_clients.html",
        {
            "clients":
                client_data,

            "today":
                today,

            "active_memberships_count":
                active_memberships_count,
        }
    )


# =============================================================
# TRAINER CLIENT DETAIL
# =============================================================

# =============================================================
# TRAINER CLIENT DETAIL
# =============================================================

# =============================================================
# TRAINER CLIENT DETAIL
# =============================================================

# =============================================================
# TRAINER CLIENT DETAIL
# =============================================================


@login_required
def trainer_client_detail(request, client_id):

    # =========================================================
    # TRAINER AND CLIENT
    # =========================================================

    trainer = request.user.trainer_profile

    client = get_object_or_404(
        ClientProfile,
        id=client_id,
        trainer=trainer
    )

    today = timezone.localdate()

    detail_url = "core:trainer_client_detail"

    # =========================================================
    # MARK EXPIRED SUBSCRIPTIONS
    # =========================================================

    Subscription.objects.filter(
        client=client,
        status="active",
        end_date__lt=today
    ).update(
        status="expired",
        updated_at=timezone.now()
    )

    # =========================================================
    # HANDLE POST ACTIONS
    # =========================================================

    if request.method == "POST":

        action = request.POST.get("action", "").strip()

        # =====================================================
        # DEACTIVATE CLIENT ACCOUNT
        # This is separate from subscription deactivation.
        # =====================================================

        if action == "deactivate_client_account":

            if not client.user.is_active:
                django_messages.info(
                    request,
                    "This client account is already deactivated."
                )
            else:
                client.user.is_active = False
                client.user.save(update_fields=["is_active"])

                django_messages.success(
                    request,
                    "Client account deactivated successfully."
                )

            return redirect(detail_url, client_id=client.id)

        # =====================================================
        # ACTIVATE CLIENT ACCOUNT
        # =====================================================

        elif action == "activate_client_account":

            has_valid_subscription = Subscription.objects.filter(
                client=client,
                status="active",
                start_date__lte=today,
                end_date__gte=today
            ).exists()

            if not has_valid_subscription:
                django_messages.error(
                    request,
                    "This account cannot be activated yet. "
                    "Please activate a valid subscription first."
                )

            elif client.user.is_active:
                django_messages.info(
                    request,
                    "This client account is already active."
                )

            else:
                client.user.is_active = True
                client.user.save(update_fields=["is_active"])

                django_messages.success(
                    request,
                    "Client account activated successfully."
                )

            return redirect(detail_url, client_id=client.id)

        # =====================================================
        # CREATE NEW SUBSCRIPTION
        # =====================================================

        elif action == "create_subscription":

            plan_name = request.POST.get("plan_name", "").strip()
            amount = request.POST.get("amount", "").strip()
            start_date_string = request.POST.get(
                "start_date", ""
            ).strip()
            duration = request.POST.get("duration", "").strip()
            custom_days_string = request.POST.get(
                "custom_days", ""
            ).strip()

            if not plan_name:
                django_messages.error(
                    request,
                    "Please enter a subscription plan name."
                )
                return redirect(detail_url, client_id=client.id)

            # Validate start date
            if start_date_string:
                try:
                    start_date = datetime.strptime(
                        start_date_string,
                        "%Y-%m-%d"
                    ).date()
                except ValueError:
                    django_messages.error(
                        request,
                        "Please enter a valid start date."
                    )
                    return redirect(detail_url, client_id=client.id)
            else:
                start_date = today

            if not duration:
                django_messages.error(
                    request,
                    "Please select a subscription duration."
                )
                return redirect(detail_url, client_id=client.id)

            # Calculate subscription end date
            duration_map = {
                "1_month": 1,
                "3_months": 3,
                "6_months": 6,
                "1_year": 12,
            }

            if duration in duration_map:
                months = duration_map[duration]

                month = start_date.month - 1 + months
                year = start_date.year + month // 12
                month = month % 12 + 1

                day = min(
                    start_date.day,
                    calendar.monthrange(year, month)[1]
                )

                end_date = datetime(year, month, day).date()

            elif duration == "custom":
                try:
                    custom_days = int(custom_days_string)
                except (TypeError, ValueError):
                    django_messages.error(
                        request,
                        "Please enter a valid custom duration in days."
                    )
                    return redirect(detail_url, client_id=client.id)

                if custom_days <= 0:
                    django_messages.error(
                        request,
                        "Custom duration must be greater than zero."
                    )
                    return redirect(detail_url, client_id=client.id)

                end_date = start_date + timedelta(days=custom_days)

            else:
                django_messages.error(
                    request,
                    "Please select a valid subscription duration."
                )
                return redirect(detail_url, client_id=client.id)

            # Validate amount
            subscription_amount = None

            if amount:
                try:
                    subscription_amount = float(amount)
                except (TypeError, ValueError):
                    django_messages.error(
                        request,
                        "Please enter a valid subscription amount."
                    )
                    return redirect(detail_url, client_id=client.id)

                if subscription_amount < 0:
                    django_messages.error(
                        request,
                        "Subscription amount cannot be negative."
                    )
                    return redirect(detail_url, client_id=client.id)

            if end_date < start_date:
                django_messages.error(
                    request,
                    "The subscription end date must not precede "
                    "its start date."
                )
                return redirect(detail_url, client_id=client.id)

            if end_date < today:
                django_messages.error(
                    request,
                    "This subscription would already be expired. "
                    "Please choose a valid start date."
                )
                return redirect(detail_url, client_id=client.id)

            # Only one subscription should be active at a time.
            # Future-dated subscriptions won't grant access until
            # their start date because access checks use the dates.
            Subscription.objects.filter(
                client=client,
                status="active"
            ).update(
                status="inactive",
                updated_at=timezone.now()
            )

            new_subscription = Subscription.objects.create(
                client=client,
                plan_name=plan_name,
                amount=subscription_amount,
                start_date=start_date,
                end_date=end_date,
                status="active"
            )

            # Keep legacy membership fields synchronized only
            # when the new subscription is valid today.
            if start_date <= today <= end_date:
                client.membership_start = start_date
                client.membership_end = end_date
            else:
                client.membership_start = None
                client.membership_end = None

            client.save(
                update_fields=[
                    "membership_start",
                    "membership_end"
                ]
            )

            django_messages.success(
                request,
                f"{plan_name} subscription created for "
                f"{client.user.username}."
            )

            return redirect(detail_url, client_id=client.id)

        # =====================================================
        # DEACTIVATE SUBSCRIPTION
        # =====================================================

        elif action == "deactivate":

            subscription_id = request.POST.get(
                "subscription_id", ""
            ).strip()

            if not subscription_id:
                django_messages.error(
                    request,
                    "No subscription was selected."
                )
                return redirect(detail_url, client_id=client.id)

            subscription = get_object_or_404(
                Subscription,
                id=subscription_id,
                client=client
            )

            if subscription.status != "active":
                django_messages.info(
                    request,
                    "This subscription is not currently active."
                )
                return redirect(detail_url, client_id=client.id)

            # Deactivate only the selected subscription.
            subscription.status = "inactive"
            subscription.save(
                update_fields=["status", "updated_at"]
            )

            # Check whether another valid subscription remains.
            remaining_subscription = (
                Subscription.objects.filter(
                    client=client,
                    status="active",
                    start_date__lte=today,
                    end_date__gte=today
                )
                .order_by("-start_date", "-created_at")
                .first()
            )

            if remaining_subscription:
                client.membership_start = (
                    remaining_subscription.start_date
                )
                client.membership_end = (
                    remaining_subscription.end_date
                )
            else:
                client.membership_start = None
                client.membership_end = None

            client.save(
                update_fields=[
                    "membership_start",
                    "membership_end"
                ]
            )

            django_messages.success(
                request,
                "Subscription deactivated successfully. "
                "The client will need a valid subscription "
                "to access protected client pages."
            )

            # Keep the trainer on the client details page.
            return redirect(detail_url, client_id=client.id)

        # =====================================================
        # ACTIVATE AN EXISTING SUBSCRIPTION
        # =====================================================

        elif action == "activate":

            subscription_id = request.POST.get(
                "subscription_id", ""
            ).strip()

            if not subscription_id:
                django_messages.error(
                    request,
                    "No subscription was selected."
                )
                return redirect(detail_url, client_id=client.id)

            subscription = get_object_or_404(
                Subscription,
                id=subscription_id,
                client=client
            )

            if subscription.status == "active":
                django_messages.info(
                    request,
                    "This subscription is already active."
                )
                return redirect(detail_url, client_id=client.id)

            if subscription.end_date < today:
                subscription.status = "expired"
                subscription.save(
                    update_fields=["status", "updated_at"]
                )

                django_messages.error(
                    request,
                    "This subscription has expired. "
                    "Please create a new subscription."
                )
                return redirect(detail_url, client_id=client.id)

            if subscription.start_date > today:
                django_messages.error(
                    request,
                    "This subscription has not started yet. "
                    "It cannot be activated for access before "
                    "its start date."
                )
                return redirect(detail_url, client_id=client.id)

            # Deactivate other active subscriptions.
            Subscription.objects.filter(
                client=client,
                status="active"
            ).exclude(
                id=subscription.id
            ).update(
                status="inactive",
                updated_at=timezone.now()
            )

            subscription.status = "active"
            subscription.save(
                update_fields=["status", "updated_at"]
            )

            client.membership_start = subscription.start_date
            client.membership_end = subscription.end_date

            client.save(
                update_fields=[
                    "membership_start",
                    "membership_end"
                ]
            )

            django_messages.success(
                request,
                f"{subscription.plan_name} subscription activated."
            )

            return redirect(detail_url, client_id=client.id)

    # =========================================================
    # CURRENT VALID SUBSCRIPTION
    # =========================================================

    current_subscription = (
        Subscription.objects.filter(
            client=client,
            status="active",
            start_date__lte=today,
            end_date__gte=today
        )
        .order_by("-start_date", "-created_at")
        .first()
    )

    # =========================================================
    # LATEST SUBSCRIPTION
    # =========================================================

    latest_subscription = (
        Subscription.objects
        .filter(client=client)
        .order_by("-start_date", "-created_at")
        .first()
    )

    # =========================================================
    # SUBSCRIPTION STATUS
    # =========================================================

    if current_subscription:
        subscription_status = "active"
        days_remaining = (
            current_subscription.end_date - today
        ).days

    elif latest_subscription:
        if latest_subscription.end_date < today:
            subscription_status = "expired"
            days_remaining = 0

        elif latest_subscription.status == "inactive":
            subscription_status = "inactive"
            days_remaining = max(
                0,
                (latest_subscription.end_date - today).days
            )

        else:
            subscription_status = "not_active"
            days_remaining = max(
                0,
                (latest_subscription.end_date - today).days
            )

    else:
        subscription_status = "not_set"
        days_remaining = None

    # =========================================================
    # SUBSCRIPTION HISTORY
    # =========================================================

    subscription_history = (
        Subscription.objects
        .filter(client=client)
        .order_by("-start_date", "-created_at")
    )

    # =========================================================
    # TODAY'S ATTENDANCE
    # =========================================================

    daily_log = DailyLog.objects.filter(
        client=client,
        date=today
    ).first()

    attendance_marked = (
        daily_log.attendance if daily_log else False
    )

    client_marked = (
        daily_log.client_attendance_marked
        if daily_log else False
    )

    trainer_marked = (
        daily_log.trainer_attendance_marked
        if daily_log else False
    )

    # Backward compatibility with existing records
    if daily_log:
        if daily_log.attendance_marked_by == "client":
            client_marked = True
        elif daily_log.attendance_marked_by == "trainer":
            trainer_marked = True

    # =========================================================
    # WHO MARKED ATTENDANCE?
    # =========================================================

    if client_marked and trainer_marked:
        attendance_marked_by = "Client & Trainer"
    elif client_marked:
        attendance_marked_by = "Client"
    elif trainer_marked:
        attendance_marked_by = "Trainer"
    else:
        attendance_marked_by = None

    if attendance_marked:
        if attendance_marked_by:
            attendance_status = f"{attendance_marked_by} marked"
        else:
            attendance_status = "Present"
    else:
        attendance_status = "Not marked"

    # =========================================================
    # ATTENDANCE COUNT
    # =========================================================

    attendance_count = DailyLog.objects.filter(
        client=client,
        attendance=True
    ).count()

    # =========================================================
    # RECENT LOGS AND QUERIES
    # =========================================================

    recent_logs = (
        DailyLog.objects
        .filter(client=client)
        .order_by("-date")[:7]
    )

    queries = (
        Query.objects
        .filter(client=client)
        .order_by("-created_at")[:5]
    )

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {
        "client": client,
        "today": today,

        "client_account_active": client.user.is_active,

        "current_subscription": current_subscription,
        "latest_subscription": latest_subscription,
        "subscription_history": subscription_history,
        "subscription_status": subscription_status,
        "days_remaining": days_remaining,

        "daily_log": daily_log,
        "attendance": attendance_marked,
        "attendance_marked_by": attendance_marked_by,
        "attendance_status": attendance_status,
        "client_marked": client_marked,
        "trainer_marked": trainer_marked,
        "attendance_count": attendance_count,

        "recent_logs": recent_logs,
        "queries": queries,
    }

    return render(
        request,
        "core/trainer_client_detail.html",
        context
    )


# =============================================================
# TRAINER CLIENT PROGRESS
# =============================================================

# =============================================================
# TRAINER CLIENT PROGRESS
# =============================================================

@login_required
def trainer_client_progress(
    request,
    client_id
):

    # =========================================================
    # TRAINER
    # =========================================================

    trainer = request.user.trainer_profile

    # =========================================================
    # CLIENT
    # =========================================================

    client = get_object_or_404(
        ClientProfile,
        id=client_id,
        trainer=trainer
    )

    # =========================================================
    # ALL LOGS
    # =========================================================

    logs = DailyLog.objects.filter(
        client=client
    ).order_by(
        "date"
    )

    # =========================================================
    # ATTENDANCE
    # =========================================================

    attendance_count = logs.filter(
        attendance=True
    ).count()

    # =========================================================
    # SLEEP
    # =========================================================

    sleep_values = [
        log.sleep_hours
        for log in logs
        if log.sleep_hours is not None
    ]

    avg_sleep = (
        sum(sleep_values) / len(sleep_values)
        if sleep_values
        else None
    )

    # =========================================================
    # WATER
    # =========================================================

    water_values = [
        log.water_liters
        for log in logs
        if log.water_liters is not None
    ]

    avg_water = (
        sum(water_values) / len(water_values)
        if water_values
        else None
    )

    # =========================================================
    # NUTRIENTS
    # =========================================================

    calorie_values = [
        log.calories
        for log in logs
        if log.calories is not None
    ]

    protein_values = [
        log.protein
        for log in logs
        if log.protein is not None
    ]

    carb_values = [
        log.carbs
        for log in logs
        if log.carbs is not None
    ]

    fiber_values = [
        log.fiber
        for log in logs
        if log.fiber is not None
    ]

    avg_calories = (
        sum(calorie_values) / len(calorie_values)
        if calorie_values
        else None
    )

    avg_protein = (
        sum(protein_values) / len(protein_values)
        if protein_values
        else None
    )

    avg_carbs = (
        sum(carb_values) / len(carb_values)
        if carb_values
        else None
    )

    avg_fiber = (
        sum(fiber_values) / len(fiber_values)
        if fiber_values
        else None
    )

    # =========================================================
    # NUTRITION QUALITY
    # =========================================================

    nutrition_map = {
        "poor": 1,
        "average": 2,
        "good": 3,
        "excellent": 4,
    }

    nutrition_values = [
        log.nutrition
        for log in logs
        if log.nutrition
    ]

    nutrition_scores = [
        nutrition_map[nutrition]
        for nutrition in nutrition_values
        if nutrition in nutrition_map
    ]

    avg_nutrition = (
        sum(nutrition_scores) / len(nutrition_scores)
        if nutrition_scores
        else None
    )

    # =========================================================
    # GRAPH DATA
    # =========================================================

    progress_data = []

    for log in logs:

        nutrition_value = None

        if log.nutrition:
            nutrition_value = nutrition_map.get(
                log.nutrition
            )

        progress_data.append({

            "date":
                log.date.strftime("%d %b"),

            "sleep": (
                float(log.sleep_hours)
                if log.sleep_hours is not None
                else None
            ),

            "water": (
                float(log.water_liters)
                if log.water_liters is not None
                else None
            ),

            "calories": (
                float(log.calories)
                if log.calories is not None
                else None
            ),

            "protein": (
                float(log.protein)
                if log.protein is not None
                else None
            ),

            "carbs": (
                float(log.carbs)
                if log.carbs is not None
                else None
            ),

            "fiber": (
                float(log.fiber)
                if log.fiber is not None
                else None
            ),

            "nutrition":
                nutrition_value,
        })

    # =========================================================
    # CONTEXT
    # =========================================================

    context = {

        "client":
            client,

        "logs":
            logs,

        "attendance_count":
            attendance_count,

        "avg_sleep":
            avg_sleep,

        "avg_water":
            avg_water,

        "avg_calories":
            avg_calories,

        "avg_protein":
            avg_protein,

        "avg_carbs":
            avg_carbs,

        "avg_fiber":
            avg_fiber,

        "avg_nutrition":
            avg_nutrition,

        "progress_data":
            progress_data,
    }

    return render(
        request,
        "core/trainer_client_progress.html",
        context
    )


# =============================================================
# TRAINER CLIENT PLANS
# =============================================================
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_date

from .models import (
    ClientProfile,
    TrainingPlan,
    TrainingPlanNotification,
    TrainerProfile,
)


@login_required
def trainer_client_plans(request, client_id):

    # =========================================================
    # TRAINER
    # =========================================================

    try:
        trainer = request.user.trainer_profile
    except TrainerProfile.DoesNotExist:
        django_messages.error(
            request,
            "You do not have a trainer profile.",
        )
        return redirect("core:home")

    # =========================================================
    # CLIENT — ENSURE CLIENT BELONGS TO THIS TRAINER
    # =========================================================

    client = get_object_or_404(
        ClientProfile,
        id=client_id,
        trainer=trainer,
    )

    # =========================================================
    # HANDLE PLAN SUBMISSION
    # =========================================================

    if request.method == "POST":

        plan_date_input = request.POST.get("date", "").strip()
        plan_type = request.POST.get("plan_type", "").strip()
        title = request.POST.get("title", "").strip()

        # Existing PDF upload
        pdf = request.FILES.get("pdf")

        # NEW: Manual video upload
        video = request.FILES.get("video")

        # Optional external video URL
        video_url = request.POST.get("video_url", "").strip()

        # -----------------------------------------------------
        # VALIDATION
        # -----------------------------------------------------

        plan_date = (
            parse_date(plan_date_input)
            if plan_date_input
            else None
        )

        if not plan_date:
            error = "Please select a valid plan date."

        elif plan_type not in ["workout", "nutrition"]:
            error = "Please select a valid plan type."

        elif not title:
            error = "Please enter a plan title."

        elif not pdf:
            error = "Please upload a PDF file."

        elif not pdf.name.lower().endswith(".pdf"):
            error = "Please upload a PDF file."

        # Validate uploaded video extension
        elif video and not video.name.lower().endswith(
            (".mp4", ".webm", ".mov")
        ):
            error = "Please upload a video in MP4, WebM, or MOV format."

        # Basic validation for an optional video URL
        elif video_url and not (
            video_url.startswith("https://")
            or video_url.startswith("http://")
        ):
            error = (
                "Please enter a valid video URL starting "
                "with http:// or https://."
            )

        else:
            error = None

        # -----------------------------------------------------
        # SHOW VALIDATION ERROR
        # -----------------------------------------------------

        if error:
            plans = TrainingPlan.objects.filter(
                client=client
            ).order_by("-date", "-id")

            return render(
                request,
                "core/trainer_client_plans.html",
                {
                    "client": client,
                    "plans": plans,
                    "error": error,
                },
            )

        # -----------------------------------------------------
        # CHECK FOR DUPLICATE PLAN
        # One plan per client, date, and plan type
        # -----------------------------------------------------

        existing_plan = TrainingPlan.objects.filter(
            client=client,
            date=plan_date,
            plan_type=plan_type,
        ).first()

        if existing_plan:
            django_messages.error(
                request,
                (
                    f"A {plan_type} plan already exists for this client "
                    f"on {plan_date.strftime('%d %b %Y')}. "
                    "Please choose another date or plan type."
                ),
            )

            return redirect(
                "core:trainer_client_plans",
                client_id=client.id,
            )

        # -----------------------------------------------------
        # CREATE PLAN WITH PDF, VIDEO, AND OPTIONAL VIDEO URL
        # -----------------------------------------------------

        try:
            plan = TrainingPlan.objects.create(
                client=client,
                date=plan_date,
                plan_type=plan_type,
                title=title,
                pdf=pdf,
                video=video,
                video_url=video_url,
            )

        except ValidationError:
            django_messages.error(
                request,
                (
                    "The plan could not be saved. "
                    "Please check the date, PDF, and video details."
                ),
            )

            return redirect(
                "core:trainer_client_plans",
                client_id=client.id,
            )

        # -----------------------------------------------------
        # CREATE CLIENT NOTIFICATION
        # -----------------------------------------------------

        plan_label = plan.get_plan_type_display()

        notification_message = (
            f"Your trainer has sent you a new "
            f"{plan_label.lower()} plan: {plan.title}. "
        )

        if plan.video or plan.video_url:
            notification_message += (
                "A workout video is also included. "
            )

        notification_message += (
            "Open the notification to view your plan."
        )

        TrainingPlanNotification.objects.create(
            client=client,
            training_plan=plan,
            title=f"New {plan_label} plan received",
            message=notification_message,
        )

        # -----------------------------------------------------
        # SUCCESS MESSAGE
        # -----------------------------------------------------

        django_messages.success(
            request,
            (
                f"{plan_label} plan sent to "
                f"{client.user.username} successfully."
            ),
        )

        return redirect(
            "core:trainer_client_plans",
            client_id=client.id,
        )

    # =========================================================
    # EXISTING PLANS
    # =========================================================

    plans = TrainingPlan.objects.filter(
        client=client
    ).order_by("-date", "-id")

    # =========================================================
    # RENDER
    # =========================================================

    return render(
        request,
        "core/trainer_client_plans.html",
        {
            "client": client,
            "plans": plans,
        },
    )


# =============================================================
# TRAINER SCHEDULE
# =============================================================

@login_required
def trainer_schedule(request):

    # ---------------------------------------------------------
    # GET LOGGED-IN TRAINER
    # ---------------------------------------------------------

    trainer = request.user.trainer_profile

    # ---------------------------------------------------------
    # GET ONLY THIS TRAINER'S CLIENTS
    # ---------------------------------------------------------

    clients = trainer.clients.select_related(
        "user"
    ).all()

    # ---------------------------------------------------------
    # CLIENT PLAN COUNTS
    # ---------------------------------------------------------

    client_data = []

    for client in clients:

        workout_count = TrainingPlan.objects.filter(
            client=client,
            plan_type="workout"
        ).count()

        nutrition_count = TrainingPlan.objects.filter(
            client=client,
            plan_type="nutrition"
        ).count()

        client_data.append({

            "client":
                client,

            "workout_count":
                workout_count,

            "nutrition_count":
                nutrition_count,

        })
        
    

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

    return render(
        request,
        "core/trainer_schedule.html",
        {
            "clients":
                client_data,
        }
    )
    
def website_home(request):
    return render(request, "core/home11.html")

# =============================================================
# CLIENT PROFILE
# =============================================================

@login_required
def profile(request):

    client = get_object_or_404(
        ClientProfile.objects.select_related("user", "trainer__user"),
        user=request.user
    )

    today = timezone.localdate()

    # =========================================================
    # UPDATE CLIENT PROFILE
    # =========================================================

    if request.method == "POST":

        user = client.user

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        age_value = request.POST.get("age", "").strip()
        gender = request.POST.get("gender", "").strip()
        height_value = request.POST.get("height", "").strip()
        weight_value = request.POST.get("weight", "").strip()
        fitness_goal = request.POST.get("fitness_goal", "").strip()

        uploaded_image = request.FILES.get("profile_image")

        errors = []

        # -----------------------------------------------------
        # VALIDATE FULL NAME
        # -----------------------------------------------------

        if not full_name:
            errors.append("Full name is required.")

        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # -----------------------------------------------------
        # VALIDATE EMAIL
        # -----------------------------------------------------

        try:
            email = forms.EmailField().clean(email)
        except ValidationError:
            errors.append("Please enter a valid email address.")

        UserModel = get_user_model()

        if email and UserModel.objects.filter(
            email__iexact=email
        ).exclude(pk=user.pk).exists():
            errors.append("This email address is already being used.")

        # -----------------------------------------------------
        # VALIDATE PHONE
        # -----------------------------------------------------

        if len(phone) > 15:
            errors.append("Phone number cannot exceed 15 characters.")

        # -----------------------------------------------------
        # VALIDATE AGE
        # -----------------------------------------------------

        age = None

        if age_value:
            try:
                age = int(age_value)

                if age <= 0:
                    errors.append("Age must be greater than zero.")

            except ValueError:
                errors.append("Please enter a valid age.")

        # -----------------------------------------------------
        # VALIDATE GENDER
        # -----------------------------------------------------

        gender_choices = ClientProfile._meta.get_field(
            "gender"
        ).choices

        allowed_genders = [
            value for value, label in gender_choices
        ]

        if gender not in allowed_genders:
            errors.append("Please select a valid gender.")

        # -----------------------------------------------------
        # VALIDATE HEIGHT
        # -----------------------------------------------------

        height = None

        if height_value:
            try:
                height = Decimal(height_value)

                if not height.is_finite():
                    errors.append("Please enter a valid height.")

                elif height <= 0 or height >= 1000:
                    errors.append(
                        "Height must be greater than zero and less than 1000."
                    )

                elif max(0, -height.as_tuple().exponent) > 2:
                    errors.append(
                        "Height can have at most two decimal places."
                    )

            except (InvalidOperation, ValueError):
                errors.append("Please enter a valid height.")

        # -----------------------------------------------------
        # VALIDATE WEIGHT
        # -----------------------------------------------------

        weight = None

        if weight_value:
            try:
                weight = Decimal(weight_value)

                if not weight.is_finite():
                    errors.append("Please enter a valid weight.")

                elif weight <= 0 or weight >= 1000:
                    errors.append(
                        "Weight must be greater than zero and less than 1000."
                    )

                elif max(0, -weight.as_tuple().exponent) > 2:
                    errors.append(
                        "Weight can have at most two decimal places."
                    )

            except (InvalidOperation, ValueError):
                errors.append("Please enter a valid weight.")

        # -----------------------------------------------------
        # VALIDATE FITNESS GOAL
        # -----------------------------------------------------

        fitness_goal_choices = ClientProfile._meta.get_field(
            "fitness_goal"
        ).choices

        allowed_fitness_goals = [
            value for value, label in fitness_goal_choices
        ]

        if fitness_goal and fitness_goal not in allowed_fitness_goals:
            errors.append("Please select a valid fitness goal.")

        # -----------------------------------------------------
        # VALIDATE PROFILE IMAGE
        # -----------------------------------------------------

        if uploaded_image:

            # Maximum allowed image size: 5 MB.
            if uploaded_image.size > 5 * 1024 * 1024:
                errors.append(
                    "Profile image must be smaller than 5 MB."
                )

            else:
                try:
                    forms.ImageField(
                        required=False
                    ).clean(uploaded_image)

                except ValidationError:
                    errors.append(
                        "Please upload a valid image file."
                    )

        # -----------------------------------------------------
        # SAVE PROFILE IF VALIDATION SUCCEEDS
        # -----------------------------------------------------

        if errors:

            for error in errors:
                django_messages.error(request, error)

        else:

            # Update Django user information.
            user.first_name = first_name
            user.last_name = last_name
            user.email = email

            user.save(
                update_fields=[
                    "first_name",
                    "last_name",
                    "email",
                ]
            )

            # Update client profile information.
            client.phone = phone
            client.age = age
            client.gender = gender
            client.height = height
            client.weight = weight
            client.fitness_goal = fitness_goal or None

            # Keep the existing image unless a new one is uploaded.
            if uploaded_image:
                client.profile_image = uploaded_image

            client.save(
                update_fields=[
                    "phone",
                    "age",
                    "gender",
                    "height",
                    "weight",
                    "fitness_goal",
                    "profile_image",
                ]
            )

            django_messages.success(
                request,
                "Your profile has been updated successfully."
            )

            return redirect("core:profile")

    # =========================================================
    # UPDATE EXPIRED SUBSCRIPTION STATUS
    # =========================================================

    Subscription.objects.filter(
        client=client,
        status="active",
        end_date__lt=today
    ).update(
        status="expired",
        updated_at=timezone.now()
    )

    # =========================================================
    # GET CURRENT SUBSCRIPTION
    # =========================================================

    current_subscription = (
        Subscription.objects
        .filter(
            client=client,
            status="active",
            start_date__lte=today,
            end_date__gte=today
        )
        .order_by("-start_date", "-created_at")
        .first()
    )

    # =========================================================
    # GET LATEST SUBSCRIPTION
    # =========================================================

    latest_subscription = (
        Subscription.objects
        .filter(client=client)
        .order_by("-start_date", "-created_at")
        .first()
    )

    # =========================================================
    # SUBSCRIPTION HISTORY
    # =========================================================

    subscription_history = (
        Subscription.objects
        .filter(client=client)
        .order_by("-start_date", "-created_at")
    )

    # =========================================================
    # SUBSCRIPTION STATUS
    # =========================================================

    if current_subscription:

        subscription_status = "active"

        days_remaining = (
            current_subscription.end_date - today
        ).days

    elif latest_subscription:

        subscription_status = latest_subscription.status

        days_remaining = max(
            0,
            (latest_subscription.end_date - today).days
        )

    else:

        subscription_status = "not_set"
        days_remaining = None

    # =========================================================
    # RENDER PROFILE PAGE
    # =========================================================

    return render(
        request,
        "core/profile.html",
        {
            "client": client,
            "today": today,
            "current_subscription": current_subscription,
            "latest_subscription": latest_subscription,
            "subscription_history": subscription_history,
            "subscription_status": subscription_status,
            "days_remaining": days_remaining,
            "gender_choices": ClientProfile._meta.get_field(
                "gender"
            ).choices,
            "fitness_goal_choices": ClientProfile._meta.get_field(
                "fitness_goal"
            ).choices,
        }
    )

# =============================================================
# CLIENT BODY MEASUREMENTS - 10 DAY TRACKING
# =============================================================

@login_required
def body_measurements(request):
    client = get_object_or_404(
        ClientProfile,
        user=request.user
    )

    today = timezone.localdate()
    period_start = today - timedelta(days=9)

    measurements = BodyMeasurement.objects.filter(
        client=client,
        date__range=(period_start, today)
    ).order_by("date")

    errors = []

    if request.method == "POST":
        date_text = request.POST.get("date", "").strip()
        notes = request.POST.get("notes", "").strip()

        try:
            entry_date = datetime.strptime(
                date_text, "%Y-%m-%d"
            ).date()
        except ValueError:
            entry_date = None
            errors.append("Please select a valid date.")

        if entry_date and not (period_start <= entry_date <= today):
            errors.append(
                "Choose a date within the current 10-day tracking period."
            )

        field_names = [
            "weight",
            "waist",
            "chest",
            "hips",
            "arms",
            "thighs",
        ]

        values = {}

        for field in field_names:
            raw_value = request.POST.get(field, "").strip()

            if not raw_value:
                values[field] = None
                continue

            try:
                number = Decimal(raw_value)

                if not number.is_finite() or number < 0:
                    raise InvalidOperation

                values[field] = number

            except (InvalidOperation, ValueError):
                errors.append(
                    f"Enter a valid non-negative number for {field}."
                )

        if not errors:
            BodyMeasurement.objects.update_or_create(
                client=client,
                date=entry_date,
                defaults={
                    **values,
                    "notes": notes,
                }
            )

            django_messages.success(
                request,
                "Your body measurements have been saved."
            )

            return redirect("core:body_measurements")

    # Include every day in the 10-day window, even when
    # the client has not entered measurements for that day.
    measurement_by_date = {
        item.date: item for item in measurements
    }

    daily_entries = []

    for offset in range(10):
        entry_date = period_start + timedelta(days=offset)

        daily_entries.append({
            "date": entry_date,
            "measurement": measurement_by_date.get(entry_date),
            "is_today": entry_date == today,
        })

    return render(
        request,
        "core/body_measurements.html",
        {
            "client": client,
            "today": today,
            "period_start": period_start,
            "daily_entries": daily_entries,
            "errors": errors,
        }
    )


# =============================================================
# DOWNLOAD BODY MEASUREMENT PDF
# =============================================================

@login_required
def download_body_measurement_pdf(request):
    client = get_object_or_404(
        ClientProfile,
        user=request.user
    )

    today = timezone.localdate()
    period_start = today - timedelta(days=9)

    measurements = list(
        BodyMeasurement.objects.filter(
            client=client,
            date__range=(period_start, today)
        ).order_by("date")
    )

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(
        Paragraph("FitConnect - Body Measurement Report", styles["Title"])
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        Paragraph(
            f"Client: {client.user.username}",
            styles["Normal"]
        )
    )
    story.append(
        Paragraph(
            f"Period: {period_start:%d %b %Y} - {today:%d %b %Y}",
            styles["Normal"]
        )
    )
    story.append(Spacer(1, 6 * mm))

    headers = [
        "Date",
        "Weight (kg)",
        "Waist (cm)",
        "Chest (cm)",
        "Hips (cm)",
        "Arms (cm)",
        "Thighs (cm)",
        "Notes",
    ]

    table_data = [headers]

    for item in measurements:
        table_data.append([
            item.date.strftime("%d %b %Y"),
            str(item.weight) if item.weight is not None else "-",
            str(item.waist) if item.waist is not None else "-",
            str(item.chest) if item.chest is not None else "-",
            str(item.hips) if item.hips is not None else "-",
            str(item.arms) if item.arms is not None else "-",
            str(item.thighs) if item.thighs is not None else "-",
            Paragraph(
                (item.notes or "-").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
                styles["BodyText"]
            ),
        ])

    if not measurements:
        story.append(
            Paragraph(
                "No body measurements were recorded during this period.",
                styles["Normal"]
            )
        )
    else:
        table = Table(
            table_data,
            repeatRows=1,
            colWidths=[
                25 * mm,
                22 * mm,
                22 * mm,
                22 * mm,
                22 * mm,
                20 * mm,
                22 * mm,
                65 * mm,
            ],
        )

        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6D28D9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D6D3E0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white,
                colors.HexColor("#F5F3FF"),
            ]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))

        story.append(table)

        # Compare the first and latest recorded values
        # separately for each measurement field.
        story.append(Spacer(1, 8 * mm))
        story.append(
            Paragraph("First-to-Latest Comparison", styles["Heading2"])
        )

        comparison_data = [["Measurement", "First recorded", "Latest recorded", "Change"]]

        fields = [
            ("Weight (kg)", "weight"),
            ("Waist (cm)", "waist"),
            ("Chest (cm)", "chest"),
            ("Hips (cm)", "hips"),
            ("Arms (cm)", "arms"),
            ("Thighs (cm)", "thighs"),
        ]

        for label, field in fields:
            recorded = [
                getattr(item, field)
                for item in measurements
                if getattr(item, field) is not None
            ]

            if recorded:
                first_value = recorded[0]
                latest_value = recorded[-1]
                change = latest_value - first_value

                comparison_data.append([
                    label,
                    str(first_value),
                    str(latest_value),
                    f"{change:+}",
                ])

        if len(comparison_data) > 1:
            comparison_table = Table(
                comparison_data,
                colWidths=[55 * mm, 45 * mm, 45 * mm, 35 * mm],
            )
            comparison_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6D28D9")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(comparison_table)

    document.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )
    response["Content-Disposition"] = (
        'attachment; filename="fitconnect_body_measurements.pdf"'
    )

    return response

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from core.models import (
    ClientProfile,
    TrainingPlanNotification,
)


@login_required
def open_training_notification(request, notification_id):

    # Ensure the logged-in user is a client
    try:
        client = request.user.client_profile
    except ClientProfile.DoesNotExist:
        return redirect("core:home")

    # Only allow clients to open their own notifications
    notification = get_object_or_404(
        TrainingPlanNotification.objects.select_related(
            "training_plan"
        ),
        id=notification_id,
        client=client,
    )

    # Mark notification as read
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    # Redirect to the uploaded PDF
    plan = notification.training_plan

    if plan.pdf:
        return redirect(plan.pdf.url)

    return redirect("core:home")
