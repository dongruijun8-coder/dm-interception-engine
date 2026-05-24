"""Abstract base class for all APP plugins."""
from abc import ABC, abstractmethod
from engine.models import AuthResult, Room, User, Message, SendResult, HealthStatus


class BasePlugin(ABC):
    """Each APP plugin must implement these 5 methods."""

    @abstractmethod
    async def authenticate(self, credential: dict) -> AuthResult:
        """Login / refresh token. Engine stores returned session and passes it to subsequent calls."""
        ...

    @abstractmethod
    async def fetch_rooms(self, session: dict, filters: dict) -> list[Room]:
        """Fetch all rooms for this APP. Plugin handles pagination internally.
        Each Room must have type set to 'voice' or 'video'."""
        ...

    @abstractmethod
    async def fetch_users(self, session: dict, room: Room) -> list[User]:
        """Fetch ranked users from a single room. Plugin normalizes fields to the unified User model."""
        ...

    @abstractmethod
    async def send_message(self, session: dict, user: User, message: Message) -> SendResult:
        """Send one DM to one user. Plugin handles rate limiting internally.
        On failure, return SendResult(success=False, error_code=...) so engine can skip+continue."""
        ...

    @abstractmethod
    async def check_health(self, session: dict) -> HealthStatus:
        """Check if account is still valid (not banned, token not expired)."""
        ...

    app_name: str
    """Unique APP identifier, e.g. 'popo'. Subclasses must set this as a class attribute."""
