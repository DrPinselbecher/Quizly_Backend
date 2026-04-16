# ✅ QUIZLY – Backend (Django REST API)

Quizly is an AI-powered quiz platform where authenticated users can submit a **YouTube URL** and generate a quiz with **10 questions** based on the content of the video.

This repository contains the **Django REST Framework backend API** for the Quizly platform.

Frontend Repository: 👉 **https://github.com/DrPinselbecher/Quizly_Frontend**

---

## 🚀 Features

- User registration
- User login with **JWT**
- Authentication via **HTTP-only cookies**
- Logout with **refresh token blacklist**
- Access token refresh via cookie
- Create quizzes from **YouTube URLs**
- Automatic YouTube audio download via **yt-dlp**
- Audio transcription via **Whisper AI**
- Quiz generation via **Google Gemini Flash**
- Store generated quizzes and questions in the database
- List only the authenticated user's quizzes
- Retrieve quiz details
- Update quiz title and description
- Delete quizzes
- Admin panel support for quizzes and questions
- Automated tests for auth and quiz modules

---

## 📦 Technologies & Requirements

| Technology | Version / Info |
|-----------|----------------|
| Python | 3.11.9 |
| Django | 5.1.8 |
| Django REST Framework | 3.15.2 |
| djangorestframework-simplejwt | 5.5.1 |
| django-cors-headers | 4.9.0 |
| python-dotenv | 1.2.2 |
| google-genai | 1.72.0 |
| openai-whisper | 20250625 |
| yt-dlp | 2026.3.17 |
| yt-dlp-ejs | 0.8.0 |
| Database | SQLite (default) |
| Development Environment | VS Code recommended |

---

## ⚠️ Required External Tools

### FFmpeg (required)

**FFmpeg must be installed globally**, because Whisper needs it to process audio files.

Check if FFmpeg is available:

~~~bash
ffmpeg -version
~~~

### Windows installation

~~~bash
winget install --id Gyan.FFmpeg -e --source winget
~~~

After installation, restart your terminal.

---

### Deno (recommended)

For newer YouTube extraction cases, **yt-dlp may require a JavaScript runtime**. Installing **Deno** is recommended for more stable YouTube downloads.

Check if Deno is available:

~~~bash
deno --version
~~~

### Windows installation

~~~bash
winget install DenoLand.Deno
~~~

After installation, restart your terminal.

---

## ⚙️ Installation & Setup

### ✅ 1. Clone the backend repository

~~~bash
git clone https://github.com/DrPinselbecher/Quizly_Backend
cd Quizly_Backend
~~~

---

### ✅ 2. Create and activate a virtual environment

#### Windows

~~~bash
py -3.11 -m venv venv
venv\Scripts\activate
~~~

#### macOS / Linux

~~~bash
python3.11 -m venv venv
source venv/bin/activate
~~~

---

### ✅ 3. Install dependencies

~~~bash
pip install -r requirements.txt
~~~

---

### ✅ 4. Create your local `.env` file

Create a file named `.env` in the same directory as `manage.py`.

Example:

~~~env
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

GEMINI_API_KEY=your_gemini_api_key_here

CORS_ALLOWED_ORIGINS=http://127.0.0.1:5500,http://localhost:5500,http://localhost:4200

WHISPER_MODEL=base
GEMINI_MODEL=gemini-2.5-flash
~~~

Generate a secure secret key:

~~~bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
~~~

Copy the generated value into `SECRET_KEY`.

---

### ✅ 5. Get a Gemini API key

Create your Gemini API key here:

`https://ai.google.dev/`

Then add it to your `.env` file:

~~~env
GEMINI_API_KEY=your_gemini_api_key_here
~~~

---

### ✅ 6. Run database migrations

~~~bash
python manage.py migrate
~~~

---

### ✅ 7. Create an admin user (optional)

~~~bash
python manage.py createsuperuser
~~~

---

### ✅ 8. Start the backend server

~~~bash
python manage.py runserver
~~~

Backend runs at:

👉 `http://127.0.0.1:8000/`

---

## 🌐 Frontend Setup

The frontend is a separate project.

Frontend Repository: 👉 **https://github.com/DrPinselbecher/Quizly_Frontend**

If your frontend runs on one of these origins:

- `http://127.0.0.1:5500`
- `http://localhost:5500`
- `http://localhost:4200`

the backend is already prepared for that via `CORS_ALLOWED_ORIGINS`.

---

## 🔐 Authentication

Authentication is handled with **JWT** and **HTTP-only cookies**.

### Register

