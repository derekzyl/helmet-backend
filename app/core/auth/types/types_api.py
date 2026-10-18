

from dataclasses import dataclass


@dataclass
class ApiKey:
    
    key: str
    secret: str
    user_id:str
    
    