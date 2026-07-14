import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, RefreshToken

@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient, db_session: AsyncSession):
    # Test registration succeeds
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "securepassword123"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Check that refresh token cookie was set
    assert "refresh_token" in client.cookies

    # Verify user in database
    result = await db_session.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalars().first()
    assert user is not None
    assert user.email == "test@example.com"

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    # First registration
    await client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "securepassword123"}
    )
    
    # Duplicate registration
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "anotherpassword"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Email is already registered"

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "securepassword123"}
    )
    
    # Clear cookies to simulate clean login
    client.cookies.clear()

    # Attempt login
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "securepassword123"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in client.cookies

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    # Register user
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wronglogin@example.com", "password": "securepassword123"}
    )
    
    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wronglogin@example.com", "password": "incorrectpassword"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "access_token" not in response.json()

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_replay_detection(client: AsyncClient, db_session: AsyncSession):
    # 1. Register and login
    await client.post(
        "/api/v1/auth/register",
        json={"email": "rotation@example.com", "password": "securepassword123"}
    )
    
    first_refresh_token = client.cookies.get("refresh_token")
    assert first_refresh_token is not None

    # 2. Trigger a refresh (RTR rotates tokens)
    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == status.HTTP_200_OK
    
    second_refresh_token = client.cookies.get("refresh_token")
    assert second_refresh_token is not None
    assert second_refresh_token != first_refresh_token  # Verify rotation

    # 3. Simulate Replay Attack by sending the FIRST refresh token again
    client.cookies.set("refresh_token", first_refresh_token)
    replay_response = await client.post("/api/v1/auth/refresh")
    
    # Expect 401 unauthorized
    assert replay_response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Session compromised" in replay_response.json()["detail"]

    # Verify that all refresh tokens for this user have been revoked
    # Query all refresh tokens in DB
    result = await db_session.execute(select(RefreshToken))
    tokens = result.scalars().all()
    for t in tokens:
        assert t.revoked_at is not None

@pytest.mark.asyncio
async def test_logout(client: AsyncClient, db_session: AsyncSession):
    import hashlib
    from app.models import RefreshToken

    await client.post(
        "/api/v1/auth/register",
        json={"email": "logout@example.com", "password": "securepassword123"}
    )

    raw_refresh = client.cookies.get("refresh_token")
    assert raw_refresh is not None

    # Logout
    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == status.HTTP_204_NO_CONTENT

    # Verify the token is marked as revoked in the database (more meaningful than cookie header check)
    token_hash = hashlib.sha256(raw_refresh.encode()).hexdigest()
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    db_token = result.scalars().first()
    assert db_token is not None
    assert db_token.revoked_at is not None
