import jwt

from src.adapters.security.token_service import AbstractTokenService, TokenPayload


class JWTTokenService(AbstractTokenService):
    def decode_token(self, token: str) -> TokenPayload | None:
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=["HS256"])
            return {
                "sub": payload["sub"],
                "iat": payload["iat"],
                "exp": payload["exp"],
            }
        except jwt.PyJWTError:
            return None
