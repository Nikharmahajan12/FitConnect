from django.db import models
from django.contrib.auth.models import User


# ============================================================
# TRAINER PROFILE
# ============================================================

class TrainerProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="trainer_profile"
    )

    def __str__(self):
        return self.user.username


# ============================================================
# CLIENT PROFILE
# ============================================================

class ClientProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="client_profile"
    )
        # ========================================================
    # CLIENT PROFILE IMAGE
    # ========================================================

    profile_image = models.ImageField(
        upload_to="client_profiles/",
        null=True,
        blank=True
    )

    # ========================================================
    # PHYSICAL DETAILS
    # ========================================================

    age = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    height = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    phone = models.CharField(
        max_length=15,
        blank=True
    )

    gender = models.CharField(
        max_length=20,
        choices=[
            ("male", "Male"),
            ("female", "Female"),
            ("other", "Other"),
        ]
    )

    fitness_goal = models.CharField(
    max_length=100,
    blank=True,
    null=True,
    choices=[
        ("weight_loss", "Weight Loss"),
        ("muscle_gain", "Build Muscle"),
        ("strength", "Build Strength"),
        ("endurance", "Improve Endurance"),
        ("general_fitness", "General Fitness"),
        ("flexibility", "Flexibility & Mobility"),
        ("sports_performance", "Sports Performance"),
        ("weight_maintenance", "Maintain Current Weight"),
        ("healthy_lifestyle", "Improve Overall Health"),
        ("other", "Other"),
    ]
)

    # ========================================================
    # TRAINER
    # ========================================================

    trainer = models.ForeignKey(
        TrainerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clients"
    )

    # ========================================================
    # OLD MEMBERSHIP FIELDS
    # ========================================================
    # Kept for compatibility with your existing dashboard/code.
    # Subscription will become the main subscription system.

    membership_start = models.DateField(
        null=True,
        blank=True
    )

    membership_end = models.DateField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.user.username


# ============================================================
# SUBSCRIPTION
# ============================================================

class Subscription(models.Model):

    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("expired", "Expired"),
    ]

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    # ========================================================
    # SUBSCRIPTION DETAILS
    # ========================================================

    plan_name = models.CharField(
        max_length=100
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    start_date = models.DateField()

    end_date = models.DateField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="inactive"
    )

    # ========================================================
    # TRACKING
    # ========================================================

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return (
            f"{self.client.user.username} - "
            f"{self.plan_name} - "
            f"{self.status}"
        )


# ============================================================
# DAILY LOG
# ============================================================

class DailyLog(models.Model):

    # ========================================================
    # ATTENDANCE SOURCE
    # ========================================================

    ATTENDANCE_MARKED_BY_CHOICES = [
        ("client", "Client"),
        ("trainer", "Trainer"),
    ]

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="daily_logs"
    )

    date = models.DateField()

    attendance = models.BooleanField(
        default=False
    )

    
    attendance_marked_by = models.CharField(
        max_length=20,
        choices=ATTENDANCE_MARKED_BY_CHOICES,
        null=True,
        blank=True
    )

    # Track both attendance markers independently
    client_attendance_marked = models.BooleanField(
        default=False
    )

    trainer_attendance_marked = models.BooleanField(
        default=False
    )


    # ========================================================
    # LIFESTYLE
    # ========================================================

    sleep_hours = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    water_liters = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True
    )

    # ========================================================
    # NUTRITION
    # ========================================================

    calories = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True
    )

    protein = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )

    carbs = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )

    fiber = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True
    )

    nutrition = models.CharField(
        max_length=20,
        choices=[
            ("poor", "Poor"),
            ("average", "Average"),
            ("good", "Good"),
            ("excellent", "Excellent"),
        ],
        blank=True
    )

    class Meta:

        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=["client", "date"],
                name="unique_client_daily_log"
            )
        ]

    def __str__(self):
        return f"{self.client} - {self.date}"


# ============================================================
# TRAINING PLAN
# ============================================================

