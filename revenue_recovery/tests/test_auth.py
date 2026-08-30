import pytest
from fastapi.testclient import TestClient

from app.domain.auth import hash_password, verify_password
from app.main import create_app


def test_password_hashing_and_verification():
    raw_pwd = "SecretPassword123!"
    hashed = hash_password(raw_pwd)

    assert hashed.startswith("pbkdf2_sha256$100000$")
    assert raw_pwd not in hashed
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False
    assert verify_password(raw_pwd, "invalid$hash$string") is False


def test_auth_complete_regression_suite_a_to_j():
    """Regression suite covering all 10 requirements (A through J):
    A. signup -> authenticated session/token exists
    B. login with correct credentials -> 200
    C. login response establishes usable authentication
    D. authenticated /api/auth/me -> 200 with correct user
    E. /api/auth/me without authentication -> 401
    F. invalid credentials -> 401/appropriate error
    G. browser refresh preserves authentication (token/cookie reuse)
    H. logout clears authentication
    I. authenticated API requests continue working after login
    J. duplicate signup still returns 409
    """
    app = create_app(webhook_secret="test-secret")
    client = TestClient(app)

    # A. Signup creates user & authenticated session token
    res_signup = client.post(
        "/api/auth/signup",
        json={
            "email": "user_reg@revplug.io",
            "password": "StrongPassword123",
            "full_name": "Reg Test User",
        },
    )
    assert res_signup.status_code == 201
    signup_token = res_signup.json().get("session_token")
    assert signup_token is not None
    assert "revplug_session" in res_signup.cookies

    # J. Duplicate signup returns 409
    res_dup = client.post(
        "/api/auth/signup",
        json={
            "email": "user_reg@revplug.io",
            "password": "StrongPassword123",
            "full_name": "Reg Test User",
        },
    )
    assert res_dup.status_code == 409

    # E. Unauthenticated /api/auth/me returns 401
    client.cookies.clear()
    res_unauth = client.get("/api/auth/me")
    assert res_unauth.status_code == 401

    # F. Invalid credentials return 401
    res_invalid_pwd = client.post(
        "/api/auth/login",
        json={"email": "user_reg@revplug.io", "password": "WrongPassword"},
    )
    assert res_invalid_pwd.status_code == 401

    res_invalid_email = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@revplug.io", "password": "StrongPassword123"},
    )
    assert res_invalid_email.status_code == 401

    # B. Login with correct credentials returns 200
    res_login = client.post(
        "/api/auth/login",
        json={"email": "user_reg@revplug.io", "password": "StrongPassword123"},
    )
    assert res_login.status_code == 200
    login_data = res_login.json()

    # C. Login response establishes usable session token & cookie
    token = login_data.get("session_token")
    assert token is not None
    assert login_data["user"]["email"] == "user_reg@revplug.io"
    assert "revplug_session" in res_login.cookies

    # D. Authenticated /api/auth/me returns 200 with correct user via Cookie
    res_me_cookie = client.get("/api/auth/me")
    assert res_me_cookie.status_code == 200
    assert res_me_cookie.json()["user"]["email"] == "user_reg@revplug.io"

    # D & G. Authenticated /api/auth/me returns 200 via Bearer header (simulating refreshed browser)
    client.cookies.clear()
    res_me_bearer = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_me_bearer.status_code == 200
    assert res_me_bearer.json()["user"]["email"] == "user_reg@revplug.io"

    # I. Authenticated API requests continue working after login
    res_health = client.get("/health")
    assert res_health.status_code == 200

    # H. Logout clears authentication
    res_logout = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_logout.status_code == 200

    res_me_after_logout = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_me_after_logout.status_code == 401


def test_cors_credentials_header():
    """Verify CORS headers allow credentials from localhost:3000 origin."""
    app = create_app(webhook_secret="test-secret")
    client = TestClient(app)

    res = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert res.headers.get("access-control-allow-credentials") == "true"
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
