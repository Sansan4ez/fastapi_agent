"""
Unit tests for ACP Agent Registry.

Tests cover:
- AgentRegistry: Agent registration and management
- AgentHandler: Agent handler wrapper
- agent_decorator: Decorator for registering agents
"""

from __future__ import annotations

from typing import AsyncGenerator

import pytest


# =============================================================================
# Helper Functions for Lazy Imports
# =============================================================================


def _get_types():
    """Lazy import of ACP types module."""
    from app.acp.core.types import AgentStatus

    return {
        "AgentStatus": AgentStatus,
    }


def _get_models():
    """Lazy import of ACP models module."""
    from app.acp.core.models import (
        Message,
        AgentManifest,
        AgentMetadata,
    )

    return {
        "Message": Message,
        "AgentManifest": AgentManifest,
        "AgentMetadata": AgentMetadata,
    }


def _get_agent_registry():
    """Lazy import of agent registry module."""
    from app.acp.server.agent import (
        AgentRegistry,
        AgentHandler,
        agent_decorator,
        create_agent_decorator,
    )

    return {
        "AgentRegistry": AgentRegistry,
        "AgentHandler": AgentHandler,
        "agent_decorator": agent_decorator,
        "create_agent_decorator": create_agent_decorator,
    }


def _create_mock_agent_func():
    """Create a mock agent function for testing."""
    from app.acp.core.models import Message
    from app.acp.server.context import Context

    async def mock_agent(
        input: list[Message], context: Context
    ) -> AsyncGenerator:
        yield Message.agent_text("Hello from mock agent!")

    return mock_agent


def _create_test_handler(name: str = "test-agent", description: str = "Test agent"):
    """Create a test AgentHandler."""
    models = _get_models()
    agent_registry = _get_agent_registry()

    manifest = models["AgentManifest"](
        name=name,
        description=description,
    )

    handler = agent_registry["AgentHandler"](
        func=_create_mock_agent_func(),
        manifest=manifest,
    )

    return handler


# =============================================================================
# AgentRegistry Tests
# =============================================================================


