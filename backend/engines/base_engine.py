from abc import ABC, abstractmethod
import logging

class BaseEngine(ABC):
    """
    Abstract Base Class for all XEDY engines.
    Enforces the 'Interface-first design' constraint from the Project Manifest.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"xedy.engine.{self.engine_name}")
        self.logger.info(f"{self.engine_name} initialized.")

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Return the unique name of the engine."""
        pass

    @abstractmethod
    async def start(self):
        """Start the engine's background tasks or connections."""
        pass

    @abstractmethod
    async def stop(self):
        """Gracefully shutdown the engine."""
        pass
