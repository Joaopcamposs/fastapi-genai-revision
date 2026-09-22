from infra.security import SecurityServices


def test_encrypt_and_verify_password() -> None:
    hashed = SecurityServices.encrypt_password("secret123")
    assert hashed != "secret123"
    assert SecurityServices.verify_password("secret123", hashed)


def test_verify_password_rejects_wrong_password() -> None:
    hashed = SecurityServices.encrypt_password("secret123")
    assert not SecurityServices.verify_password("wrong-password", hashed)


def test_verify_password_rejects_malformed_hash() -> None:
    assert not SecurityServices.verify_password("secret123", "not-a-bcrypt-hash")


def test_create_and_decode_access_token() -> None:
    token = SecurityServices.create_access_token(subject="user@example.com")
    assert SecurityServices.decode_access_token(token) == "user@example.com"


def test_decode_access_token_rejects_invalid_token() -> None:
    assert SecurityServices.decode_access_token("not-a-jwt") is None
