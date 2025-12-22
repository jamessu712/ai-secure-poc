# __init__.py

# Optional: expose common variables or functions for direct external import
from .config import COGNITIVE_SERVICES_ENDPOINT, COGNITIVE_SERVICES_KEY

# Define package public interface (optional)
__all__ = [
    "COGNITIVE_SERVICES_ENDPOINT",
    "COGNITIVE_SERVICES_KEY"
]
