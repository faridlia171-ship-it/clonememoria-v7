import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer
from supabase import Client
from typing import Optional

from backend.core.security import create_access_token, verify_password, get_password_hash
from backend.db.client import get_db
from backend.schemas.user import UserCreate, UserLogin, UserResponse
from backend.schemas.tokens import TokenPair, RefreshTokenRequest
from backend.services.token_service import TokenService
from backend.api.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


def get_client_info(request: Request) -> dict:
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "device_info": {
            "user_agent": request.headers.get("user-agent"),
            "accept_language": request.headers.get("accept-language"),
            "origin": request.headers.get("origin")
        }
    }


def set_auth_cookies(response: Response, token_pair: TokenPair, secure: bool = False):
    response.set_cookie(
        key="access_token",
        value=token_pair.access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=1800
    )

    response.set_cookie(
        key="refresh_token",
        value=token_pair.refresh_token,
        httponly=True,
        secure=secure,
        samesite="strict",
        max_age=2592000
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    response: Response,
    db: Client = Depends(get_db)
):
    logger.info("REGISTRATION_ATTEMPT", extra={"email": user_data.email})

    existing = db.table("users").select("id").eq("email", user_data.email).maybeSingle().execute()

    if existing.data:
        logger.warning("REGISTRATION_FAILED_EMAIL_EXISTS", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    password_hash = get_password_hash(user_data.password)

    user_insert = {
        "email": user_data.email,
        "password_hash": password_hash,
        "full_name": user_data.full_name,
        "billing_plan": "free"
    }

    result = db.table("users").insert(user_insert).execute()

    if not result.data:
        logger.error("USER_CREATION_FAILED", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    user = result.data[0]
    user_id = user["id"]

    client_info = get_client_info(request)
    token_service = TokenService(db)

    token_pair = token_service.create_token_pair(
        user_id=user_id,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"]
    )

    db.rpc('log_auth_event', {
        'p_user_id': str(user_id),
        'p_event': 'user_register',
        'p_ip_address': client_info["ip_address"],
        'p_user_agent': client_info["user_agent"],
        'p_metadata': {"email": user["email"]}
    }).execute()

    set_auth_cookies(response, token_pair, secure=False)

    logger.info("USER_REGISTERED_SUCCESS", extra={
        "user_id": user_id,
        "email": user["email"]
    })

    user_response = UserResponse(**user)

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": "bearer",
        "expires_in": token_pair.expires_in,
        "user": user_response
    }


@router.post("/login")
async def login(
    credentials: UserLogin,
    request: Request,
    response: Response,
    db: Client = Depends(get_db)
):
    logger.info("LOGIN_ATTEMPT", extra={"email": credentials.email})

    result = db.table("users").select("*").eq("email", credentials.email).maybeSingle().execute()

    if not result.data:
        logger.warning("LOGIN_FAILED_USER_NOT_FOUND", extra={"email": credentials.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    user = result.data

    if not verify_password(credentials.password, user["password_hash"]):
        logger.warning("LOGIN_FAILED_INVALID_PASSWORD", extra={"email": credentials.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    user_id = user["id"]
    client_info = get_client_info(request)
    token_service = TokenService(db)

    token_pair = token_service.create_token_pair(
        user_id=user_id,
        ip_address=client_info["ip_address"],
        user_agent=client_info["user_agent"],
        device_info=client_info["device_info"]
    )

    db.rpc('log_auth_event', {
        'p_user_id': str(user_id),
        'p_event': 'user_login',
        'p_ip_address': client_info["ip_address"],
        'p_user_agent': client_info["user_agent"],
        'p_metadata': {"email": user["email"]}
    }).execute()

    set_auth_cookies(response, token_pair, secure=False)

    logger.info("LOGIN_SUCCESS", extra={
        "user_id": user_id,
        "email": user["email"]
    })

    user_response = UserResponse(**user)

    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": "bearer",
        "expires_in": token_pair.expires_in,
        "user": user_response
    }


@router.post("/refresh")
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    response: Response,
    db: Client = Depends(get_db)
):
    logger.info("TOKEN_REFRESH_ATTEMPT")

    client_info = get_client_info(request)
    token_service = TokenService(db)

    try:
        token_pair = token_service.refresh_access_token(
            refresh_token=refresh_request.refresh_token,
            ip_address=client_info["ip_address"],
            user_agent=client_info["user_agent"]
        )

        set_auth_cookies(response, token_pair, secure=False)

        logger.info("TOKEN_REFRESH_SUCCESS")

        return {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "token_type": "bearer",
            "expires_in": token_pair.expires_in
        }

    except Exception as e:
        logger.error(f"TOKEN_REFRESH_FAILED: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    user_id = current_user["id"]
    logger.info("LOGOUT_ATTEMPT", extra={"user_id": user_id})

    token_service = TokenService(db)
    revoked_count = token_service.revoke_all_user_tokens(
        user_id=user_id,
        reason="user_logout"
    )

    db.rpc('log_auth_event', {
        'p_user_id': str(user_id),
        'p_event': 'user_logout',
        'p_ip_address': None,
        'p_user_agent': None,
        'p_metadata': {"tokens_revoked": revoked_count}
    }).execute()

    clear_auth_cookies(response)

    logger.info("LOGOUT_SUCCESS", extra={
        "user_id": user_id,
        "tokens_revoked": revoked_count
    })

    return {
        "message": "Logged out successfully",
        "tokens_revoked": revoked_count
    }


@router.post("/revoke")
async def revoke_token(
    refresh_request: RefreshTokenRequest,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    user_id = current_user["id"]
    logger.info("TOKEN_REVOKE_ATTEMPT", extra={"user_id": user_id})

    token_service = TokenService(db)

    success = token_service.revoke_token(
        token=refresh_request.refresh_token,
        reason="manual_revoke"
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to revoke token"
        )

    db.rpc('log_auth_event', {
        'p_user_id': str(user_id),
        'p_event': 'token_revoked',
        'p_ip_address': None,
        'p_user_agent': None,
        'p_metadata': {"reason": "manual_revoke"}
    }).execute()

    logger.info("TOKEN_REVOKE_SUCCESS", extra={"user_id": user_id})

    return {"message": "Token revoked successfully"}


@router.get("/sessions")
async def get_sessions(
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    user_id = current_user["id"]
    logger.info("GET_SESSIONS_ATTEMPT", extra={"user_id": user_id})

    token_service = TokenService(db)
    sessions = token_service.get_user_sessions(user_id=user_id)

    return {
        "sessions": sessions,
        "total": len(sessions)
    }


@router.post("/logout-all")
async def logout_all(
    response: Response,
    current_user: dict = Depends(get_current_user),
    db: Client = Depends(get_db)
):
    user_id = current_user["id"]
    logger.info("LOGOUT_ALL_ATTEMPT", extra={"user_id": user_id})

    token_service = TokenService(db)
    revoked_count = token_service.revoke_all_user_tokens(
        user_id=user_id,
        reason="logout_all"
    )

    db.rpc('log_auth_event', {
        'p_user_id': str(user_id),
        'p_event': 'logout_all',
        'p_ip_address': None,
        'p_user_agent': None,
        'p_metadata': {"tokens_revoked": revoked_count}
    }).execute()

    clear_auth_cookies(response)

    logger.info("LOGOUT_ALL_SUCCESS", extra={
        "user_id": user_id,
        "tokens_revoked": revoked_count
    })

    return {
        "message": "All sessions logged out successfully",
        "tokens_revoked": revoked_count
    }


@router.get("/me")
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    return UserResponse(**current_user)
