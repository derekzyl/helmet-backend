from dataclasses import dataclass
from hashlib import blake2b
from hmac import compare_digest
import secrets


@dataclass()
class EncryptAndCompareData:
    SECRET_KEY = secrets.token_bytes(64)
    AUTH_SIZE = 64

    def sign(self, data: str):

        encode_data = data.encode("utf-8")
        h = blake2b(digest_size=self.AUTH_SIZE, key=self.SECRET_KEY)

        h.update(encode_data)
        return h.hexdigest()

    def verify(self, raw_data: str, encoded_data: str) -> bool:
        good_sig = self.sign(raw_data)

        return compare_digest(good_sig, encoded_data)
