import random
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import env
from app.config.config import TokenType
from app.core.auth.models.model_token import TokenModel
from app.core.auth.types.types_token import SaveTokenData
from app.utils.crud.migration_helper import HybridCrudService as CrudService
from app.utils.crud.types_crud import response_message
from app.utils.logger.log import logs
from app.utils.my_jwt import MyJwt

jwt = MyJwt()
security = HTTPBearer()

class TokenService:
    def __init__(self, db:AsyncSession) -> None:
        self.db = db
        self.crud_service = CrudService(db=db, model=TokenModel) 

        
    async def get_all_tokens(self):
       data = await self.crud_service.get_many({})
       return data
        
    
    @staticmethod
    def generate_token (user_id:str, token_type:str ,expires_in:int) -> str:
        return jwt.create_token(subject=user_id,token_type=token_type, expires_in=expires_in)

    @staticmethod
    def generate_otp_token(otp_length:int=6) -> int:
        """Generate OTP token as an integer with fixed digits"""
        lower = 10 ** (otp_length - 1)
        upper = 10**otp_length - 1
        return random.randint(lower, upper)
    
    @staticmethod
    async def save_token(data:SaveTokenData, db:AsyncSession):
        get_existing_token = await CrudService(db=db, model=TokenModel).get_one(data={"user_id":data['user_id'], "type":data['type']})  

        # Blacklist existing token if it exists
        # logs.info(f"get_existing_token==========>>>: {get_existing_token}")
     
        if "data" in get_existing_token and get_existing_token["data"] is not None: 
            existing_token:TokenModel = get_existing_token['data']
            # Handle both SQLAlchemy objects and cached dictionaries
            if isinstance(existing_token, dict):
                dict_existing_token = existing_token
            else:
                dict_existing_token = existing_token.to_dict()
            await CrudService(db=db, model=TokenModel).delete(filter={"id":dict_existing_token['id']})
            # logs.info(f"delete_existing_token==========>>>: {delete_existing_token}")
            
        
        # Handle expires field properly
        if isinstance(data['expires'], str):
            # If expires is already a string (formatted datetime), use it directly
            expires_str = data['expires']
        elif isinstance(data['expires'], (int, float)):
            # If expires is minutes, calculate the datetime
            expires_datetime = datetime.now() + timedelta(minutes=int(data['expires']))
            expires_str = expires_datetime.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(data['expires'], datetime):
            # If expires is a datetime object, format it
            expires_str = data['expires'].strftime("%Y-%m-%d %H:%M:%S")
        else:
            # Default case - assume it's minutes
            expires_datetime = datetime.now() + timedelta(minutes=30)  # 30 minutes default
            expires_str = expires_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        # Update the data with properly formatted expires
        data['expires'] = expires_str
        
        token_data = TokenModel(**data)
        db.add(token_data)
        await db.commit()
        await db.refresh(token_data)
        
        return token_data
    
    @staticmethod
    async def verify_token(token:str, type:TokenType, db:AsyncSession):
        token_data = jwt.verify_token(token=token)
        logs.info(f"token_data in verify_token: {token_data}")

        if isinstance(token_data['sub'], str)==False:
            raise HTTPException(
                status_code=400,
                detail=response_message(error="Invalid token", success_status=False, message="Invalid token")
            )
        try:
            token_model = await CrudService(db=db, model=TokenModel).get_one({
                "user_id": token_data['sub'],
                "type": type.value,
                "blacklisted": False
                })

            if token_model is None or  "data" not in token_model:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(error="Invalid token", success_status=False, message="Invalid token")
                )
            token_:TokenModel = token_model.get("data")

            # Handle both SQLAlchemy objects and cached dictionaries
            if isinstance(token_, dict):
                token_dict = token_
            else:
                token_dict = token_.to_dict()
            # logs.info(f"token_dict in verify_token: {token_dict}")
            await CrudService(db=db, model=TokenModel).delete(filter={"id":token_dict['id']})
            # logs.info(f"delete_token in verify_token: {delete_token}")
            return token_dict    
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=response_message(error=e, success_status=False, message="Invalid token")
            )    

    @staticmethod
    async def verify_jwt_token(token:str):
        # logs.info(f"token_data: {token}")
        token_data = jwt.verify_token(token=token)
        # logs.info(f"token_data: {token_data}")

        if isinstance(token_data['sub'], str)==False:
            raise HTTPException(
                status_code=400,
                detail=response_message(error="Invalid token", success_status=False, message="Invalid token")
            )
        try:
            # check if token has expired
            token_time = token_data['exp']
           
            if datetime.fromtimestamp(token_time) < datetime.now():
                raise HTTPException(
                    status_code=400,
                    detail=response_message(error="Invalid token", success_status=False, message="Invalid token")
                )

            return token_data["sub"]   
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=response_message(error=e, success_status=False, message="Invalid token")
            )    

    @staticmethod
    async def verify_otp_token(token: str, user_id: str, type: TokenType, db: AsyncSession):
        try:
            # Use proper query instead of get_one with multiple conditions
            stmt = select(TokenModel).where(
                TokenModel.user_id == user_id,
                TokenModel.type == type.value,
                TokenModel.blacklisted == False,
                TokenModel.token == token
            )
            result = await db.execute(stmt)
            token_data = result.scalar_one_or_none()
            
            # Check if token exists
            if token_data is None:
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="Invalid token", 
                        success_status=False, 
                        message="Token not found or already used"
                    )
                )

            # Check if token is expired
            if datetime.strptime(token_data.expires, "%Y-%m-%d %H:%M:%S") < datetime.now():
                raise HTTPException(
                    status_code=400,
                    detail=response_message(
                        error="Token expired", 
                        success_status=False, 
                        message="Verification token has expired"
                    )
                )   

            # Only blacklist the token after validation
            stmt = update(TokenModel).values(blacklisted=True).where(TokenModel.id == token_data.id)
            await db.execute(stmt)
            await db.commit()  # Don't forget to commit the blacklist update
            
            return token_data
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logs.error(f"Error in verify_otp_token: {e}")
            raise HTTPException(
                status_code=400,
                detail=response_message(
                    error="Token verification failed", 
                    success_status=False, 
                    message="Invalid token"
                )
            )
    @staticmethod
    async def generate_auth_token(user_id:str, db:AsyncSession):
        # logs.info(f"user_id in generate_auth_token: {user_id}")
        access_expiry_time = datetime.now() + timedelta(minutes=env.env['jwt']['jwt_access_expiry_time'])
        refresh_expiry_time = datetime.now() + timedelta(minutes=env.env['jwt']['jwt_refresh_expiry_time'])

        access_token = MyJwt().create_token(subject=user_id, token_type=TokenType.ACCESS_TOKEN.value, expires_in=env.env['jwt']['jwt_access_expiry_time'])
        refresh_token = MyJwt().create_token(subject=user_id, token_type=TokenType.REFRESH_TOKEN.value, expires_in=env.env['jwt']['jwt_refresh_expiry_time'])
        
      
        
        # Pass the datetime object directly, let save_token handle the formatting
        # logs.info(f"refresh_expiry_time in generate_auth_token: {refresh_token}")
        await TokenService.save_token(data={
            "token": refresh_token,
            "expires": refresh_expiry_time.strftime("%Y-%m-%d %H:%M:%S"),
            "type": TokenType.REFRESH_TOKEN.value,
            "user_id": user_id,
            "blacklisted": False
        }, db=db)
        
        # logs.info(f"Save refresh token ==========>>>: {save_refresh_token}")
        
        return {
            "access": {"token": access_token, "expires": access_expiry_time.strftime("%Y-%m-%d %H:%M:%S")},
            "refresh": {"token": refresh_token, "expires": refresh_expiry_time.strftime("%Y-%m-%d %H:%M:%S")}
        }

    @staticmethod
    async def refresh_auth_token(refresh_token:str, db:AsyncSession):
        get_user = await TokenService.verify_token(token=refresh_token, type=TokenType.REFRESH_TOKEN, db=db)
       
        # logs.info(f"generate_user_token in refresh_auth_token: {get_user}")
        generate_user_token = await TokenService.generate_auth_token(user_id=get_user['user_id'], db=db)  # Use user_id instead of id
        return generate_user_token

    @staticmethod
    async def get_refresh_token(
        credentials: HTTPAuthorizationCredentials = Depends(security),
    ) -> str:
        """
        Extract refresh token from Authorization header
        Expected format: Authorization: Bearer <refresh_token>
        """
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=response_message(
                    error="Missing token",
                    success_status=False,
                    message="Authorization token is required",
                ),
            )

        if not credentials.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=response_message(
                    error="Invalid token format",
                    success_status=False,
                    message="Token cannot be empty",
                ),
            )

        return credentials.credentials