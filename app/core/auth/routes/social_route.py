# app/core/auth/routes/social_auth_routes.py
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.auth.services.middleware_auth import response_message
from app.core.auth.services.social_auth import SocialAuthService
from app.utils.logger import log

social_auth_router = APIRouter()

# In-memory state storage (use Redis in production)
auth_states = {}


@social_auth_router.get("/google/login")
async def google_login(db: AsyncSession = Depends(get_db)):
    """Initiate Google OAuth login"""
    state = secrets.token_urlsafe(32)
    auth_states[state] = "google"

    service = SocialAuthService(db=db)  # No DB needed for URL generation
    auth_url = service.get_google_auth_url(state)

    return RedirectResponse(url=auth_url)


@social_auth_router.get("/google/callback")
async def google_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    error: Annotated[str, Query()]|None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback"""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_message(
                error=error,
                success_status=False,
                message="Google authentication failed",
            ),
        )

    # Validate state
    if state not in auth_states or auth_states[state] != "google":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_message(
                error="Invalid state parameter",
                success_status=False,
                message="Authentication failed",
            ),
        )

    # Remove used state
    del auth_states[state]

    try:
        service = SocialAuthService(db=db)
        result = await service.authenticate_google_user(code, state)

        log.logs.info(f"Google login successful for user: {result['user']['email']}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_message(
                data=result,
                success_status=True,
                message="Google authentication successful",
            ),
        )
    except Exception as e:
        log.logs.error(f"Google callback error: {e}")
        raise e


@social_auth_router.get("/facebook/login")
async def facebook_login(db: AsyncSession = Depends(get_db)):
    """Initiate Facebook OAuth login"""
    state = secrets.token_urlsafe(32)
    auth_states[state] = "facebook"

    service = SocialAuthService(db=db)
    auth_url = service.get_facebook_auth_url(state)

    return RedirectResponse(url=auth_url)


@social_auth_router.get("/facebook/callback")
async def facebook_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    error: Annotated[str, Query()]|None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle Facebook OAuth callback"""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_message(
                error=error,
                success_status=False,
                message="Facebook authentication failed",
            ),
        )

    # Validate state
    if state not in auth_states or auth_states[state] != "facebook":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_message(
                error="Invalid state parameter",
                success_status=False,
                message="Authentication failed",
            ),
        )

    # Remove used state
    del auth_states[state]

    try:
        service = SocialAuthService(db=db)
        result = await service.authenticate_facebook_user(code, state)

        log.logs.info(f"Facebook login successful for user: {result['user']['email']}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_message(
                data=result,
                success_status=True,
                message="Facebook authentication successful",
            ),
        )
    except Exception as e:
        log.logs.error(f"Facebook callback error: {e}")
        raise e


@social_auth_router.get("/github/login")
async def github_login(db: AsyncSession = Depends(get_db)):
    """Initiate GitHub OAuth login"""
    state = secrets.token_urlsafe(32)
    auth_states[state] = "github"

    service = SocialAuthService(db=db)
    auth_url = service.get_github_auth_url(state)

    return RedirectResponse(url=auth_url)


@social_auth_router.get("/github/callback")
async def github_callback(
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    error: Annotated[str, Query()]|None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth callback"""
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_message(
                error=error,
                success_status=False,
                message="GitHub authentication failed",
            ),
        )

    # Validate state
    if state not in auth_states or auth_states[state] != "github":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response_message(
                error="Invalid state parameter",
                success_status=False,
                message="Authentication failed",
            ),
        )

    # Remove used state
    del auth_states[state]

    try:
        service = SocialAuthService(db=db)
        result = await service.authenticate_github_user(code, state)

        log.logs.info(f"GitHub login successful for user: {result['user']['email']}")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_message(
                data=result,
                success_status=True,
                message="GitHub authentication successful",
            ),
        )
    except Exception as e:
        log.logs.error(f"GitHub callback error: {e}")
        raise e
