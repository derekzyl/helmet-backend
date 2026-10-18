from datetime import datetime, timedelta
from typing import Any

import jwt

from app.config import env

jwt_secret: str = env.env['jwt']["jwt_secret"]


class MyJwt:
    def __init__(self):
        self.JWT_SECRET: str = jwt_secret
        # Remove self.IAT as it's not needed as instance variable

    def create_token(self, subject: str, token_type: str, expires_in: int):
        """
        This function creates a JWT token with specified subject, token type, and expiration time.
        
        :param subject: The `subject` parameter typically represents the entity to which the token is
        issued, such as a user ID or username. It helps identify the entity for which the token is generated
        :type subject: str
        :param token_type: The `token_type` parameter in the `create_token` function is used to specify the
        type of token being created. This could be a string indicating the purpose or nature of the token,
        such as "access_token", "refresh_token", "id_token", etc. It helps in identifying the token
        :type token_type: str
        :param expires_in: The `expires_in` parameter specifies the duration in minutes for which the token
        will be valid before it expires
        :type expires_in: int
        :return: The `create_token` method is returning a JWT token encoded with the payload containing the
        subject, token type, expiration time, issued at time, and algorithm information.
        """
        # Use UTC time consistently
        now = datetime.utcnow()
        expire = timedelta(minutes=expires_in)
        
        payload = {
            "sub": subject,
            "type": token_type,
            "iat": now,  # Issued at time (UTC)
            "exp": now + expire,  # Expiration time (UTC)
            "alg": "HS256"  # Note: This should not be in payload, it's in header
        }
        
        return jwt.encode(payload=payload, key=self.JWT_SECRET, algorithm="HS256")

    def verify_token(self, token: str) -> dict[str, Any]:
        """
        The function `verify_token` decodes a JWT token using a secret key and returns the decoded token as
        a dictionary. Now includes leeway to handle clock skew.
        
        :param token: A JWT token that needs to be verified
        :type token: str
        :return: A dictionary containing the decoded token is being returned.
        """
        try:
            # Add leeway to handle clock skew (60 seconds tolerance)
            decoded_token = jwt.decode(
                jwt=token, 
                key=self.JWT_SECRET, 
                algorithms=["HS256"],
                leeway=timedelta(seconds=60)  # 60 seconds leeway for clock skew
            )
            return decoded_token
        except jwt.ExpiredSignatureError:
            raise Exception("Token has expired")
        except jwt.InvalidTokenError as e:
            raise Exception(f"Invalid token: {str(e)}")
        except Exception as e:
            raise Exception(f"Token verification failed: {str(e)}")

    def decode_token_without_verification(self, token: str) -> dict[str, Any]:
        """
        Debug helper: Decode token without verification to inspect payload
        Useful for debugging timing issues
        
        :param token: JWT token to decode
        :type token: str
        :return: Decoded token payload
        """
        try:
            decoded_token = jwt.decode(
                jwt=token, 
                key=self.JWT_SECRET, 
                algorithms=["HS256"],
                options={"verify_signature": False, "verify_exp": False, "verify_iat": False}
            )
            return decoded_token
        except Exception as e:
            raise Exception(f"Token decoding failed: {str(e)}")

    def debug_token_timing(self, token: str) -> dict:
        """
        Debug helper to check token timing issues
        
        :param token: JWT token to debug
        :type token: str
        :return: Dictionary with timing information
        """
        try:
            payload = self.decode_token_without_verification(token)
            current_time = datetime.utcnow()
            current_timestamp = current_time.timestamp()
            
            debug_info = {
                "current_utc_time": current_time.isoformat(),
                "current_timestamp": current_timestamp,
                "payload": payload
            }
            
            if 'iat' in payload:
                iat_time = datetime.utcfromtimestamp(payload['iat'])
                debug_info.update({
                    "issued_at_utc": iat_time.isoformat(),
                    "issued_at_timestamp": payload['iat'],
                    "time_since_issued": current_timestamp - payload['iat']
                })
            
            if 'exp' in payload:
                exp_time = datetime.utcfromtimestamp(payload['exp'])
                debug_info.update({
                    "expires_at_utc": exp_time.isoformat(),
                    "expires_at_timestamp": payload['exp'],
                    "time_until_expiry": payload['exp'] - current_timestamp
                })
            
            return debug_info
            
        except Exception as e:
            return {"error": f"Debug failed: {str(e)}"}