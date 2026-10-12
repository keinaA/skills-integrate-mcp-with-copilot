# Mergington High School Activities API

A super simple FastAPI application that allows students to view extracurricular activities. Teacher sign-in is required to register or unregister students.

## Features

- View all available extracurricular activities
- View registered participants
- Register and unregister students as an authenticated teacher

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   cd src
   export TEACHER_USERNAME=teacher
   export TEACHER_PASSWORD='choose-a-strong-password'
   export SESSION_SECRET="$(openssl rand -hex 32)"
   export COOKIE_SECURE=false
   uvicorn app:app --reload
   ```

   Set `COOKIE_SECURE=true` when serving the application over HTTPS. Teacher credentials and the signing secret are supplied through environment variables; do not commit real credentials or secrets. If authentication settings are missing or the signing secret is shorter than 32 characters, activities remain viewable but teacher sign-in and all registration changes are unavailable.

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                          |
| ------ | ----------------------------------------------------------------- | -------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get activities and their current participants (public)              |
| GET    | `/auth/me`                                                        | Get the current teacher login state                                  |
| POST   | `/auth/login`                                                     | Sign in with the configured teacher username and password            |
| POST   | `/auth/logout`                                                    | Sign out and clear the teacher session cookie                        |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher sign-in required)                        |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher sign-in required)                    |

Teacher sessions use a signed, HTTP-only cookie that expires after eight hours. The cookie uses `SameSite=Strict`; set `COOKIE_SECURE=true` in HTTPS deployments.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

Activity and participant data is stored in memory, which means it will be reset when the server restarts. This sample supports one configured teacher account through environment variables and does not provide teacher account management.
