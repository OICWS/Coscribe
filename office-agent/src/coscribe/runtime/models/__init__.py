"""What a model can do: the bundled model catalog (decision 0055), and which providers search
the web."""

from .catalog import ModelInfo, catalog_provider, model_info
from .web_search import WebSearchInfo, provider_web_search

__all__ = [
    "ModelInfo",
    "WebSearchInfo",
    "catalog_provider",
    "model_info",
    "provider_web_search",
]
