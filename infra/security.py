from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from consts import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY


class SecurityServices:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Check whether the given password matches the stored hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode()[:72],
                hashed_password.encode(),
            )
        except ValueError:
            return False

    @staticmethod
    def encrypt_password(password: str) -> str:
        """Hash the password using bcrypt."""
        encrypted_password = bcrypt.hashpw(
            password.encode()[:72], bcrypt.gensalt()
        ).decode()
        return encrypted_password

    @staticmethod
    def create_access_token(subject: str) -> str:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": subject, "exp": expire}
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_access_token(token: str) -> str | None:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            return None
        return payload.get("sub")