**POST** `/api/register/`

Request body:

~~~json
{
  "username": "your_username",
  "email": "your_email@example.com",
  "password": "your_password",
  "confirmed_password": "your_password"
}
~~~

Success response:

~~~json
{
  "detail": "User created successfully!"
}
~~~

---

### Login

**POST** `/api/login/`

Request body:

~~~json
{
  "username": "your_username",
  "password": "your_password"
}
~~~

Success response:

~~~json
{
  "detail": "Login successfully!",
  "user": {
    "id": 1,
    "username": "your_username",
    "email": "your_email@example.com"
  }
}
~~~

#### Extra info

On login, the backend sets:

- `access_token` as **HTTP-only cookie**
- `refresh_token` as **HTTP-only cookie**

---

### Logout

**POST** `/api/logout/`

Success response:

~~~json
{
  "detail": "Log-Out successfully! All Tokens will be deleted. Refresh token is now invalid."
}
~~~

#### Extra info

- The refresh token is blacklisted
- Auth cookies are deleted

---

### Refresh Access Token

**POST** `/api/token/refresh/`

Success response:

~~~json
{
  "detail": "Token refreshed"
}
~~~

#### Extra info

- Reads the `refresh_token` from the cookie
- Sets a new `access_token` cookie

---

## 🧠 Quiz Generation Flow

When a user submits a YouTube URL:

1. The backend validates and normalizes the YouTube URL
2. The audio is downloaded using **yt-dlp**
3. The audio is transcribed using **Whisper AI**
4. The transcript is sent to **Gemini Flash**
5. Gemini returns structured quiz data
6. The backend validates the response
7. The quiz and questions are saved to the database

---

## 📦 Quiz API Endpoints

### Create Quiz

**POST** `/api/quizzes/`

Request body:

~~~json
{
  "url": "https://www.youtube.com/watch?v=example"
}
~~~

Success response:

~~~json
{
  "id": 1,
  "title": "Quiz Title",
  "description": "Quiz Description",
  "created_at": "2026-04-15T12:34:56.789Z",
  "updated_at": "2026-04-15T12:34:56.789Z",
  "video_url": "https://www.youtube.com/watch?v=example",
  "questions": [
    {
      "id": 1,
      "question_title": "Question 1",
      "question_options": [
        "Option A",
        "Option B",
        "Option C",
        "Option D"
      ],
      "answer": "Option A",
      "created_at": "2026-04-15T12:34:56.789Z",
      "updated_at": "2026-04-15T12:34:56.789Z"
    }
  ]
}
~~~

---

### Get All Own Quizzes

**GET** `/api/quizzes/`

Returns only quizzes of the authenticated user.

---

### Get Quiz Detail

**GET** `/api/quizzes/<id>/`

Returns one quiz of the authenticated user.

---

### Update Quiz

**PATCH** `/api/quizzes/<id>/`

Request body example:

~~~json
{
  "title": "Updated Title",
  "description": "Updated Description"
}
~~~

---

### Delete Quiz

**DELETE** `/api/quizzes/<id>/`

Deletes the selected quiz and all related questions.

---

## 🛠 Admin Panel

The admin panel supports:

- Editing quizzes
- Editing questions
- Inline question editing inside quiz admin

Open:

👉 `http://127.0.0.1:8000/admin/`

---

## 🧪 Testing

Run all tests:

~~~bash
python manage.py test
~~~

Run auth tests only:

~~~bash
python manage.py test user_auth_app
~~~

Run quiz tests only:

~~~bash
python manage.py test quiz_app
~~~

---

## 📄 Dependencies

Install all dependencies from:

~~~bash
pip install -r requirements.txt
~~~

Main packages used in this project:

- Django 5.1.8
- djangorestframework 3.15.2
- djangorestframework-simplejwt 5.5.1
- django-cors-headers 4.9.0
- python-dotenv 1.2.2
- google-genai 1.72.0
- openai-whisper 20250625
- yt-dlp 2026.3.17
- yt-dlp-ejs 0.8.0

> The exact full dependency list is maintained in `requirements.txt`.

---

## 👤 Author

Project: **QUIZLY**  
Developer: **René Theis**  
GitHub: `https://github.com/DrPinselbecher`

---

## 📌 Notes

- This backend is part of a full-stack portfolio project
- The frontend is provided separately
- **FFmpeg is required**
- **Deno is recommended**
- Authentication uses **JWT in HTTP-only cookies**
- The backend stores the canonical YouTube URL format:

~~~text
https://www.youtube.com/watch?v=VIDEO_ID
~~~