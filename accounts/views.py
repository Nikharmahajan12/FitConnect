import re

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from core.models import ClientProfile, TrainerProfile


def login_view(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:

            login(request, user)

            # =========================
            # TRAINER LOGIN
            # =========================

            if hasattr(user, "trainer_profile"):
                return redirect(
                    "core:trainer_dashboard"
                )

            # =========================
            # CLIENT LOGIN
            # =========================

            if hasattr(user, "client_profile"):

                next_url = request.GET.get("next")

                if next_url:
                    return redirect(next_url)

                return redirect(
                    "core:home"
                )

            # =========================
            # UNKNOWN ACCOUNT TYPE
            # =========================

            return redirect(
                "core:home"
            )

        return render(
            request,
            "accounts/login.html",
            {
                "error": "Invalid username or password."
            }
        )

    return render(
        request,
        "accounts/login.html"
    )


def register_view(request):

    if request.method == "POST":

        # =========================
        # GET FORM DATA
        # =========================

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        age = request.POST.get(
            "age",
            ""
        ).strip()

        gender = request.POST.get(
            "gender",
            ""
        )

        height = request.POST.get(
            "height",
            ""
        ).strip()

        weight = request.POST.get(
            "weight",
            ""
        ).strip()

        fitness_goal = request.POST.get(
            "fitness_goal",
            ""
        ).strip()

        form_data = request.POST

        # =========================
        # REQUIRED FIELDS
        # =========================

        if not all([
            full_name,
            username,
            email,
            phone,
            password,
            confirm_password,
            age,
            gender,
            height,
            weight
        ]):

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "Please fill in all required fields.",
                    "form_data": form_data
                }
            )

        # =========================
        # EMAIL VALIDATION
        # =========================

        email_pattern = (
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        )

        if not re.fullmatch(
            email_pattern,
            email
        ):

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "Please enter a valid email address.",
                    "form_data": form_data
                }
            )

        # =========================
        # EMAIL UNIQUENESS
        # =========================

        if User.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "An account with this email already exists.",
                    "form_data": form_data
                }
            )

        # =========================
        # PHONE VALIDATION
        # =========================

        if not re.fullmatch(
            r"\d{10}",
            phone
        ):

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "Phone number must contain exactly 10 digits.",
                    "form_data": form_data
                }
            )

        # =========================
        # PASSWORD VALIDATION
        # =========================

        if not re.fullmatch(
            r"\d{6}",
            password
        ):

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "Password must contain exactly 6 digits.",
                    "form_data": form_data
                }
            )

        # =========================
        # PASSWORD CONFIRMATION
        # =========================

        if password != confirm_password:

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "Passwords do not match.",
                    "form_data": form_data
                }
            )

        # =========================
        # USERNAME VALIDATION
        # =========================

        if User.objects.filter(
            username__iexact=username
        ).exists():

            return render(
                request,
                "accounts/register.html",
                {
                    "error":
                        "This username is already taken.",
                    "form_data": form_data
                }
            )

        # =========================
        # CREATE USER
        # =========================

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # Store full name

        name_parts = full_name.split(
            " ",
            1
        )

        user.first_name = name_parts[0]

        if len(name_parts) > 1:
            user.last_name = name_parts[1]

        user.save()

        # =========================
        # CREATE CLIENT PROFILE
        # =========================

        ClientProfile.objects.create(
            user=user,
            age=age,
            gender=gender,
            height=height,
            weight=weight,
            phone=phone,
            fitness_goal=(
                fitness_goal
                if fitness_goal
                else None
            )
        )

        # =========================
        # REGISTRATION COMPLETE
        # =========================

        return redirect(
            "core:home"
        )

    return render(
        request,
        "accounts/register.html"
    )


def trainer_register_view(request):

    if request.method == "POST":

        # =========================
        # GET FORM DATA
        # =========================

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        confirm_password = request.POST.get(
            "confirm_password",
            ""
        )

        form_data = request.POST

        # =========================
        # REQUIRED FIELDS
        # =========================

        if not all([
            full_name,
            username,
            email,
            password,
            confirm_password
        ]):

            return render(
                request,
                "accounts/trainer_register.html",
                {
                    "error":
                        "Please fill in all required fields.",
                    "form_data": form_data
                }
            )

        # =========================
        # EMAIL VALIDATION
        # =========================

        email_pattern = (
            r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        )

        if not re.fullmatch(
            email_pattern,
            email
        ):

            return render(
                request,
                "accounts/trainer_register.html",
                {
                    "error":
                        "Please enter a valid email address.",
                    "form_data": form_data
                }
            )

        # =========================
        # EMAIL UNIQUENESS
        # =========================

        if User.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "accounts/trainer_register.html",
                {
                    "error":
                        "An account with this email already exists.",
                    "form_data": form_data
                }
            )

        # =========================
        # USERNAME VALIDATION
        # =========================

        if User.objects.filter(
            username__iexact=username
        ).exists():

            return render(
                request,
                "accounts/trainer_register.html",
                {
                    "error":
                        "This username is already taken.",
                    "form_data": form_data
                }
            )

        # =========================
        # PASSWORD VALIDATION
        # =========================

        if not re.fullmatch(
            r"\d{6}",
            password
        ):

            return render(
                request,
                "accounts/trainer_register.html",
                {
                    "error":
                        "Password must contain exactly 6 digits.",
                    "form_data": form_data
                }
            )

        # =========================
        # PASSWORD CONFIRMATION
        # =========================

        if password != confirm_password:

            return render(
                request,
                "accounts/trainer_register.html",
                {
                    "error":
                        "Passwords do not match.",
                    "form_data": form_data
                }
            )

        # =========================
        # CREATE USER
        # =========================

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        # =========================
        # STORE FULL NAME
        # =========================

        name_parts = full_name.split(
            " ",
            1
        )

        user.first_name = name_parts[0]

        if len(name_parts) > 1:
            user.last_name = name_parts[1]

        user.save()

        # =========================
        # CREATE TRAINER PROFILE
        # =========================

        TrainerProfile.objects.create(
            user=user
        )

        # =========================
        # REGISTRATION COMPLETE
        # =========================

        return redirect(
            "accounts:login"
        )

    return render(
        request,
        "accounts/trainer_register.html"
    )