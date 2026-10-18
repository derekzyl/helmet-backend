from dataclasses import dataclass
from typing import TypedDict

from app.config.config import TokenType


@dataclass
class TokenData:
    type:TokenType
    user_id:str
    expires:str
    blacklisted:bool 
    created_at:str
    updated_at:str


class SaveTokenData(TypedDict):
    token: str 
    expires: int|str
    type: str
    user_id: str
    blacklisted: bool