from typing import TypedDict

from pydantic_settings import BaseSettings, SettingsConfigDict


class Mail_Env_Type(TypedDict):
    mail_server:str
    mail_port:int
    mail_username:str
    mail_password:str
    use_credentials:bool
    mail_use_ssl:bool
    mail_use_tls:bool
    mail_sender:str
    mail_sender_name:str
    use_mail_service:bool



class Social_Env_Type(TypedDict):
    google_client_id:str
    google_client_secret:str
    google_redirect_uri:str
    facebook_client_id:str
    facebook_client_secret:str
    facebook_redirect_uri:str
    github_client_id:str
    github_client_secret:str
    github_redirect_uri:str

    
    
  
class JWT_Env_Type(TypedDict):
    jwt_secret: str
    jwt_access_expiry_time:int
    jwt_refresh_expiry_time: int
    jwt_expiry_time:str


class Cloudinary_Env_Type(TypedDict):
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

class Payment_Env_Type(TypedDict):
    paystack_secret_key: str
    paystack_public_key: str
    flutterwave_secret_key: str
    flutterwave_public_key: str
    stripe_secret_key: str
    stripe_public_key: str
    payment_callback_url: str  # Frontend URL where user is redirected after payment
    payment_webhook_url: str  # Backend URL for payment gateway webhooks

class Performance_Env_Type(TypedDict):
    redis_url: str
    cache_enabled: bool
    enable_query_logging: bool
    db_pool_size: int
    db_max_overflow: int

class Cron_Scheduler_Env_Type(TypedDict):
    enable_cron_scheduler: bool

class env_type(TypedDict):
    jwt:JWT_Env_Type
    env_type:str
    enable_perf_logs:bool
 
    database_url:str
    mail:Mail_Env_Type
    social:Social_Env_Type
    cloudinary:Cloudinary_Env_Type
    payment:Payment_Env_Type
    performance:Performance_Env_Type
    cron_scheduler:Cron_Scheduler_Env_Type
  


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", validate_default=False)
    jwt_secret: str=""
    enable_perf_logs:bool=False
    jwt_access_expiry_time:str=""
    jwt_refresh_expiry_time: str=""
    jwt_expiry_time:str=""
    database_url:str=""
    mail_server:str=''
    mail_port:int =0
    mail_username:str=''
    mail_password:str=''
    use_credentials:bool=False
    mail_use_ssl:bool=False
    mail_use_tls:bool=False
    mail_sender:str=''
    mail_sender_name:str=""
    env_type: str=''
    use_mail_service:bool=False

    google_client_id:str=""
    google_client_secret:str=""
    google_redirect_uri:str=""
    facebook_client_id:str=""
    facebook_client_secret:str=""
    facebook_redirect_uri:str=""
    github_client_id:str=""
    github_client_secret:str=""
    github_redirect_uri:str=""
    
    # Cloudinary settings
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""
    
    # Payment Gateway settings
    paystack_secret_key: str = ""
    paystack_public_key: str = ""
    flutterwave_secret_key: str = ""
    flutterwave_public_key: str = ""
    stripe_secret_key: str = ""
    stripe_public_key: str = ""
    payment_callback_url: str = ""  # Frontend callback URL
    payment_webhook_url: str = ""  # Backend webhook URL
    
    # Performance settings
    redis_url: str = "redis://localhost:6379"
    cache_enabled: bool = True
    enable_query_logging: bool = False
    db_pool_size: int = 20
    db_max_overflow: int = 40

    # Cron scheduler settings
    enable_cron_scheduler: bool = False
    
    





# @lru_cache
settings:Settings = Settings()

env:env_type = {"database_url":settings.database_url, "env_type":settings.env_type,
                "enable_perf_logs":settings.enable_perf_logs,
                "jwt":{
                "jwt_expiry_time":settings.jwt_expiry_time, 
                "jwt_secret":settings.jwt_secret,  
                "jwt_access_expiry_time": int(settings.jwt_access_expiry_time or 3600),
                "jwt_refresh_expiry_time": int(settings.jwt_refresh_expiry_time or 86400)},
                "mail":{
                    "mail_password":settings.mail_password,
                    "mail_port":settings.mail_port,
                    "mail_server":settings.mail_server,
                    "mail_sender":settings.mail_sender,
                    "mail_use_tls":settings.mail_use_tls,
                    "mail_use_ssl":settings.mail_use_ssl,
                    "mail_username":settings.mail_username,
                    "use_credentials":settings.use_credentials,
                    "mail_sender_name":settings.mail_sender_name,
                    
                    "use_mail_service": settings.use_mail_service
                    
                },
                "social": {
                    "google_client_id":settings.google_client_id,
                    "google_client_secret":settings.google_client_secret,
                    "google_redirect_uri":settings.google_redirect_uri,
                    "facebook_client_id":settings.facebook_client_id,
                    "facebook_client_secret":settings.facebook_client_secret,
                    "facebook_redirect_uri":settings.facebook_redirect_uri,
                    "github_client_id":settings.github_client_id,
                    "github_client_secret":settings.github_client_secret,
                    "github_redirect_uri":settings.github_redirect_uri
                },
                "cloudinary":{
                    "cloudinary_cloud_name":settings.cloudinary_cloud_name,
                    "cloudinary_api_key":settings.cloudinary_api_key,
                    "cloudinary_api_secret":settings.cloudinary_api_secret
                },
                "payment":{
                    "paystack_secret_key":settings.paystack_secret_key,
                    "paystack_public_key":settings.paystack_public_key,
                    "flutterwave_secret_key":settings.flutterwave_secret_key,
                    "flutterwave_public_key":settings.flutterwave_public_key,
                    "stripe_secret_key":settings.stripe_secret_key,
                    "stripe_public_key":settings.stripe_public_key,
                    "payment_callback_url":settings.payment_callback_url,
                    "payment_webhook_url":settings.payment_webhook_url
                },
                "performance":{
                    "redis_url":settings.redis_url,
                    "cache_enabled":settings.cache_enabled,
                    "enable_query_logging":settings.enable_query_logging,
                    "db_pool_size":settings.db_pool_size,
                    "db_max_overflow":settings.db_max_overflow
                },
                "cron_scheduler":{
                    "enable_cron_scheduler":settings.enable_cron_scheduler
                }
                 }