class TestAgentRegistry:
    """Tests for AgentRegistry - agent registration and management."""

    def test_registry_creation_empty(self):
        """Verify AgentRegistry can be created empty."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        assert registry.count == 0

    def test_register_single_agent(self):
        """Verify single agent can be registered."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="agent-1")

        registry.register(handler)

        assert registry.count == 1
        assert registry.has_agent("agent-1")

    def test_register_multiple_agents(self):
        """Verify multiple agents can be registered."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler1 = _create_test_handler(name="agent-1")
        handler2 = _create_test_handler(name="agent-2")
        handler3 = _create_test_handler(name="agent-3")

        registry.register(handler1)
        registry.register(handler2)
        registry.register(handler3)

        assert registry.count == 3
        assert registry.has_agent("agent-1")
        assert registry.has_agent("agent-2")
        assert registry.has_agent("agent-3")

    def test_register_duplicate_agent_raises_error(self):
        """Verify registering duplicate agent name raises ValueError."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler1 = _create_test_handler(name="duplicate-agent")
        handler2 = _create_test_handler(name="duplicate-agent")

        registry.register(handler1)

        with pytest.raises(ValueError) as exc_info:
            registry.register(handler2)

        assert "duplicate-agent" in str(exc_info.value)
        assert "already registered" in str(exc_info.value)

    def test_unregister_existing_agent(self):
        """Verify existing agent can be unregistered."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="agent-to-remove")

        registry.register(handler)
        assert registry.count == 1

        result = registry.unregister("agent-to-remove")

        assert result is True
        assert registry.count == 0
        assert not registry.has_agent("agent-to-remove")

    def test_unregister_nonexistent_agent(self):
        """Verify unregistering nonexistent agent returns False."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        result = registry.unregister("nonexistent-agent")

        assert result is False

    def test_unregister_with_remaining_agents(self):
        """Verify unregistering one agent leaves others intact."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler1 = _create_test_handler(name="agent-1")
        handler2 = _create_test_handler(name="agent-2")
        handler3 = _create_test_handler(name="agent-3")

        registry.register(handler1)
        registry.register(handler2)
        registry.register(handler3)

        registry.unregister("agent-2")

        assert registry.count == 2
        assert registry.has_agent("agent-1")
        assert not registry.has_agent("agent-2")
        assert registry.has_agent("agent-3")

    def test_get_existing_agent(self):
        """Verify get returns existing agent handler."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="my-agent", description="My test agent")

        registry.register(handler)

        retrieved = registry.get("my-agent")

        assert retrieved is not None
        assert retrieved.name == "my-agent"
        assert retrieved.manifest.description == "My test agent"

    def test_get_nonexistent_agent(self):
        """Verify get returns None for nonexistent agent."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        retrieved = registry.get("nonexistent-agent")

        assert retrieved is None

    def test_get_after_unregister(self):
        """Verify get returns None after agent is unregistered."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="temporary-agent")

        registry.register(handler)
        assert registry.get("temporary-agent") is not None

        registry.unregister("temporary-agent")

        assert registry.get("temporary-agent") is None

    def test_get_manifest_existing_agent(self):
        """Verify get_manifest returns manifest for existing agent."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="manifest-agent", description="Agent with manifest")

        registry.register(handler)

        manifest = registry.get_manifest("manifest-agent")

        assert manifest is not None
        assert manifest.name == "manifest-agent"
        assert manifest.description == "Agent with manifest"

    def test_get_manifest_nonexistent_agent(self):
        """Verify get_manifest returns None for nonexistent agent."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        manifest = registry.get_manifest("nonexistent-agent")

        assert manifest is None

    def test_list_agents_empty_registry(self):
        """Verify list_agents returns empty list for empty registry."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        manifests, total = registry.list_agents()

        assert manifests == []
        assert total == 0

    def test_list_agents_with_agents(self):
        """Verify list_agents returns all registered agents."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler1 = _create_test_handler(name="agent-1")
        handler2 = _create_test_handler(name="agent-2")

        registry.register(handler1)
        registry.register(handler2)

        manifests, total = registry.list_agents()

        assert total == 2
        assert len(manifests) == 2
        names = [m.name for m in manifests]
        assert "agent-1" in names
        assert "agent-2" in names

    def test_list_agents_pagination_offset(self):
        """Verify list_agents respects offset parameter."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        for i in range(5):
            handler = _create_test_handler(name=f"agent-{i}")
            registry.register(handler)

        manifests, total = registry.list_agents(offset=2)

        assert total == 5
        assert len(manifests) == 3  # 5 - 2 offset

    def test_list_agents_pagination_limit(self):
        """Verify list_agents respects limit parameter."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        for i in range(5):
            handler = _create_test_handler(name=f"agent-{i}")
            registry.register(handler)

        manifests, total = registry.list_agents(limit=2)

        assert total == 5
        assert len(manifests) == 2

    def test_list_agents_pagination_offset_and_limit(self):
        """Verify list_agents respects both offset and limit parameters."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        for i in range(10):
            handler = _create_test_handler(name=f"agent-{i}")
            registry.register(handler)

        manifests, total = registry.list_agents(offset=3, limit=4)

        assert total == 10
        assert len(manifests) == 4

    def test_list_agents_offset_beyond_count(self):
        """Verify list_agents handles offset beyond total count."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        for i in range(3):
            handler = _create_test_handler(name=f"agent-{i}")
            registry.register(handler)

        manifests, total = registry.list_agents(offset=10)

        assert total == 3
        assert len(manifests) == 0

    def test_list_agents_filter_by_status(self):
        """Verify list_agents can filter by agent status."""
        agent_registry = _get_agent_registry()
        models = _get_models()
        types = _get_types()

        registry = agent_registry["AgentRegistry"]()

        # Create handlers with different statuses
        active_manifest = models["AgentManifest"](
            name="active-agent",
            description="Active agent",
            status=types["AgentStatus"].ACTIVE,
        )
        active_handler = agent_registry["AgentHandler"](
            func=_create_mock_agent_func(),
            manifest=active_manifest,
        )

        degraded_manifest = models["AgentManifest"](
            name="degraded-agent",
            description="Degraded agent",
            status=types["AgentStatus"].DEGRADED,
        )
        degraded_handler = agent_registry["AgentHandler"](
            func=_create_mock_agent_func(),
            manifest=degraded_manifest,
        )

        registry.register(active_handler)
        registry.register(degraded_handler)

        # Filter by ACTIVE status
        manifests, total = registry.list_agents(status=types["AgentStatus"].ACTIVE)

        assert total == 1
        assert len(manifests) == 1
        assert manifests[0].name == "active-agent"

    def test_list_agents_filter_by_status_no_match(self):
        """Verify list_agents returns empty when no agents match status filter."""
        agent_registry = _get_agent_registry()
        types = _get_types()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="active-agent")

        registry.register(handler)

        # Filter by RETIRED status (no agents have this)
        manifests, total = registry.list_agents(status=types["AgentStatus"].RETIRED)

        assert total == 0
        assert len(manifests) == 0

    def test_has_agent_true(self):
        """Verify has_agent returns True for registered agent."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        handler = _create_test_handler(name="existing-agent")

        registry.register(handler)

        assert registry.has_agent("existing-agent") is True

    def test_has_agent_false(self):
        """Verify has_agent returns False for non-registered agent."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        assert registry.has_agent("nonexistent-agent") is False

    def test_count_increments(self):
        """Verify count increments with each registration."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        assert registry.count == 0

        registry.register(_create_test_handler(name="agent-1"))
        assert registry.count == 1

        registry.register(_create_test_handler(name="agent-2"))
        assert registry.count == 2

        registry.register(_create_test_handler(name="agent-3"))
        assert registry.count == 3

    def test_count_decrements(self):
        """Verify count decrements with each unregistration."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()
        registry.register(_create_test_handler(name="agent-1"))
        registry.register(_create_test_handler(name="agent-2"))
        registry.register(_create_test_handler(name="agent-3"))

        assert registry.count == 3

        registry.unregister("agent-2")
        assert registry.count == 2

        registry.unregister("agent-1")
        assert registry.count == 1

        registry.unregister("agent-3")
        assert registry.count == 0


