from typing import NotRequired, TypedDict


class ChangePassWordData(TypedDict):
    new_password: str
    confirm_password: str
    current_password: NotRequired[str]
    old_password: NotRequired[str]


class VerifyResetTokenData(TypedDict):
    email: str
    token: str


class LoginData(TypedDict):
    email: str
    password: str


class VerifyEmailData(TypedDict):
    email: str


class ForgotPasswordData(TypedDict):
    email: str


class ResetPasswordData(TypedDict):
    email: str
    token: str
    password: str


class VerifyEmailDataTokenData(TypedDict):
    email: str
    token: str


class ResetPassWordData(TypedDict):
    token: str
    password: str
    email: str
