"""
Fixture-specific conftest for ACP fixtures.

This file ensures environment variables are set before the acp_fixtures module is imported.
"""

# IMPORTANT: Environment setup must happen before any app imports
import os

# Bot token must be in valid format: {bot_id}:{alphanumeric_token}
# The token format is validated by aiogram, so we use a valid-looking format
os.environ.setdefault("BOT_TOKEN", "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ADMIN_IDS", "[123456789]")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")
os.environ.setdefault("ACP_SERVER_URL", "http://localhost:8000")
