import datetime
import json

from src.adapters.security import AbstractTokenService, TokenPayload
from src.domain.user import UserID


class FakeTokenService(AbstractTokenService):
    def decode_token(self, token: str) -> TokenPayload | None:
        return json.loads(token)

    @classmethod
    def create_fake_token(cls, user_id: UserID) -> str:
        return json.dumps(
            {
                "sub": str(user_id),
                "iat": datetime.datetime.now().isoformat(),
                "exp": (
                    datetime.datetime.now() + datetime.timedelta(hours=1)
                ).isoformat(),
            }
        )
