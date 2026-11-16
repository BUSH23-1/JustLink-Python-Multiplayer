"""Base interface for all social platform publishing integrations."""

from abc import ABC, abstractmethod
import datetime
from typing import Tuple
from app.schemas import PlatformResult


class BasePlatform(ABC):
    """Abstract base class that all platform integrations must implement."""

    name: str

    @abstractmethod
    async def publish(self, message: str) -> PlatformResult:
        """Publish the given message to the platform.

        Args:
            message: The validated text message to post.

        Returns:
            PlatformResult: Details of the post attempt (status, URL, timestamps, errors).
        """
        pass

    @staticmethod
    def get_current_utc_timestamp() -> Tuple[str, str]:
        """Returns current UTC date (YYYY-MM-DD) and time (HH:MM:SS)."""
        now = datetime.datetime.now(datetime.timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

