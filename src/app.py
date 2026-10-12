"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import base64
import binascii
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

SESSION_COOKIE_NAME = "teacher_session"
SESSION_DURATION_SECONDS = 8 * 60 * 60


class LoginCredentials(BaseModel):
    username: str
    password: str


def get_auth_settings() -> tuple[str, str, str] | None:
    username = os.getenv("TEACHER_USERNAME")
    password = os.getenv("TEACHER_PASSWORD")
    secret = os.getenv("SESSION_SECRET")
    if not username or not password or not secret or len(secret) < 32:
        return None
    return username, password, secret


def create_session_token(username: str, secret: str) -> str:
    payload = json.dumps(
        {
            "username": username,
            "expires_at": int(time.time()) + SESSION_DURATION_SECONDS,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode()
    encoded_payload = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(
        secret.encode(), encoded_payload.encode(), hashlib.sha256
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def is_valid_session(token: str | None, username: str, secret: str) -> bool:
    if not token:
        return False

    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        expected_signature = hmac.new(
            secret.encode(), encoded_payload.encode(), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            return False

        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        session = json.loads(payload)
        if not isinstance(session, dict):
            return False
        expires_at = session.get("expires_at", 0)
        return (
            session.get("username") == username
            and isinstance(expires_at, int)
            and not isinstance(expires_at, bool)
            and expires_at > int(time.time())
        )
    except (ValueError, TypeError, binascii.Error, json.JSONDecodeError):
        return False


def require_teacher(request: Request) -> str:
    settings = get_auth_settings()
    if settings is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Teacher access is not configured. Set TEACHER_USERNAME, "
                "TEACHER_PASSWORD, and a SESSION_SECRET of at least 32 characters."
            ),
        )

    username, _, secret = settings
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not is_valid_session(token, username, secret):
        raise HTTPException(status_code=401, detail="Teacher login required")
    return username


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/me")
def get_current_user(request: Request):
    settings = get_auth_settings()
    if settings is None:
        return {"authenticated": False, "configured": False}

    username, _, secret = settings
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if is_valid_session(token, username, secret):
        return {"authenticated": True, "configured": True, "username": username}
    return {"authenticated": False, "configured": True}


@app.post("/auth/login")
def login(credentials: LoginCredentials, response: Response):
    settings = get_auth_settings()
    if settings is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Teacher access is not configured. Set TEACHER_USERNAME, "
                "TEACHER_PASSWORD, and a SESSION_SECRET of at least 32 characters."
            ),
        )

    username, password, secret = settings
    username_matches = hmac.compare_digest(
        credentials.username.encode(), username.encode()
    )
    password_matches = hmac.compare_digest(
        credentials.password.encode(), password.encode()
    )
    if not (username_matches and password_matches):
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=create_session_token(username, secret),
        max_age=SESSION_DURATION_SECONDS,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed in", "username": username}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "").lower() == "true",
        samesite="strict",
        path="/",
    )
    return {"message": "Signed out"}


@app.post(
    "/activities/{activity_name}/signup",
    dependencies=[Depends(require_teacher)],
)
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete(
    "/activities/{activity_name}/unregister",
    dependencies=[Depends(require_teacher)],
)
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
