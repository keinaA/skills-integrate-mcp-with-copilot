import os
import sys
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException, Request, Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import (  # noqa: E402
    SESSION_COOKIE_NAME,
    SESSION_DURATION_SECONDS,
    app,
    create_session_token,
    get_activities,
    is_valid_session,
    login,
    require_teacher,
)
from app import LoginCredentials  # noqa: E402


TEACHER_SETTINGS = {
    "TEACHER_USERNAME": "staff",
    "TEACHER_PASSWORD": "a-long-test-password",
    "SESSION_SECRET": "test-session-secret-that-is-at-least-32-bytes",
}


def make_request(cookie: str | None = None) -> Request:
    headers = []
    if cookie is not None:
        headers.append((b"cookie", cookie.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/",
            "headers": headers,
        }
    )


class TeacherAuthenticationTests(unittest.TestCase):
    def test_unconfigured_authentication_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as context:
                require_teacher(make_request())

        self.assertEqual(context.exception.status_code, 503)

    def test_missing_or_invalid_session_is_rejected(self):
        with patch.dict(os.environ, TEACHER_SETTINGS, clear=True):
            for request in (make_request(), make_request("teacher_session=invalid")):
                with self.subTest(request=request):
                    with self.assertRaises(HTTPException) as context:
                        require_teacher(request)
                    self.assertEqual(context.exception.status_code, 401)

    def test_valid_login_sets_http_only_session_cookie(self):
        with patch.dict(os.environ, TEACHER_SETTINGS, clear=True):
            response = Response()
            result = login(
                LoginCredentials(username="staff", password="a-long-test-password"),
                response,
            )

            cookie = SimpleCookie()
            cookie.load(response.headers["set-cookie"])
            token = cookie[SESSION_COOKIE_NAME].value

            self.assertEqual(result["username"], "staff")
            self.assertTrue(cookie[SESSION_COOKIE_NAME]["httponly"])
            self.assertEqual(cookie[SESSION_COOKIE_NAME]["samesite"], "strict")
            self.assertTrue(
                is_valid_session(
                    token,
                    "staff",
                    TEACHER_SETTINGS["SESSION_SECRET"],
                )
            )
            self.assertEqual(require_teacher(make_request(f"{SESSION_COOKIE_NAME}={token}")), "staff")

    def test_login_rejects_wrong_password(self):
        with patch.dict(os.environ, TEACHER_SETTINGS, clear=True):
            with self.assertRaises(HTTPException) as context:
                login(
                    LoginCredentials(username="staff", password="wrong-password"),
                    Response(),
                )

        self.assertEqual(context.exception.status_code, 401)

    def test_expired_and_tampered_tokens_are_rejected(self):
        with patch.dict(os.environ, TEACHER_SETTINGS, clear=True):
            with patch("app.time.time", return_value=1000):
                token = create_session_token(
                    "staff", TEACHER_SETTINGS["SESSION_SECRET"]
                )

            with patch(
                "app.time.time",
                return_value=1000 + SESSION_DURATION_SECONDS,
            ):
                self.assertFalse(
                    is_valid_session(
                        token,
                        "staff",
                        TEACHER_SETTINGS["SESSION_SECRET"],
                    )
                )

            self.assertFalse(
                is_valid_session(
                    token + "tampered",
                    "staff",
                    TEACHER_SETTINGS["SESSION_SECRET"],
                )
            )

    def test_registration_routes_require_teacher_dependency(self):
        protected_paths = {
            "/activities/{activity_name}/signup",
            "/activities/{activity_name}/unregister",
        }
        routes = {
            route.path: route
            for route in app.routes
            if getattr(route, "path", None) in protected_paths
        }

        self.assertEqual(set(routes), protected_paths)
        for route in routes.values():
            with self.subTest(path=route.path):
                self.assertTrue(
                    any(
                        dependency.call is require_teacher
                        for dependency in route.dependant.dependencies
                    )
                )

    def test_activities_remain_publicly_viewable(self):
        route = next(
            route
            for route in app.routes
            if getattr(route, "path", None) == "/activities"
        )

        self.assertEqual(route.dependant.dependencies, [])
        self.assertIn("Chess Club", get_activities())
        self.assertIn("participants", get_activities()["Chess Club"])


if __name__ == "__main__":
    unittest.main()
