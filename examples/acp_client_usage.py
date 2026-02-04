"""
Example ACP Client Usage

This module demonstrates comprehensive usage patterns for the ACP (Agent Communication Protocol)
client library. It covers all major features including:

- Agent discovery and listing
- Synchronous, asynchronous, and streaming runs
- Session management for multi-turn conversations
- Batch operations for parallel agent execution
- Run lifecycle management with callbacks
- Error handling patterns

Based on the ACP protocol specification research.

Usage:
    python -m examples.acp_client_usage

    Or run specific examples:
        python -m examples.acp_client_usage basic
        python -m examples.acp_client_usage streaming
        python -m examples.acp_client_usage sessions
        python -m examples.acp_client_usage batch
        python -m examples.acp_client_usage callbacks
"""

import asyncio
import sys
from typing import Any
from uuid import UUID

from loguru import logger

from app.acp.client import ACPClient, SessionManager, RunManager, AgentDiscovery
from app.acp.client.run import BatchRunManager
from app.acp.core.models import Message, MessagePart
from app.acp.core.types import RunStatus, AgentStatus
from app.acp.core.schemas import RunResponse
from app.config import settings


# ==============================================================================
# Configuration
# ==============================================================================

# Default ACP server URL (can be overridden via settings)
ACP_SERVER_URL = getattr(settings, "ACP_SERVER_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = getattr(settings, "ACP_REQUEST_TIMEOUT", 60)


# ==============================================================================
# Example 1: Basic Agent Discovery and Listing
# ==============================================================================

async def example_agent_discovery():
    """
    Demonstrates how to discover and list available agents on an ACP server.

    This is typically the first step when working with an ACP server.
    """
    print("\n" + "=" * 60)
    print("Example 1: Agent Discovery")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        # List all available agents
        agents_response = await client.list_agents()

        print(f"\nDiscovered {len(agents_response.agents)} agents:")
        for agent in agents_response.agents:
            print(f"\n  - {agent.name}")
            print(f"    Description: {agent.description}")
            print(f"    Status: {agent.status}")
            print(f"    Input types: {', '.join(agent.input_content_types)}")
            print(f"    Output types: {', '.join(agent.output_content_types)}")

            # Show capabilities if available
            if agent.metadata.capabilities:
                print(f"    Capabilities: {', '.join(agent.metadata.capabilities)}")

            # Show domains if available
            if agent.metadata.domains:
                print(f"    Domains: {', '.join(agent.metadata.domains)}")

        # Get detailed info for a specific agent (if any exist)
        if agents_response.agents:
            agent_name = agents_response.agents[0].name
            print(f"\n\nDetailed info for '{agent_name}':")

            agent_manifest = await client.get_agent(agent_name)
            print(f"  Name: {agent_manifest.name}")
            print(f"  Description: {agent_manifest.description}")
            print(f"  Version: {agent_manifest.metadata.version or 'N/A'}")
            print(f"  License: {agent_manifest.metadata.license or 'N/A'}")
            print(f"  Documentation: {agent_manifest.metadata.documentation or 'N/A'}")


# ==============================================================================
# Example 2: Synchronous Agent Execution
# ==============================================================================

async def example_sync_execution():
    """
    Demonstrates synchronous agent execution.

    In sync mode, the request blocks until the agent completes.
    This is the simplest way to interact with agents.
    """
    print("\n" + "=" * 60)
    print("Example 2: Synchronous Execution")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        # Check if we have any agents available
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available. Start an ACP server with registered agents first.")
            return

        agent_name = agents_response.agents[0].name
        print(f"\nUsing agent: {agent_name}")

        # Method 1: Using run_sync with full message objects
        print("\n--- Method 1: Full message objects ---")
        response = await client.run_sync(
            agent=agent_name,
            input=[
                Message(
                    role="user",
                    parts=[
                        MessagePart(
                            content="What is 2 + 2?",
                            content_type="text/plain"
                        )
                    ]
                )
            ]
        )

        print(f"Run ID: {response.run_id}")
        print(f"Status: {response.status}")

        if response.output:
            for msg in response.output:
                for part in msg.parts:
                    if part.content:
                        print(f"Output: {part.content}")

        # Method 2: Using the convenience method for text
        print("\n--- Method 2: Convenience text method ---")
        text_result = await client.run_text(
            agent=agent_name,
            text="Tell me a short joke about programming."
        )
        print(f"Response: {text_result}")

        # Method 3: Using helper method on Message class
        print("\n--- Method 3: Message.user_text() helper ---")
        response = await client.run_sync(
            agent=agent_name,
            input=[Message.user_text("What is the capital of France?")]
        )

        if response.status == RunStatus.COMPLETED and response.output:
            for part in response.output[0].parts:
                if part.content:
                    print(f"Answer: {part.content}")


# ==============================================================================
# Example 3: Asynchronous Agent Execution with Polling
# ==============================================================================

async def example_async_execution():
    """
    Demonstrates asynchronous agent execution with polling.

    In async mode, the run starts immediately and you poll for completion.
    This is useful for long-running tasks or when you want to do other work
    while waiting.
    """
    print("\n" + "=" * 60)
    print("Example 3: Asynchronous Execution with Polling")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name
        print(f"\nUsing agent: {agent_name}")

        # Start an async run
        print("\nStarting async run...")
        run_id = await client.run_async(
            agent=agent_name,
            input=[Message.user_text("Write a haiku about async programming.")]
        )
        print(f"Run ID: {run_id}")
        print("Run started, polling for completion...")

        # Check status immediately
        current_response = await client.get_run(run_id)
        print(f"Initial status: {current_response.status}")

        # Wait for completion with custom polling interval
        final_response = await client.wait_for_run(
            run_id=run_id,
            poll_interval=0.5,  # Poll every 500ms
            timeout=30.0        # Timeout after 30 seconds
        )

        print(f"Final status: {final_response.status}")

        if final_response.status == RunStatus.COMPLETED and final_response.output:
            print("\nResult:")
            for msg in final_response.output:
                for part in msg.parts:
                    if part.content:
                        print(f"  {part.content}")
        elif final_response.status == RunStatus.FAILED:
            print(f"Run failed: {final_response.error}")


# ==============================================================================
# Example 4: Streaming Agent Responses
# ==============================================================================

async def example_streaming():
    """
    Demonstrates streaming responses from an agent.

    Streaming mode is useful for:
    - Long-running generations where you want to show progress
    - Real-time applications like chatbots
    - Large responses that you want to display incrementally
    """
    print("\n" + "=" * 60)
    print("Example 4: Streaming Responses")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name
        print(f"\nUsing agent: {agent_name}")
        print("\nStreaming response:")
        print("-" * 40)

        # Stream the response
        async for event in client.run_stream(
            agent=agent_name,
            input=[Message.user_text("Count from 1 to 5, explaining each number.")]
        ):
            if isinstance(event, Message):
                # This is a message chunk
                for part in event.parts:
                    if part.content:
                        print(part.content, end="", flush=True)
            elif isinstance(event, dict):
                # This is a status event (start, complete, etc.)
                event_type = event.get("type", "unknown")
                if event_type == "run_start":
                    print(f"\n[Run started: {event.get('run_id')}]")
                elif event_type == "run_complete":
                    print(f"\n[Run completed]")
                elif event_type == "error":
                    print(f"\n[Error: {event.get('message')}]")

        print("\n" + "-" * 40)


# ==============================================================================
# Example 5: Session Management for Multi-Turn Conversations
# ==============================================================================

async def example_session_management():
    """
    Demonstrates session management for multi-turn conversations.

    Sessions allow:
    - Maintaining context across multiple runs
    - Tracking conversation history
    - Storing custom context data
    """
    print("\n" + "=" * 60)
    print("Example 5: Session Management")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name

        # Create a session manager for local session tracking
        session_manager = SessionManager()

        # Create a new session
        session = session_manager.create_session(
            agent_name=agent_name,
            metadata={"user_id": "example_user", "topic": "math_help"}
        )

        print(f"\nCreated session: {session.session_id}")
        print(f"Agent: {session.agent_name}")

        # First turn
        print("\n--- Turn 1 ---")
        user_msg_1 = Message.user_text("My name is Alice. What is 5 + 3?")
        session.add_message(user_msg_1)  # Track locally

        response_1 = await client.run_sync(
            agent=agent_name,
            input=[user_msg_1],
            session_id=session.session_id  # Pass session ID to server
        )

        if response_1.output:
            for msg in response_1.output:
                session.add_message(msg)  # Track response locally
                for part in msg.parts:
                    if part.content:
                        print(f"Agent: {part.content}")

        # Second turn - agent should remember context
        print("\n--- Turn 2 ---")
        user_msg_2 = Message.user_text("What's my name? And what was the result of my math problem?")
        session.add_message(user_msg_2)

        response_2 = await client.run_sync(
            agent=agent_name,
            input=[user_msg_2],
            session_id=session.session_id
        )

        if response_2.output:
            for msg in response_2.output:
                session.add_message(msg)
                for part in msg.parts:
                    if part.content:
                        print(f"Agent: {part.content}")

        # Show session state
        print(f"\n--- Session Summary ---")
        print(f"Session ID: {session.session_id}")
        print(f"Total messages: {len(session.messages)}")
        print(f"Run count: {session.run_count}")
        print(f"Created at: {session.created_at}")
        print(f"Last activity: {session.last_activity_at}")

        # Use context for custom state
        session.set_context("conversation_topic", "math_and_names")
        session.set_context("user_sentiment", "curious")
        print(f"Context: {session.context}")

        # Get last messages
        print("\nLast 2 messages in session:")
        for msg in session.get_messages_since(2):
            role = msg.role
            text = msg.parts[0].content if msg.parts and msg.parts[0].content else "[no content]"
            print(f"  [{role}]: {text[:50]}...")

        # List all sessions
        print(f"\nActive sessions: {len(session_manager.list_sessions())}")

        # Close session when done
        session_manager.close_session(session.session_id)
        print(f"Session closed. Remaining sessions: {len(session_manager.list_sessions())}")


# ==============================================================================
# Example 6: Agent Discovery with Caching and Filtering
# ==============================================================================

async def example_discovery_with_caching():
    """
    Demonstrates agent discovery with caching and filtering capabilities.

    The AgentDiscovery service provides:
    - Automatic caching with configurable TTL
    - Filtering by capability, domain, tag
    - Filtering by content types
    - Health status tracking
    """
    print("\n" + "=" * 60)
    print("Example 6: Discovery with Caching and Filtering")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        # Create discovery service with 5-minute cache TTL
        discovery = AgentDiscovery(cache_ttl_seconds=300)

        # Fetch and cache agents
        agents_response = await client.list_agents()
        discovery.cache_agents(agents_response.agents)

        print(f"\nCached {len(agents_response.agents)} agents")

        # Get from cache (no network call)
        if agents_response.agents:
            agent_name = agents_response.agents[0].name
            cached_agent = discovery.get_cached_agent(agent_name)
            if cached_agent:
                print(f"\nRetrieved from cache: {cached_agent.name}")

        # Get all active agents
        active_agents = discovery.get_active_agents()
        print(f"Active agents: {len(active_agents)}")

        # Filter by capability (example)
        code_agents = discovery.find_by_capability("code_generation")
        print(f"Agents with 'code_generation' capability: {len(code_agents)}")

        # Filter by domain
        finance_agents = discovery.find_by_domain("finance")
        print(f"Agents in 'finance' domain: {len(finance_agents)}")

        # Filter by tag
        beta_agents = discovery.find_by_tag("beta")
        print(f"Agents with 'beta' tag: {len(beta_agents)}")

        # Filter by content type
        image_agents = discovery.find_by_content_type(
            input_type="image/png",
            output_type="text/plain"
        )
        print(f"Agents that accept PNG and output text: {len(image_agents)}")

        # Invalidate cache
        discovery.invalidate_cache()
        print("\nCache invalidated")

        # Cache is now empty
        all_cached = discovery.get_all_cached()
        print(f"Agents in cache after invalidation: {len(all_cached)}")


# ==============================================================================
# Example 7: Run Manager with Lifecycle Callbacks
# ==============================================================================

async def example_run_callbacks():
    """
    Demonstrates run lifecycle management with callbacks.

    The RunManager allows you to:
    - Track active runs
    - Register callbacks for lifecycle events (start, complete, fail, await)
    - Get runs by status
    """
    print("\n" + "=" * 60)
    print("Example 7: Run Manager with Callbacks")
    print("=" * 60)

    # Create run manager
    run_manager = RunManager()

    # Register callbacks
    async def on_run_start(response: RunResponse):
        print(f"  [CALLBACK] Run started: {response.run_id}")

    async def on_run_complete(response: RunResponse):
        print(f"  [CALLBACK] Run completed: {response.run_id}")
        if response.output:
            text = response.output[0].parts[0].content if response.output[0].parts else ""
            print(f"  [CALLBACK] Output preview: {text[:50]}...")

    async def on_run_fail(response: RunResponse):
        print(f"  [CALLBACK] Run failed: {response.run_id}")
        if response.error:
            print(f"  [CALLBACK] Error: {response.error.message}")

    async def on_run_await(response: RunResponse):
        print(f"  [CALLBACK] Run awaiting input: {response.run_id}")
        if response.await_request:
            print(f"  [CALLBACK] Awaiting: {response.await_request.type}")

    run_manager.on_start(on_run_start)
    run_manager.on_complete(on_run_complete)
    run_manager.on_fail(on_run_fail)
    run_manager.on_await(on_run_await)

    print("\nCallbacks registered for: start, complete, fail, await")

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name

        # Start a run
        print(f"\nStarting run with agent: {agent_name}")
        response = await client.run_sync(
            agent=agent_name,
            input=[Message.user_text("Say hello!")]
        )

        # Track the run
        run_manager.track_run(response)
        print(f"Tracking run: {response.run_id}")

        # Update status (this triggers callbacks)
        await run_manager.update_run_status(response.run_id, response)

        # Show tracked runs
        print(f"\nActive tracked runs: {len(run_manager.get_active_runs())}")

        # Get runs by status
        completed = run_manager.get_runs_by_status(RunStatus.COMPLETED)
        print(f"Completed runs: {len(completed)}")


# ==============================================================================
# Example 8: Batch Operations
# ==============================================================================

async def example_batch_operations():
    """
    Demonstrates batch operations for running multiple agents concurrently.

    The BatchRunManager provides:
    - Concurrent execution with configurable concurrency limit
    - Sequential execution with optional stop-on-error
    """
    print("\n" + "=" * 60)
    print("Example 8: Batch Operations")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name

        # Create batch manager with max 5 concurrent runs
        batch_manager = BatchRunManager(max_concurrent=5)

        # Prepare batch inputs
        questions = [
            "What is 1 + 1?",
            "What is 2 + 2?",
            "What is 3 + 3?",
            "What is 4 + 4?",
            "What is 5 + 5?",
        ]

        # Define the run function
        async def run_question(question: str) -> RunResponse:
            return await client.run_sync(
                agent=agent_name,
                input=[Message.user_text(question)]
            )

        # Run batch concurrently
        print(f"\n--- Concurrent Batch (max 5 at once) ---")
        print(f"Running {len(questions)} questions concurrently...")

        import time
        start_time = time.time()

        results = await batch_manager.run_batch(
            run_func=run_question,
            inputs=questions
        )

        elapsed = time.time() - start_time
        print(f"Completed in {elapsed:.2f}s")

        for i, (question, result) in enumerate(zip(questions, results)):
            status = result.status
            answer = ""
            if result.output and result.output[0].parts:
                answer = result.output[0].parts[0].content or ""
            print(f"  Q{i+1}: {question} -> [{status}] {answer[:30]}...")

        # Run batch sequentially
        print(f"\n--- Sequential Batch ---")
        print(f"Running {len(questions)} questions sequentially...")

        start_time = time.time()

        sequential_results = await batch_manager.run_sequential(
            run_func=run_question,
            inputs=questions[:3],  # Just run 3 for demo
            stop_on_error=False
        )

        elapsed = time.time() - start_time
        print(f"Completed in {elapsed:.2f}s")

        for i, result in enumerate(sequential_results):
            print(f"  Result {i+1}: {result.status}")


# ==============================================================================
# Example 9: Error Handling
# ==============================================================================

async def example_error_handling():
    """
    Demonstrates proper error handling when working with ACP clients.
    """
    print("\n" + "=" * 60)
    print("Example 9: Error Handling")
    print("=" * 60)

    from app.acp.client.base import ACPClientError

    # Example 1: Handle connection errors
    print("\n--- Connection Error Handling ---")
    try:
        async with ACPClient(
            base_url="http://localhost:99999",  # Invalid port
            timeout=5.0
        ) as client:
            await client.list_agents()
    except Exception as e:
        print(f"Connection error handled: {type(e).__name__}: {e}")

    # Example 2: Handle agent not found
    print("\n--- Agent Not Found Handling ---")
    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        try:
            await client.get_agent("non_existent_agent_xyz")
        except ACPClientError as e:
            print(f"Agent not found error handled: {e}")
            print(f"  Error code: {e.code}")

    # Example 3: Handle run failures
    print("\n--- Run Failure Handling ---")
    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if agents_response.agents:
            agent_name = agents_response.agents[0].name

            # This might fail depending on the agent
            response = await client.run_sync(
                agent=agent_name,
                input=[Message.user_text("Test message")]
            )

            if response.status == RunStatus.FAILED:
                print(f"Run failed gracefully")
                if response.error:
                    print(f"  Error code: {response.error.code}")
                    print(f"  Error message: {response.error.message}")
            else:
                print(f"Run succeeded with status: {response.status}")

    # Example 4: Handle timeout
    print("\n--- Timeout Handling ---")
    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if agents_response.agents:
            agent_name = agents_response.agents[0].name

            try:
                run_id = await client.run_async(
                    agent=agent_name,
                    input=[Message.user_text("Quick test")]
                )

                # Wait with very short timeout
                await client.wait_for_run(
                    run_id=run_id,
                    poll_interval=0.1,
                    timeout=0.01  # Very short timeout for demo
                )
            except ACPClientError as e:
                if e.code == "timeout":
                    print(f"Timeout handled: {e}")
                else:
                    raise


# ==============================================================================
# Example 10: Advanced - Resuming Awaiting Runs
# ==============================================================================

async def example_resume_awaiting():
    """
    Demonstrates handling runs that enter the 'awaiting' state.

    Some agents may request additional input from the user during execution.
    When this happens, the run enters the AWAITING state and can be resumed.
    """
    print("\n" + "=" * 60)
    print("Example 10: Resuming Awaiting Runs")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name

        # Start a run that might request additional input
        run_id = await client.run_async(
            agent=agent_name,
            input=[Message.user_text("Please ask me a clarifying question.")]
        )

        # Wait for the run (it might complete or enter awaiting state)
        response = await client.wait_for_run(run_id, timeout=30.0)

        print(f"Run status: {response.status}")

        if response.status == RunStatus.AWAITING:
            print("\nRun is awaiting input!")

            if response.await_request:
                print(f"  Type: {response.await_request.type}")
                print(f"  Description: {response.await_request.description}")

                if response.await_request.schema_:
                    print(f"  Expected schema: {response.await_request.schema_}")

            # Resume the run with additional input
            print("\nResuming run with additional input...")

            resumed = await client.resume_run(
                run_id=run_id,
                input=[Message.user_text("Here is my clarification: I want a simple answer.")]
            )

            # Wait for completion after resuming
            if resumed.status in [RunStatus.IN_PROGRESS, RunStatus.CREATED]:
                final = await client.wait_for_run(run_id)
                print(f"Final status: {final.status}")

                if final.output:
                    for msg in final.output:
                        for part in msg.parts:
                            if part.content:
                                print(f"Output: {part.content}")
            else:
                print(f"Resumed status: {resumed.status}")

        elif response.status == RunStatus.COMPLETED:
            print("\nRun completed without awaiting:")
            if response.output:
                for msg in response.output:
                    for part in msg.parts:
                        if part.content:
                            print(f"  {part.content}")


# ==============================================================================
# Example 11: Multi-Modal Content
# ==============================================================================

async def example_multimodal():
    """
    Demonstrates handling multi-modal content (text, images, etc.).
    """
    print("\n" + "=" * 60)
    print("Example 11: Multi-Modal Content")
    print("=" * 60)

    import base64

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()

        # Find an agent that accepts images
        image_agents = [
            a for a in agents_response.agents
            if any("image" in ct for ct in a.input_content_types)
        ]

        if not image_agents:
            print("\nNo agents accepting image input found.")
            print("Demonstrating message structure for multi-modal content:")

            # Show how to construct multi-modal messages
            multimodal_message = Message(
                role="user",
                parts=[
                    # Text part
                    MessagePart(
                        content="Please describe this image:",
                        content_type="text/plain"
                    ),
                    # Image part (example with base64 encoded data)
                    MessagePart(
                        content=base64.b64encode(b"fake-image-data").decode(),
                        content_type="image/png",
                        content_encoding="base64",  # type: ignore
                        name="example.png"
                    ),
                    # URL reference (alternative to inline content)
                    MessagePart(
                        content_url="https://example.com/image.jpg",
                        content_type="image/jpeg",
                        name="remote_image.jpg"
                    ),
                ]
            )

            print(f"\nMulti-modal message structure:")
            print(f"  Role: {multimodal_message.role}")
            print(f"  Parts: {len(multimodal_message.parts)}")
            for i, part in enumerate(multimodal_message.parts):
                print(f"    Part {i+1}:")
                print(f"      Type: {part.content_type}")
                print(f"      Name: {part.name}")
                if part.content:
                    print(f"      Content: {part.content[:30]}...")
                if part.content_url:
                    print(f"      URL: {part.content_url}")
        else:
            agent_name = image_agents[0].name
            print(f"\nFound image-accepting agent: {agent_name}")
            # Would run the agent with actual image data here


# ==============================================================================
# Example 12: Cancelling Runs
# ==============================================================================

async def example_cancel_run():
    """
    Demonstrates how to cancel a running agent execution.
    """
    print("\n" + "=" * 60)
    print("Example 12: Cancelling Runs")
    print("=" * 60)

    async with ACPClient(base_url=ACP_SERVER_URL, timeout=DEFAULT_TIMEOUT) as client:
        agents_response = await client.list_agents()
        if not agents_response.agents:
            print("\nNo agents available.")
            return

        agent_name = agents_response.agents[0].name

        # Start a long-running async job
        print(f"\nStarting async run with agent: {agent_name}")
        run_id = await client.run_async(
            agent=agent_name,
            input=[Message.user_text("Count slowly from 1 to 100.")]
        )
        print(f"Run ID: {run_id}")

        # Wait a moment
        await asyncio.sleep(0.5)

        # Check current status
        status_response = await client.get_run(run_id)
        print(f"Current status: {status_response.status}")

        # Cancel the run
        if status_response.status == RunStatus.IN_PROGRESS:
            print("Cancelling run...")
            cancel_response = await client.cancel_run(run_id)
            print(f"Status after cancel: {cancel_response.status}")
        else:
            print("Run already completed before we could cancel it")


# ==============================================================================
# Main Entry Point
# ==============================================================================

async def run_all_examples():
    """Run all examples sequentially."""
    examples = [
        ("discovery", example_agent_discovery),
        ("sync", example_sync_execution),
        ("async", example_async_execution),
        ("streaming", example_streaming),
        ("sessions", example_session_management),
        ("caching", example_discovery_with_caching),
        ("callbacks", example_run_callbacks),
        ("batch", example_batch_operations),
        ("errors", example_error_handling),
        ("resume", example_resume_awaiting),
        ("multimodal", example_multimodal),
        ("cancel", example_cancel_run),
    ]

    for name, example_func in examples:
        try:
            await example_func()
        except Exception as e:
            print(f"\n[!] Example '{name}' failed: {e}")
            logger.exception(f"Example {name} failed")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("ACP Client Usage Examples")
    print("=" * 60)
    print(f"Server URL: {ACP_SERVER_URL}")
    print(f"Timeout: {DEFAULT_TIMEOUT}s")

    if len(sys.argv) > 1:
        # Run specific example
        example_map = {
            "basic": example_sync_execution,
            "discovery": example_agent_discovery,
            "sync": example_sync_execution,
            "async": example_async_execution,
            "streaming": example_streaming,
            "sessions": example_session_management,
            "caching": example_discovery_with_caching,
            "callbacks": example_run_callbacks,
            "batch": example_batch_operations,
            "errors": example_error_handling,
            "resume": example_resume_awaiting,
            "multimodal": example_multimodal,
            "cancel": example_cancel_run,
        }

        example_name = sys.argv[1].lower()
        if example_name in example_map:
            await example_map[example_name]()
        else:
            print(f"\nUnknown example: {example_name}")
            print(f"Available examples: {', '.join(example_map.keys())}")
    else:
        # Run all examples
        await run_all_examples()


if __name__ == "__main__":
    asyncio.run(main())
