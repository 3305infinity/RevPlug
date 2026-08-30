from typing import Any
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import JSONResponse

from app.api.deps import get_container
from app.db.container import PersistenceContainer
from app.domain.auth import hash_password, verify_password

router = APIRouter()

COOKIE_NAME = "recoveros_session"


def get_token_from_request(request: Request, authorization: str | None = None) -> str | None:
    """Extract session token from HTTP cookie or Bearer Authorization header."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    if authorization and authorization.startswith("Bearer "):
        return authorization.split("Bearer ")[1].strip()
    return None


def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    container: PersistenceContainer = Depends(get_container),
) -> Any | None:
    """FastAPI dependency to retrieve the current authenticated user."""
    token = get_token_from_request(request, authorization)
    if not token or not hasattr(container, "sessions") or container.sessions is None:
        return None
    session = container.sessions.get_session(token)
    if not session or not hasattr(container, "users") or container.users is None:
        return None
    user = container.users.get_by_id(session.user_id)
    return user


@router.post("/api/auth/signup")
async def api_signup(
    request: Request,
    response: Response,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    import json
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    full_name = str(body.get("full_name", "")).strip()

    if not email or "@" not in email:
        return JSONResponse(status_code=400, content={"error": "A valid email address is required"})
    if not full_name:
        return JSONResponse(status_code=400, content={"error": "Full name is required"})
    if len(password) < 6:
        return JSONResponse(status_code=400, content={"error": "Password must be at least 6 characters"})

    if not hasattr(container, "users") or container.users is None:
        return JSONResponse(status_code=500, content={"error": "User repository not configured"})

    existing = container.users.get_by_email(email)
    if existing:
        return JSONResponse(status_code=409, content={"error": "An account with this email already exists"})

    pwd_hash = hash_password(password)
    user = container.users.create_user(email=email, password_hash=pwd_hash, full_name=full_name)

    if not hasattr(container, "sessions") or container.sessions is None:
        return JSONResponse(status_code=500, content={"error": "Session repository not configured"})

    session = container.sessions.create_session(user.id)

    res = JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "message": "Account created successfully",
            "user": user.to_dict(),
            "session_token": session.session_token,
        },
    )
    res.set_cookie(
        key=COOKIE_NAME,
        value=session.session_token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return res


@router.post("/api/auth/login")
async def api_login(
    request: Request,
    response: Response,
    container: PersistenceContainer = Depends(get_container),
) -> Response:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))

    if not email or not password:
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    if not hasattr(container, "users") or container.users is None:
        return JSONResponse(status_code=500, content={"error": "User repository not configured"})

    user = container.users.get_by_email(email)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Invalid email or password"})

    if not verify_password(password, user.password_hash):
        return JSONResponse(status_code=401, content={"error": "Invalid email or password"})

    if not hasattr(container, "sessions") or container.sessions is None:
        return JSONResponse(status_code=500, content={"error": "Session repository not configured"})

    session = container.sessions.create_session(user.id)

    res = JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Logged in successfully",
            "user": user.to_dict(),
            "session_token": session.session_token,
        },
    )
    res.set_cookie(
        key=COOKIE_NAME,
        value=session.session_token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return res


@router.post("/api/auth/logout")
async def api_logout(
    request: Request,
    container: PersistenceContainer = Depends(get_container),
    authorization: str | None = Header(None),
) -> Response:
    token = get_token_from_request(request, authorization)
    if token and hasattr(container, "sessions") and container.sessions is not None:
        container.sessions.delete_session(token)

    res = JSONResponse(
        status_code=200,
        content={"status": "success", "message": "Logged out successfully"},
    )
    res.delete_cookie(COOKIE_NAME)
    return res


@router.get("/api/auth/me")
def api_me(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Response:
    if not current_user:
        return JSONResponse(status_code=401, content={"error": "Unauthenticated"})
    return JSONResponse(
        status_code=200,
        content={"status": "success", "user": current_user.to_dict()},
    )
