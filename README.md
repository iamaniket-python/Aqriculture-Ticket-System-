# 🌾 Agriculture Ticket System

A Django-based **Agriculture Customer Support & Ticket Management System** that allows users to manage purchases, create support tickets, communicate with support staff, and track ticket status.

## 🚀 Features

### 👤 User Features

* User registration and login using mobile number
* JWT-based authentication
* User profile management
* View purchase history
* Create support tickets
* Select ticket category
* Track ticket status
* Upload supporting documents/images
* Add comments to tickets
* Real-time-style ticket conversation
* Track ticket updates

### 🎫 Ticket Management

Tickets can have the following statuses:

* `Pending`
* `In Progress`
* `Resolved`

Supported categories:

* Billing
* Technical
* Delivery
* Refund
* Other

### 🧑‍💼 Staff Features

* Staff login
* Staff approval system
* View assigned tickets
* Update ticket status
* Reply to customers
* Manage ticket conversations

### 👨‍💻 Admin Features

* Admin authentication
* View and manage users
* Manage tickets
* Assign tickets to staff
* Monitor customer conversations
* Manage staff
* Admin-to-staff communication

## 🛠️ Tech Stack

### Backend

* Python
* Django
* Django REST Framework
* Django REST Framework Simple JWT
* PostgreSQL
* Redis
* Cloudinary

### Frontend

* Django Templates
* HTML
* CSS
* JavaScript

### Deployment

* Vercel
* PostgreSQL / Neon
* Cloudinary

## 📁 Project Structure

```text
Agriculture/
│
├── agriculture/
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── ...
│
├── user/
│   ├── models.py
│   ├── views.py
│   ├── serializers.py
│   ├── middleware.py
│   ├── urls.py
│   └── ...
│
├── templates/
│   ├── Authentication/
│   └── ...
│
├── static/
├── media/
├── manage.py
├── requirements.txt
└── README.md
```

## 🗄️ Main Models

The application contains several core models:

* `Profile` — stores user mobile and address information
* `Purchase` — stores customer purchase history
* `Ticket` — stores customer support tickets
* `TicketImage` — stores ticket images
* `TicketComment` — handles ticket conversations
* `TrackingUser` — tracks users using tracking IDs
* `StaffProfile` — manages staff approval
* `AdminChat` — handles admin/staff communication

## 🔐 Authentication

The project uses **JWT authentication** for API/user authentication.

JWT configuration includes:

```text
Access Token  → 30 minutes
Refresh Token → 7 days
```

Authentication tokens are stored using secure HTTP cookies.

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/iamaniket-python/Aqriculture-Ticket-System-.git
```

```bash
cd Aqriculture-Ticket-System-
```

### 2. Create a virtual environment

Windows:

```bash
python -m venv venv
```

Activate it:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```env
SECRET_KEY=your-secret-key
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=your-database-url

CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

REDIS_URL=your-redis-url

EMAIL_USER=your-email
EMAIL_PASSWORD=your-email-password
```

> Never commit your `.env` file or API credentials to GitHub.

### 5. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an admin user

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## 🔌 API

The application provides APIs for user registration, authentication, profiles, tickets, purchases, and ticket communication.

Example authentication header:

```http
Authorization: Bearer <access_token>
```

## 🧪 Testing

You can test the APIs using:

* Postman
* Django Admin
* Browser
* REST API clients

Example login request:

```http
POST /login/
```

Request:

```text
mobile=9876543210
```

## 🔒 Security

The project includes:

* JWT authentication
* HTTP-only authentication cookies
* CSRF protection
* Secure cookies in production
* HTTPS support
* Django authentication middleware
* Environment-based secrets
* Host validation
* Cloudinary for media storage

## ☁️ Deployment

The project can be deployed using **Vercel** with PostgreSQL/Neon as the production database.

Before deployment, configure the required environment variables in the hosting platform.

Production settings should use:

```env
DEBUG=False
```

and a production database URL.

## 📌 Future Improvements

* Email notifications
* SMS notifications
* Advanced ticket filtering
* Ticket priority system
* Analytics dashboard
* Automated ticket assignment
* Improved search
* Customer satisfaction/rating system
* More detailed admin reports

## 👨‍💻 Author

**Aniket Shrivastava**

GitHub:

`https://github.com/iamaniket-python`

---

## 📄 License

This project is developed for learning and project purposes.
