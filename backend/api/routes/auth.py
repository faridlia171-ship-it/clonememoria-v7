import logging
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from backend.core.security import create_access_token, verify_password, get_password_hash
from backend.db.client import get_db
from backend.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from backend.api.deps import get_current_user_id

logger = logging.getLogger(__name__)
logger.info("AUTH_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Client = Depends(get_db)):
    logger.info("REGISTRATION_ATTEMPT", extra={"email": user_data.email})

    # SAFE QUERY — no maybe_single()
    result = db.table("users").select("id").eq("email", user_data.email).execute()

    if result.data and len(result.data) > 0:
        logger.warning("REGISTRATION_FAILED_EMAIL_EXISTS", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    password_hash = get_password_hash(user_data.password)

    insert_result = db.table("users").insert({
        "email": user_data.email,
        "password_hash": password_hash,
        "full_name": user_data.full_name
    }).execute()

    if not insert_result.data:
        logger.error("USER_CREATION_FAILED", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    user = insert_result.data[0]
    access_token = create_access_token({"sub": user["id"]})

    logger.info("USER_REGISTERED_SUCCESS", extra={"user_id": user["id"]})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**user)
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Client = Depends(get_db)):
    logger.info("LOGIN_ATTEMPT", extra={"email": credentials.email})

    result = db.table("users").select("*").eq("email", credentials.email).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    user = result.data[0]

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    access_token = create_access_token({"sub": user["id"]})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    result = db.table("users").select("*").eq("id", user_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(**result.data[0])