# =============================================================================
# AgentHandler Tests
# =============================================================================


class TestAgentHandler:
    """Tests for AgentHandler - agent function wrapper."""

    def test_handler_creation(self):
        """Verify AgentHandler can be created with func and manifest."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        manifest = models["AgentManifest"](
            name="test-handler",
            description="Test handler description",
        )

        handler = agent_registry["AgentHandler"](
            func=_create_mock_agent_func(),
            manifest=manifest,
        )

        assert handler.name == "test-handler"
        assert handler.manifest.description == "Test handler description"

    def test_handler_name_property(self):
        """Verify AgentHandler name property returns manifest name."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        manifest = models["AgentManifest"](
            name="property-test-agent",
            description="Testing name property",
        )

        handler = agent_registry["AgentHandler"](
            func=_create_mock_agent_func(),
            manifest=manifest,
        )

        assert handler.name == "property-test-agent"
        assert handler.name == handler.manifest.name

    @pytest.mark.asyncio
    async def test_handler_callable(self):
        """Verify AgentHandler can be called as async generator."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        # Import Context and Run for the test
        from app.acp.server.context import Context
        from app.acp.core.models import Run

        manifest = models["AgentManifest"](
            name="callable-agent",
            description="Callable test agent",
        )

        async def test_agent(input, context):
            yield models["Message"].agent_text("Test response")

        handler = agent_registry["AgentHandler"](
            func=test_agent,
            manifest=manifest,
        )

        # Create minimal context with a Run object
        run = Run(agent_name="callable-agent")
        context = Context(run=run)

        # Invoke the handler
        results = []
        async for item in handler([], context):
            results.append(item)

        assert len(results) == 1
        assert results[0].parts[0].content == "Test response"


# =============================================================================
# Agent Decorator Tests
# =============================================================================


class TestAgentDecorator:
    """Tests for agent_decorator - decorator for registering agents."""

    def test_agent_decorator_basic(self):
        """Verify agent_decorator registers agent with basic parameters."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()

        @agent_registry["agent_decorator"](
            registry,
            name="decorated-agent",
            description="A decorated agent",
        )
        async def my_agent(input, context):
            yield models["Message"].agent_text("Hello!")

        assert registry.has_agent("decorated-agent")
        assert registry.get_manifest("decorated-agent").description == "A decorated agent"

    def test_agent_decorator_uses_function_name(self):
        """Verify agent_decorator uses function name when name not provided."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()

        @agent_registry["agent_decorator"](
            registry,
            description="Agent using function name",
        )
        async def auto_named_agent(input, context):
            yield models["Message"].agent_text("Hello!")

        assert registry.has_agent("auto_named_agent")

    def test_agent_decorator_uses_docstring(self):
        """Verify agent_decorator uses docstring when description not provided."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()

        @agent_registry["agent_decorator"](
            registry,
            name="docstring-agent",
        )
        async def docstring_agent(input, context):
            """This description comes from the docstring."""
            yield models["Message"].agent_text("Hello!")

        manifest = registry.get_manifest("docstring-agent")
        assert manifest.description == "This description comes from the docstring."

    def test_agent_decorator_with_content_types(self):
        """Verify agent_decorator sets custom content types."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()

        @agent_registry["agent_decorator"](
            registry,
            name="multimodal-agent",
            description="Multimodal agent",
            input_content_types=["text/plain", "image/png"],
            output_content_types=["text/plain", "application/json"],
        )
        async def multimodal_agent(input, context):
            yield models["Message"].agent_text("Hello!")

        manifest = registry.get_manifest("multimodal-agent")
        assert "text/plain" in manifest.input_content_types
        assert "image/png" in manifest.input_content_types
        assert "application/json" in manifest.output_content_types

    def test_agent_decorator_with_metadata_dict(self):
        """Verify agent_decorator accepts metadata as dict."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()

        @agent_registry["agent_decorator"](
            registry,
            name="metadata-agent",
            description="Agent with metadata",
            metadata={"version": "1.0.0", "tags": ["test", "example"]},
        )
        async def metadata_agent(input, context):
            yield models["Message"].agent_text("Hello!")

        manifest = registry.get_manifest("metadata-agent")
        assert manifest.metadata.version == "1.0.0"
        assert "test" in manifest.metadata.tags

    def test_agent_decorator_with_metadata_object(self):
        """Verify agent_decorator accepts metadata as AgentMetadata object."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()

        metadata = models["AgentMetadata"](
            version="2.0.0",
            license="MIT",
            capabilities=["text-generation"],
        )

        @agent_registry["agent_decorator"](
            registry,
            name="metadata-obj-agent",
            description="Agent with metadata object",
            metadata=metadata,
        )
        async def metadata_obj_agent(input, context):
            yield models["Message"].agent_text("Hello!")

        manifest = registry.get_manifest("metadata-obj-agent")
        assert manifest.metadata.version == "2.0.0"
        assert manifest.metadata.license == "MIT"


# =============================================================================
# Create Agent Decorator Tests
# =============================================================================


class TestCreateAgentDecorator:
    """Tests for create_agent_decorator - factory for bound decorators."""

    def test_create_agent_decorator(self):
        """Verify create_agent_decorator creates bound decorator."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()
        agent = agent_registry["create_agent_decorator"](registry)

        @agent(name="bound-agent", description="Bound agent")
        async def bound_agent(input, context):
            yield models["Message"].agent_text("Hello!")

        assert registry.has_agent("bound-agent")

    def test_create_agent_decorator_multiple_agents(self):
        """Verify bound decorator can register multiple agents."""
        agent_registry = _get_agent_registry()
        models = _get_models()

        registry = agent_registry["AgentRegistry"]()
        agent = agent_registry["create_agent_decorator"](registry)

        @agent(name="agent-1", description="First agent")
        async def agent_one(input, context):
            yield models["Message"].agent_text("One!")

        @agent(name="agent-2", description="Second agent")
        async def agent_two(input, context):
            yield models["Message"].agent_text("Two!")

        @agent(name="agent-3", description="Third agent")
        async def agent_three(input, context):
            yield models["Message"].agent_text("Three!")

        assert registry.count == 3
        assert registry.has_agent("agent-1")
        assert registry.has_agent("agent-2")
        assert registry.has_agent("agent-3")


