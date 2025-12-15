@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Client = Depends(get_db)):
    logger.info("REGISTRATION_ATTEMPT", extra={"email": user_data.email})

    # SAFE query (no maybe_single)
    response = (
        db.table("users")
        .select("id")
        .eq("email", user_data.email)
        .limit(1)
        .execute()
    )

    if response.data and len(response.data) > 0:
        logger.warning("REGISTRATION_FAILED_EMAIL_EXISTS", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    password_hash = get_password_hash(user_data.password)

    insert = (
        db.table("users")
        .insert({
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name
        })
        .execute()
    )

    if not insert.data:
        logger.error("USER_CREATION_FAILED", extra={"email": user_data.email})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )

    user = insert.data[0]
    access_token = create_access_token({"sub": user["id"]})

    logger.info("USER_REGISTERED_SUCCESS", extra={"user_id": user["id"]})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(**user)
    )
