from dataclasses import dataclass

from passlib.context import CryptContext


@dataclass
class PassHash:
    hr: CryptContext = CryptContext(schemes="bcrypt")

    def hash_me(self, password: str) -> str:
        return self.hr.hash(password)

    def verify_me(self, password: str, hashed_password: str) -> bool:
        return self.hr.verify(secret=password, hash=hashed_password)
