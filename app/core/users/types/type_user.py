from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import NotRequired, Optional, TypedDict


@dataclass
class UserD:
    id: str
    first_name: str
    last_name: str
    username: str
    email: str
    password: str
    language: str
    deleted_at: datetime
    created_at: datetime
    updated_at: datetime
    allow_login: bool
    gender: str


class UserTypeEnum(Enum):
    USER = "user"
    ADMIN = "admin"

    def __str__(self):
        return self.value


class RefreshTokenData(TypedDict):
    refreshToken: str


class UserData(TypedDict):
    id: str
    first_name: str
    last_name: str
    username: str
    email: str
    password: str
    deleted_at: datetime
    created_at: datetime
    updated_at: datetime
    user_type: UserTypeEnum
    allow_login: bool
    gender: str


class CreateUserData(TypedDict):
    first_name: str
    last_name: str
    email: str
    password: str
    user_type: NotRequired[UserTypeEnum | str]
    middle_name: NotRequired[str]
    name: NotRequired[str]
    address: NotRequired[str]
    privacy_policy_accepted: NotRequired[bool]
    privacy_policy_accepted_at: NotRequired[str]
    phone: NotRequired[str]
    gender: NotRequired[str]
    allow_login: NotRequired[bool]
    username: NotRequired[str]


class LoginUserData(TypedDict):
    email: str
    password: str


class ForgotPasswordData(TypedDict):
    email: str


class UpdateUserData(TypedDict):
    first_name: str
    last_name: str
    username: NotRequired[str]
    remember_token: NotRequired[str]
    gender: NotRequired[str]


class GenderE(Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


@dataclass
class CreateUserD:
    first_name: str
    last_name: str
    email: str
    password: str
    user_type = UserTypeEnum
    address: Optional[str]
