# 💪 FitConnect

### Your Fitness Journey, Connected.

FitConnect is a Django-based fitness platform designed to support fitness management and interaction between trainers and clients.

The platform brings together training plans, fitness progress tracking, schedules, communication and client management in one place.

---

## 🚀 Features

- **User Authentication:** Registration and login functionality.
- **Client Dashboard:** Access fitness-related information and activities.
- **Trainer Dashboard:** Manage clients and training-related activities.
- **Training Plans:** View and manage training plans and workout videos.
- **Progress Tracking:** Track daily logs, body measurements and body composition.
- **Step Tracking:** Record daily step counts.
- **Schedules & Attendance:** Manage schedules and attendance.
- **Communication:** Queries, messages and notifications.
- **Profile Management:** Maintain user profiles and profile images.
- **Subscription Management:** Support for subscription-related functionality.

---

## 🛠️ Technologies Used

| Category | Technologies |
|---|---|
| Backend | Python, Django |
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Database | SQLite (local development) |
| Image Handling | Pillow |
| Version Control | Git, GitHub |

---

## 📂 Project Structure

```text
FitConnect/
│
├── accounts/
│   └── User authentication and account-related functionality
│
├── core/
│   ├── migrations/
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── img/
│   ├── templates/
│   │   └── core/
│   └── Application functionality
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── manage.py
├── requirements.txt
├── .gitignore
└── README.md
```

---

## ⚙️ Installation & Setup

Follow these steps to run FitConnect locally.

### 1. Clone the repository

```bash
git clone https://github.com/Nikharmahajan12/FitConnect.git
```

### 2. Navigate to the project directory

```bash
cd FitConnect
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows:**

```bash
venv\Scripts\activate
```

**macOS/Linux:**

```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

### 6. Configure environment variables

Create a `.env` file in the project root directory.

Add your own secret key:

```env
SECRET_KEY=your-own-django-secret-key
DEBUG=True
```

Never upload your `.env` file or expose your secret key publicly.

### 7. Apply database migrations

```bash
python manage.py migrate
```

### 8. Run the development server

```bash
python manage.py runserver
```

Open the following address in your browser:

http://127.0.0.1:8000/

---

## 📸 Screenshots

Screenshots of the application will be added here.

| Homepage | Client Dashboard |
|---|---|
| Add homepage screenshot | Add dashboard screenshot |

| Trainer Dashboard | Progress Tracking |
|---|---|
| Add trainer screenshot | Add progress screenshot |

---

## 🔮 Future Improvements

- Complete cloud deployment.
- Improve the user experience and responsive design.
- Enhance fitness analytics and progress visualization.
- Expand trainer-client interaction features.

---

## 👨‍💻 Developer

**Nikhar Mahajan**

B.Tech Information Technology | Python Full Stack Developer

- GitHub: [Nikharmahajan12](https://github.com/Nikharmahajan12)
- LinkedIn: [Nikhar Mahajan](https://www.linkedin.com/in/nikhar-mahajan-b80336387)
- Email: mahajannikhar203@gmail.com

---

⭐ If you find this project interesting, consider giving the repository a star!

**Built with Python and Django.**
