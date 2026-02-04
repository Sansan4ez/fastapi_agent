"""
ACP Test Fixtures Package

This package provides reusable test fixtures for ACP types, models, schemas,
Telegram integration testing, and mock ACP server responses.

Usage:
    To use ACP fixtures in your tests, add the following to your test file
    or in a conftest.py file in your test directory:

        pytest_plugins = ["tests.fixtures.acp_fixtures"]

    To use Telegram fixtures:

        pytest_plugins = ["tests.fixtures.telegram_fixtures"]

    To use mock ACP server fixtures (using respx):

        pytest_plugins = ["tests.fixtures.acp_server_fixtures"]

    Or use all fixtures:

        pytest_plugins = [
            "tests.fixtures.acp_fixtures",
            "tests.fixtures.telegram_fixtures",
            "tests.fixtures.acp_server_fixtures",
        ]

    Then you can use fixtures like:

        def test_message_creation(sample_user_message):
            assert sample_user_message.role == "user"

        def test_telegram_handler(mock_telegram_message):
            assert mock_telegram_message.text is not None

        @pytest.mark.anyio
        async def test_acp_client(mock_acp_server):
            config, mock = mock_acp_server
            async with ACPClient(base_url=config.base_url) as client:
                agents = await client.list_agents()
                assert len(agents.agents) > 0

    Or import factory functions directly:

        from tests.fixtures.acp_fixtures import create_message, create_run
        from tests.fixtures.telegram_fixtures import (
            create_telegram_message,
            create_telegram_update,
        )
        from tests.fixtures.acp_server_fixtures import (
            create_run_response,
            create_agent_list_response,
            MockACPServerConfig,
            CustomMockACPServer,
        )
"""
