
from enum import Enum


class TokenType(Enum):
    VERIFY_EMAIL ="VERIFY_EMAIL"
    RESET_PASSWORD="RESET_PASSWORD"
    REFRESH_TOKEN="REFRESH_TOKEN"
    ACCESS_TOKEN="ACCESS_TOKEN"

    # convert enum to string
    def __str__(self)->str:
        return self.value
    
    
    
    