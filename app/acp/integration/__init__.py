"""
ACP Integration Module

Provides integration adapters for various frameworks and services.
"""

from app.acp.integration.telegram import TelegramAdapter
from app.acp.integration.fastapi import create_acp_router, ACPFastAPIAdapter

__all__ = [
    "TelegramAdapter",
    "create_acp_router",
    "ACPFastAPIAdapter",
]