# =============================================================================
# Integration Tests
# =============================================================================


class TestAgentRegistryIntegration:
    """Integration tests for AgentRegistry with other components."""

    def test_register_unregister_cycle(self):
        """Test full register/unregister cycle."""
        agent_registry = _get_agent_registry()

        registry = agent_registry["AgentRegistry"]()

        # Register
        handler = _create_test_handler(name="cycle-agent")
        registry.register(handler)
        assert registry.has_agent("cycle-agent")
        assert registry.count == 1

        # Get and verify
        retrieved = registry.get("cycle-agent")
        assert retrieved is not None
        assert retrieved.name == "cycle-agent"

        # List and verify
        manifests, total = registry.list_agents()
        assert total == 1
        assert manifests[0].name == "cycle-agent"

        # Unregister
        result = registry.unregister("cycle-agent")
        assert result is True
        assert not registry.has_agent("cycle-agent")
        assert registry.count == 0
        assert registry.get("cycle-agent") is None

    def test_multiple_registries_independent(self):
        """Verify multiple registries are independent."""
        agent_registry = _get_agent_registry()

        registry1 = agent_registry["AgentRegistry"]()
        registry2 = agent_registry["AgentRegistry"]()

        handler1 = _create_test_handler(name="agent-in-reg1")
        handler2 = _create_test_handler(name="agent-in-reg2")

        registry1.register(handler1)
        registry2.register(handler2)

        assert registry1.has_agent("agent-in-reg1")
        assert not registry1.has_agent("agent-in-reg2")

        assert registry2.has_agent("agent-in-reg2")
        assert not registry2.has_agent("agent-in-reg1")

        assert registry1.count == 1
        assert registry2.count == 1

    def test_list_and_filter_workflow(self):
        """Test workflow of listing and filtering agents."""
        agent_registry = _get_agent_registry()
        models = _get_models()
        types = _get_types()

        registry = agent_registry["AgentRegistry"]()

        # Create agents with different statuses (using unique names)
        statuses_with_names = [
            (types["AgentStatus"].ACTIVE, "agent-active-1"),
            (types["AgentStatus"].ACTIVE, "agent-active-2"),
            (types["AgentStatus"].DEGRADED, "agent-degraded"),
            (types["AgentStatus"].RETIRING, "agent-retiring"),
        ]

        for status, name in statuses_with_names:
            manifest = models["AgentManifest"](
                name=name,
                description=f"Agent with status {status.value}",
                status=status,
            )
            handler = agent_registry["AgentHandler"](
                func=_create_mock_agent_func(),
                manifest=manifest,
            )
            registry.register(handler)

        # List all
        all_manifests, all_total = registry.list_agents()
        assert all_total == 4

        # Filter active only
        active_manifests, active_total = registry.list_agents(
            status=types["AgentStatus"].ACTIVE
        )
        assert active_total == 2

        # Filter degraded only
        degraded_manifests, degraded_total = registry.list_agents(
            status=types["AgentStatus"].DEGRADED
        )
        assert degraded_total == 1
