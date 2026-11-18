"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import time

from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

ADMIN_SESSION_COOKIE = "mergington_admin_session"
ADMIN_SESSION_MAX_AGE = 8 * 60 * 60
admin_sessions: dict[str, dict[str, float | str]] = {}


class AdminLogin(BaseModel):
    username: str
    password: str


def load_teachers() -> list[dict[str, str | int]]:
    teachers_path = current_dir / "teachers.json"
    try:
        with teachers_path.open(encoding="utf-8") as teachers_file:
            teachers = json.load(teachers_file)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to load teacher credentials: {error}") from error

    if not isinstance(teachers, list):
        raise RuntimeError("Teacher credentials must be a JSON list")

    return teachers


def verify_password(password: str, teacher: dict[str, str | int]) -> bool:
    try:
        salt = bytes.fromhex(str(teacher["salt"]))
        expected_hash = str(teacher["password_hash"])
        iterations = int(teacher["iterations"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("Teacher credential entry is invalid") from error

    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, iterations
    ).hex()
    return hmac.compare_digest(password_hash, expected_hash)


def require_admin(
    admin_session: str | None = Cookie(default=None, alias=ADMIN_SESSION_COOKIE),
) -> str:
    session = admin_sessions.get(admin_session or "")
    if not session or float(session["expires_at"]) < time.time():
        if admin_session:
            admin_sessions.pop(admin_session, None)
        raise HTTPException(status_code=401, detail="Teacher login required")
    return str(session["username"])


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


@app.post("/admin/login")
def admin_login(credentials: AdminLogin, request: Request, response: Response):
    teacher = next(
        (
            teacher
            for teacher in load_teachers()
            if teacher.get("username") == credentials.username
        ),
        None,
    )
    if not teacher or not verify_password(credentials.password, teacher):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    admin_sessions[token] = {
        "username": credentials.username,
        "expires_at": time.time() + ADMIN_SESSION_MAX_AGE,
    }
    response.set_cookie(
        key=ADMIN_SESSION_COOKIE,
        value=token,
        max_age=ADMIN_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=request.url.scheme == "https",
    )
    return {"message": "Logged in successfully", "username": credentials.username}


@app.post("/admin/logout")
def admin_logout(
    response: Response,
    admin_session: str | None = Cookie(default=None, alias=ADMIN_SESSION_COOKIE),
):
    if admin_session:
        admin_sessions.pop(admin_session, None)
    response.delete_cookie(ADMIN_SESSION_COOKIE)
    return {"message": "Logged out successfully"}


@app.get("/admin/session")
def admin_session(username: str = Depends(require_admin)):
    return {"authenticated": True, "username": username}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_admin),
):
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


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    _: str = Depends(require_admin),
):
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
