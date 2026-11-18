import unittest

from fastapi import HTTPException

from src.app import (
    ADMIN_SESSION_COOKIE,
    admin_logout,
    admin_sessions,
    load_teachers,
    require_admin,
    verify_password,
)


class AdminModeTests(unittest.TestCase):
    def setUp(self):
        admin_sessions.clear()

    def tearDown(self):
        admin_sessions.clear()

    def test_teacher_password_is_verified_from_json(self):
        teacher = load_teachers()[0]

        self.assertTrue(verify_password("Mergington2026!", teacher))
        self.assertFalse(verify_password("wrong-password", teacher))

    def test_require_admin_rejects_missing_session(self):
        with self.assertRaises(HTTPException) as error:
            require_admin(None)

        self.assertEqual(error.exception.status_code, 401)

    def test_require_admin_accepts_valid_session(self):
        import time

        token = "valid-session"
        admin_sessions[token] = {
            "username": "teacher",
            "expires_at": time.time() + 60,
        }

        self.assertEqual(require_admin(token), "teacher")

    def test_logout_removes_session_cookie(self):
        from fastapi import Response

        token = "session-to-remove"
        admin_sessions[token] = {
            "username": "teacher",
            "expires_at": 0,
        }
        response = Response()

        admin_logout(response, token)

        self.assertNotIn(token, admin_sessions)
        self.assertIn(
            f"{ADMIN_SESSION_COOKIE}=",
            response.headers["set-cookie"],
        )


if __name__ == "__main__":
    unittest.main()