class TrainingPlan(models.Model):

    PLAN_TYPES = [
        ("workout", "Workout"),
        ("nutrition", "Nutrition"),
    ]

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="training_plans"
    )

    date = models.DateField()

    plan_type = models.CharField(
        max_length=20,
        choices=PLAN_TYPES
    )

    title = models.CharField(
        max_length=200
    )

    # Existing required PDF upload
    pdf = models.FileField(
        upload_to="training_plans/"
    )

    # Optional video uploaded directly from the trainer's computer
    video = models.FileField(
        upload_to="training_videos/",
        blank=True,
        null=True
    )

    # Optional external video link, such as YouTube
    video_url = models.URLField(
        max_length=500,
        blank=True
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["date", "plan_type"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "client",
                    "date",
                    "plan_type"
                ],
                name="unique_client_plan_per_day"
            )
        ]

    def __str__(self):
        return (
            f"{self.client} - "
            f"{self.date} - "
            f"{self.get_plan_type_display()}"
        )


# ============================================================
# CLIENT QUERY
# ============================================================

class Query(models.Model):

    CATEGORY_CHOICES = [
        ("workout", "Workout"),
        ("nutrition", "Nutrition"),
        ("schedule", "Schedule"),
        ("progress", "Progress"),
        ("general", "General"),
        ("technical", "Technical Issue"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("answered", "Answered"),
        ("closed", "Closed"),
    ]

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="queries"
    )

    subject = models.CharField(
        max_length=200
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES
    )

    message = models.TextField()

    response = models.TextField(
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    answered_at = models.DateTimeField(
        blank=True,
        null=True
    )

    class Meta:

        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.subject} - {self.client}"

# ============================================================
# SUBSCRIPTION EXPIRY NOTIFICATIONS
# ============================================================

# ============================================================
# SUBSCRIPTION EXPIRY NOTIFICATIONS
# ============================================================

class SubscriptionNotification(models.Model):

    REMINDER_DAYS_CHOICES = [
    (5, "5 days before expiry"),
    (2, "2 days before expiry"),
    (1, "1 day before expiry"),
    (0, "Expires today"),
]

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    reminder_days = models.PositiveSmallIntegerField(
        choices=REMINDER_DAYS_CHOICES
    )

    title = models.CharField(max_length=150)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["subscription", "reminder_days"],
                name="unique_subscription_expiry_reminder"
            )
        ]

    def __str__(self):
        return (
            f"{self.subscription.client.user.username} - "
            f"{self.reminder_days}-day expiry reminder"
        )


# ============================================================
# BODY MEASUREMENT TRACKING
# ============================================================

class BodyMeasurement(models.Model):

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="body_measurements"
    )

    date = models.DateField()

    # Body measurements
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    waist = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    chest = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    hips = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    arms = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    thighs = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "date"],
                name="unique_client_body_measurement_date"
            )
        ]

    def __str__(self):
        return f"{self.client.user.username} - {self.date}"

class BodyCompositionTest(models.Model):
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="body_composition_tests"
    )
    test_date = models.DateField()

    body_fat_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )
    muscle_mass_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )
    body_water_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )
    bmi = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-test_date", "-created_at"]

    def __str__(self):
        return f"{self.client.user.username} - {self.test_date}"

# ============================================================
# DAILY STEP COUNTER
# ============================================================

class DailyStepCount(models.Model):

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="step_counts"
    )

    date = models.DateField()

    steps = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "date"],
                name="unique_client_step_count_date"
            )
        ]

    def __str__(self):
        return f"{self.client.user.username} - {self.date} - {self.steps} steps"

# ============================================================
# TRAINING PLAN NOTIFICATIONS
# ============================================================

class TrainingPlanNotification(models.Model):

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="training_plan_notifications"
    )

    training_plan = models.ForeignKey(
        TrainingPlan,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(max_length=150)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.client.user.username} - "
            f"{self.title}"
        )
