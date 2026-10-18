# app/config/social_config.py
# app/core/auth/services/social_auth_service.py
import secrets
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.env import env
from app.core.auth.services.service_auth import AuthService
from app.core.auth.services.service_token import TokenService
from app.core.users.models.model_user import UserModel
from app.utils.crud.types_crud import response_message
from app.utils.logger import log


class SocialAuthService(AuthService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    # Google OAuth Implementation
    def get_google_auth_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL"""
        params = {
            "client_id": env["social"]["google_client_id"],
            "redirect_uri":env["social"]["google_redirect_uri"],
            "scope": "openid email profile",
            "response_type": "code",
            "access_type": "offline",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/auth?{urlencode(params)}"

    async def authenticate_google_user(self, code: str, state: str) -> Dict[str, Any]:
        """Authenticate user with Google OAuth"""
        try:
            # Exchange code for access token
            token_data = await self._get_google_access_token(code)
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Failed to get access token",
                        success_status=False,
                        message="Google authentication failed",
                    ),
                )

            # Get user info from Google
            user_info = await self._get_google_user_info(token_data["access_token"])
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Failed to get user info",
                        success_status=False,
                        message="Google authentication failed",
                    ),
                )

            # Find or create user
            return await self._handle_social_user(user_info, "google")

        except Exception as e:
            log.logs.error(f"Google authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Google authentication failed",
                ),
            )

    async def _get_google_access_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": env["social"]["google_client_id"],
                "client_secret": env["social"]["google_client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": env["social"]["google_redirect_uri"],
            }

            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=data,
                headers={"Accept": "application/json"},
            )

            if response.status_code == 200:
                return response.json()
            return None

    async def _get_google_user_info(
        self, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get user information from Google"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 200:
                return response.json()
            return None

    # Facebook OAuth Implementation
    def get_facebook_auth_url(self, state: str) -> str:
        """Generate Facebook OAuth authorization URL"""
        params = {
            "client_id": env["social"]["facebook_client_id"],
            "redirect_uri": env["social"]["facebook_redirect_uri"],
            "scope": "email,public_profile",
            "response_type": "code",
            "state": state,
        }
        return f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"

    async def authenticate_facebook_user(self, code: str, state: str) -> Dict[str, Any]:
        """Authenticate user with Facebook OAuth"""
        try:
            # Exchange code for access token
            token_data = await self._get_facebook_access_token(code)
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Failed to get access token",
                        success_status=False,
                        message="Facebook authentication failed",
                    ),
                )

            # Get user info from Facebook
            user_info = await self._get_facebook_user_info(token_data["access_token"])
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Failed to get user info",
                        success_status=False,
                        message="Facebook authentication failed",
                    ),
                )

            # Find or create user
            return await self._handle_social_user(user_info, "facebook")

        except Exception as e:
            log.logs.error(f"Facebook authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="Facebook authentication failed",
                ),
            )

    async def _get_facebook_access_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            params = {
                "client_id": env["social"]["facebook_client_id"],
                "client_secret": env["social"]["facebook_client_secret"],
                "code": code,
                "redirect_uri": env["social"]["facebook_redirect_uri"],
            }

            response = await client.get(
                "https://graph.facebook.com/v18.0/oauth/access_token", params=params
            )

            if response.status_code == 200:
                return response.json()
            return None

    async def _get_facebook_user_info(
        self, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get user information from Facebook"""
        async with httpx.AsyncClient() as client:
            params = {
                "fields": "id,name,email,first_name,last_name,picture",
                "access_token": access_token,
            }

            response = await client.get("https://graph.facebook.com/me", params=params)

            if response.status_code == 200:
                return response.json()
            return None

    # GitHub OAuth Implementation
    def get_github_auth_url(self, state: str) -> str:
        """Generate GitHub OAuth authorization URL"""
        params = {
            "client_id": env["social"]["github_client_id"],
            "redirect_uri": env["social"]["github_redirect_uri"],
            "scope": "user:email",
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urlencode(params)}"

    async def authenticate_github_user(self, code: str, state: str) -> Dict[str, Any]:
        """Authenticate user with GitHub OAuth"""
        try:
            # Exchange code for access token
            token_data = await self._get_github_access_token(code)
            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Failed to get access token",
                        success_status=False,
                        message="GitHub authentication failed",
                    ),
                )

            # Get user info from GitHub
            user_info = await self._get_github_user_info(token_data["access_token"])
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Failed to get user info",
                        success_status=False,
                        message="GitHub authentication failed",
                    ),
                )

            # Get user email (GitHub might not return email in user info)
            user_email = await self._get_github_user_email(token_data["access_token"])
            if user_email:
                user_info["email"] = user_email

            # Find or create user
            return await self._handle_social_user(user_info, "github")

        except Exception as e:
            log.logs.error(f"GitHub authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error=str(e),
                    success_status=False,
                    message="GitHub authentication failed",
                ),
            )

    async def _get_github_access_token(self, code: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token"""
        async with httpx.AsyncClient() as client:
            data = {
                "client_id": env                ["social"]["github_client_id"],
                "client_secret": env["social"]["github_client_secret"],
                "code": code,
            }

            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data=data,
                headers={"Accept": "application/json"},
            )

            if response.status_code == 200:
                return response.json()
            return None

    async def _get_github_user_info(
        self, access_token: str
    ) -> Optional[Dict[str, Any]]:
        """Get user information from GitHub"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {access_token}"},
            )

            if response.status_code == 200:
                return response.json()
            return None

    async def _get_github_user_email(self, access_token: str) -> Optional[str]:
        """Get user email from GitHub (might be private)"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"token {access_token}"},
            )

            if response.status_code == 200:
                emails = response.json()
                # Get primary email
                for email in emails:
                    if email.get("primary") and email.get("verified"):
                        return email["email"]
                # Fallback to first verified email
                for email in emails:
                    if email.get("verified"):
                        return email["email"]
            return None

    # Common method to handle social user creation/login
    async def _handle_social_user(
        self, user_info: Dict[str, Any], provider: str
    ) -> Dict[str, Any]:
        """Handle social user creation or login"""
        try:
            email = user_info.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Email not provided by social provider",
                        success_status=False,
                        message="Email is required for authentication",
                    ),
                )

            # Check if user already exists
            stmt = select(UserModel).filter(UserModel.email == email)
            result = (await self.db.scalars(stmt)).one_or_none()

            if result:
                # User exists, update social login info if needed
                user = result
                # You might want to update user's social provider info here
            else:
                # Create new user
                user_data = self._extract_user_data_from_social(user_info, provider)
                user = await self.create_user(user_data=user_data)
                if  not  user:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=response_message(
                            error="Failed to create user",
                            success_status=False,
                            message="User creation failed",
                        ),
                    )
                

            # Generate JWT token
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=response_message(
                        error="User not found",
                        success_status=False,
                        message="Authentication failed",
                    ),
                )
            token = await TokenService.generate_auth_token(user.id, db=self.db)

            # Convert user to dict and remove password
            from app.utils.convert_sqlalchemy_dict import sqlalchemy_obj_to_dict

            user_dict = sqlalchemy_obj_to_dict(user)
            if isinstance(user_dict, dict):
                user_dict.pop("password", None)

            return {"user": user_dict, "token": token, "provider": provider}

        except Exception as e:
            log.logs.error(f"Error handling social user: {e}")
            raise e

    def _extract_user_data_from_social(
        self, user_info: Dict[str, Any], provider: str
    ) -> Any:
        """Extract user data from social provider response"""
        if provider == "google":
            return {
                "email": user_info["email"],
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
                "username": user_info["email"].split("@")[0],
                "password": secrets.token_urlsafe(32),  # Generate random password
                "is_verified": True,  # Social accounts are pre-verified
                "profile_picture": user_info.get("picture", ""),
            }
        elif provider == "facebook":
            return {
                "email": user_info["email"],
                "first_name": user_info.get("first_name", ""),
                "last_name": user_info.get("last_name", ""),
                "username": user_info["email"].split("@")[0],
                "password": secrets.token_urlsafe(32),
                "is_verified": True,
                "profile_picture": user_info.get("picture", {})
                .get("data", {})
                .get("url", ""),
            }
        elif provider == "github":
            return {
                "email": user_info["email"],
                "first_name": user_info.get("name", "").split(" ")[0]
                if user_info.get("name")
                else "",
                "last_name": " ".join(user_info.get("name", "").split(" ")[1:])
                if user_info.get("name")
                and len(user_info.get("name", "").split(" ")) > 1
                else "",
                "username": user_info.get("login", user_info["email"].split("@")[0]),
                "password": secrets.token_urlsafe(32),
                "is_verified": True,
                "profile_picture": user_info.get("avatar_url", ""),
            }
        else:
            raise ValueError(f"Unsupported provider: {provider}")
