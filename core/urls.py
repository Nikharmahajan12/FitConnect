from django.urls import path

from . import views

app_name = "core"

urlpatterns = [

    path("", views.home, name="home"),

    path("schedule/", views.schedule, name="schedule"),

    path("messages/", views.messages, name="messages"),

    path("attendance/", views.mark_attendance, name="mark_attendance"),

    path("save-lifestyle/", views.save_lifestyle, name="save_lifestyle"),

    # Trainer
    path(
        "trainer/",
        views.trainer_dashboard,
        name="trainer_dashboard"
    ),

    path(
        "trainer/attendance/<int:client_id>/",
        views.trainer_mark_attendance,
        name="trainer_mark_attendance"
    ),

    path(
        "trainer/query/<int:query_id>/",
        views.trainer_query_detail,
        name="trainer_query_detail"
    ),

    path(
        "trainer/queries/",
        views.trainer_queries,
        name="trainer_queries"
    ),

    path(
        "trainer/clients/",
        views.trainer_clients,
        name="trainer_clients"
    ),

    path(
        "trainer/clients/<int:client_id>/",
        views.trainer_client_detail,
        name="trainer_client_detail"
    ),

    path(
        "trainer/clients/<int:client_id>/progress/",
        views.trainer_client_progress,
        name="trainer_client_progress"
    ),

    path(
        "trainer/schedule/",
        views.trainer_schedule,
        name="trainer_schedule"
    ),

    # Public website
    path(
        "website/",
        views.website_home,
        name="website_home"
    ),
path(
    "trainer/clients/connect/",
    views.trainer_connect_client,
    name="trainer_connect_client"
),
path(
    "trainer/clients/<int:client_id>/plans/",
    views.trainer_client_plans,
    name="trainer_client_plans"
),
path(
    "progress/",
    views.progress,
    name="progress",
),
    path("profile/", views.profile, name="profile"),
    path(
        "body-measurements/",
        views.body_measurements,
        name="body_measurements",
    ),

    path(
        "body-measurements/download-pdf/",
        views.download_body_measurement_pdf,
        name="download_body_measurement_pdf",
    ),
    path(
    "training-notifications/<int:notification_id>/",
    views.open_training_notification,
    name="open_training_notification",
),

]
