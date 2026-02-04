"""
Example ACP Agent Implementations

This module demonstrates how to implement ACP (Agent Communication Protocol) agents
using the server-side framework. It covers:

- Basic agent with decorator pattern
- Stateful agent with session context
- Streaming agent with intermediate outputs
- Agent with human-in-the-loop (await pattern)
- Multi-modal agent handling different content types
- Agent with error handling
- Agent with metadata and capabilities

Based on the ACP protocol specification and internal implementation patterns.

Usage:
    # Start the server with example agents
    python -m examples.acp_agent_examples

    # Or import and register with your own server
    from examples.acp_agent_examples import register_example_agents
    register_example_agents(your_acp_server)
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator
from uuid import uuid4

from loguru import logger

# Import directly from submodules to avoid triggering app config loading
# This allows the example to be imported/tested independently
from app.acp.core.models import (
    Message,
    MessagePart,
    AgentMetadata,
    AwaitRequest,
)
from app.acp.core.types import ContentEncoding
from app.acp.server.base import ACPServer
from app.acp.server.context import Context
from app.acp.server.agent import RunYield, RunYieldResume


# ==============================================================================
# Create the ACP Server
# ==============================================================================

# Create a server instance for registering agents
server = ACPServer(name="example-acp-server", version="1.0.0")


# ==============================================================================
# Example 1: Basic Echo Agent
# ==============================================================================

@server.agent(
    name="echo",
    description="A simple agent that echoes back the user's input with a timestamp.",
    input_content_types=["text/plain"],
    output_content_types=["text/plain"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["echo", "text_processing"],
        "domains": ["utility"],
        "tags": ["simple", "demo", "beginner"],
    },
)
async def echo_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Echo agent that returns the input message with added metadata.

    This is the simplest form of an ACP agent - it receives messages
    and yields response messages.
    """
    logger.info(f"Echo agent invoked for run {context.run_id}")

    for message in input:
        # Extract text content from the message
        text = context.get_message_text(message)

        if text:
            response = (
                f"[Echo @ {datetime.utcnow().isoformat()}]\n"
                f"You said: {text}\n"
                f"Run ID: {context.run_id}"
            )
            yield Message.agent_text(response, agent_name="echo")


# ==============================================================================
# Example 2: Calculator Agent
# ==============================================================================

@server.agent(
    name="calculator",
    description="A calculator agent that evaluates mathematical expressions safely.",
    input_content_types=["text/plain"],
    output_content_types=["text/plain", "application/json"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["math", "calculation", "expression_evaluation"],
        "domains": ["math", "utility"],
        "tags": ["calculator", "math", "safe_eval"],
    },
)
async def calculator_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Calculator agent that safely evaluates mathematical expressions.

    Demonstrates:
    - Input validation
    - Safe expression evaluation
    - Structured JSON output alongside text
    """
    logger.info(f"Calculator agent invoked for run {context.run_id}")

    for message in input:
        text = context.get_message_text(message)

        if not text:
            yield Message.agent_text("Please provide a mathematical expression.", agent_name="calculator")
            continue

        # Clean the expression
        expression = text.strip()

        # Safe evaluation - only allow basic math operations
        allowed_chars = set("0123456789+-*/().% ")
        if not all(c in allowed_chars for c in expression):
            yield Message.agent_text(
                f"Invalid expression. Only numbers and basic operators (+, -, *, /, %) are allowed.",
                agent_name="calculator"
            )
            continue

        try:
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, {})

            # Yield both text and JSON responses
            text_response = f"Result: {expression} = {result}"
            yield Message.agent_text(text_response, agent_name="calculator")

            # Also yield structured JSON response
            json_response = Message(
                role="agent/calculator",
                parts=[
                    MessagePart(
                        content=json.dumps({
                            "expression": expression,
                            "result": result,
                            "type": type(result).__name__,
                        }),
                        content_type="application/json",
                    )
                ],
            )
            yield json_response

        except Exception as e:
            yield Message.agent_text(
                f"Error evaluating expression: {str(e)}",
                agent_name="calculator"
            )


# ==============================================================================
# Example 3: Stateful Conversation Agent
# ==============================================================================

@server.agent(
    name="conversation",
    description="A stateful agent that remembers conversation context within a session.",
    input_content_types=["text/plain"],
    output_content_types=["text/plain"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["conversation", "memory", "context_tracking"],
        "domains": ["chat", "assistant"],
        "tags": ["stateful", "session", "memory"],
    },
)
async def conversation_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Stateful conversation agent that tracks context across turns.

    Demonstrates:
    - Using session context for state management
    - Accessing conversation history
    - Storing and retrieving custom context values
    """
    logger.info(f"Conversation agent invoked for run {context.run_id}")

    # Get or initialize turn count
    turn_count = context.get_context_value("turn_count", 0) + 1
    context.set_context_value("turn_count", turn_count)

    # Get conversation history
    history = context.messages

    # Get last user message
    last_user_msg = context.get_last_user_message()
    user_text = context.get_message_text(last_user_msg) if last_user_msg else ""

    # Build response with context awareness
    response_parts = [
        f"Turn #{turn_count}",
        f"Session ID: {context.session_id or 'No session'}",
        f"History length: {len(history)} messages",
    ]

    if user_text:
        response_parts.append(f"You said: {user_text}")

        # Track mentioned topics
        topics = context.get_context_value("topics", [])

        # Simple topic extraction (in real agent, use NLP)
        words = user_text.lower().split()
        new_topics = [w for w in words if len(w) > 5 and w not in topics]
        if new_topics:
            topics.extend(new_topics[:3])  # Keep top 3 new topics
            context.set_context_value("topics", topics[-10:])  # Keep last 10 topics

        if topics:
            response_parts.append(f"Topics discussed: {', '.join(topics)}")

    yield Message.agent_text("\n".join(response_parts), agent_name="conversation")


# ==============================================================================
# Example 4: Streaming Counter Agent
# ==============================================================================

@server.agent(
    name="streaming_counter",
    description="An agent that streams incremental counting updates.",
    input_content_types=["text/plain"],
    output_content_types=["text/plain"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["streaming", "incremental_output"],
        "domains": ["demo"],
        "tags": ["streaming", "async", "incremental"],
    },
)
async def streaming_counter_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Streaming agent that yields incremental outputs.

    Demonstrates:
    - Streaming/incremental responses
    - Yielding multiple messages over time
    - Including thought/metadata dictionaries
    """
    logger.info(f"Streaming counter agent invoked for run {context.run_id}")

    # Extract count from input
    last_msg = context.get_last_user_message()
    text = context.get_message_text(last_msg) if last_msg else "5"

    try:
        count_to = min(int(text.strip()), 20)  # Cap at 20 to prevent abuse
    except ValueError:
        count_to = 5

    # Yield a thought (metadata) first
    yield {"thought": f"Starting to count to {count_to}..."}

    # Stream the counts
    for i in range(1, count_to + 1):
        # Simulate some processing time
        await asyncio.sleep(0.2)

        # Yield progress thoughts
        if i % 5 == 0:
            yield {"thought": f"Progress: {i}/{count_to}"}

        # Yield the actual count
        yield Message.agent_text(f"Count: {i}", agent_name="streaming_counter")

    # Final summary
    yield {"thought": "Counting complete!"}
    yield Message.agent_text(
        f"Finished counting from 1 to {count_to}!",
        agent_name="streaming_counter"
    )


# ==============================================================================
# Example 5: Approval Agent (Human-in-the-Loop)
# ==============================================================================

@server.agent(
    name="approval_workflow",
    description="An agent that demonstrates the human-in-the-loop pattern by requesting approval.",
    input_content_types=["text/plain", "application/json"],
    output_content_types=["text/plain", "application/json"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["approval", "workflow", "human_in_the_loop"],
        "domains": ["workflow", "business_process"],
        "tags": ["approval", "hitl", "await"],
    },
)
async def approval_workflow_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Approval workflow agent demonstrating the await/resume pattern.

    Demonstrates:
    - Pausing execution to await user input
    - Creating structured await requests with schemas
    - Resuming execution with new input
    """
    logger.info(f"Approval workflow agent invoked for run {context.run_id}")

    # Check if this is a resume (we have approval context)
    approval_pending = context.get_context_value("approval_pending", False)

    if not approval_pending:
        # First invocation - extract action and request approval
        last_msg = context.get_last_user_message()
        action = context.get_message_text(last_msg) if last_msg else "Unknown action"

        # Store the action for when we resume
        context.set_context_value("pending_action", action)
        context.set_context_value("approval_pending", True)

        # Inform user we're requesting approval
        yield Message.agent_text(
            f"Action requested: {action}\n"
            f"Awaiting approval...",
            agent_name="approval_workflow"
        )

        # Create await request for approval
        await_request = context.create_await_request(
            await_type="approval",
            description=f"Please approve or reject the action: {action}",
            schema={
                "type": "object",
                "properties": {
                    "approved": {"type": "boolean", "description": "Whether to approve"},
                    "reason": {"type": "string", "description": "Reason for decision"},
                },
                "required": ["approved"],
            },
            timeout_seconds=300,  # 5 minute timeout
        )

        # Yield the await request to pause execution
        yield {"await": await_request.model_dump()}

    else:
        # This is a resume - process the approval
        pending_action = context.get_context_value("pending_action", "Unknown")
        context.set_context_value("approval_pending", False)

        # Get the approval response from the resumed input
        last_msg = context.get_last_user_message()
        response_text = context.get_message_text(last_msg) if last_msg else ""

        # Try to parse as JSON, otherwise interpret as yes/no
        try:
            approval_data = json.loads(response_text)
            approved = approval_data.get("approved", False)
            reason = approval_data.get("reason", "No reason provided")
        except json.JSONDecodeError:
            # Simple text interpretation
            approved = response_text.lower().strip() in ["yes", "approve", "approved", "y", "true"]
            reason = response_text

        if approved:
            yield Message.agent_text(
                f"Action APPROVED: {pending_action}\n"
                f"Reason: {reason}\n"
                f"Proceeding with execution...",
                agent_name="approval_workflow"
            )
            # In a real agent, execute the action here
        else:
            yield Message.agent_text(
                f"Action REJECTED: {pending_action}\n"
                f"Reason: {reason}\n"
                f"Action cancelled.",
                agent_name="approval_workflow"
            )


# ==============================================================================
# Example 6: Multi-Modal Agent
# ==============================================================================

@server.agent(
    name="multimodal",
    description="An agent that handles multiple content types including text, JSON, and base64 data.",
    input_content_types=["text/plain", "application/json", "image/png", "image/jpeg"],
    output_content_types=["text/plain", "application/json"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["multimodal", "image_description", "json_processing"],
        "domains": ["media", "data_processing"],
        "tags": ["multimodal", "images", "json"],
    },
)
async def multimodal_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Multi-modal agent that processes different content types.

    Demonstrates:
    - Handling multiple input content types
    - Processing message parts with different MIME types
    - Returning structured analysis results
    """
    logger.info(f"Multi-modal agent invoked for run {context.run_id}")

    analysis_results = []

    for message in input:
        for part in message.parts:
            part_analysis = {
                "content_type": part.content_type,
                "has_content": bool(part.content),
                "has_url": bool(part.content_url),
                "encoding": part.content_encoding.value if part.content_encoding else "plain",
                "name": part.name,
            }

            if part.content_type == "text/plain" and part.content:
                part_analysis["text_length"] = len(part.content)
                part_analysis["preview"] = part.content[:100]

            elif part.content_type == "application/json" and part.content:
                try:
                    parsed = json.loads(part.content)
                    part_analysis["json_type"] = type(parsed).__name__
                    if isinstance(parsed, dict):
                        part_analysis["json_keys"] = list(parsed.keys())
                except json.JSONDecodeError:
                    part_analysis["json_error"] = "Invalid JSON"

            elif part.content_type.startswith("image/"):
                if part.content and part.content_encoding == ContentEncoding.BASE64:
                    # Calculate approximate size from base64
                    part_analysis["approx_size_bytes"] = len(part.content) * 3 // 4
                part_analysis["image_format"] = part.content_type.split("/")[1]

            analysis_results.append(part_analysis)

    # Return text summary
    summary = f"Analyzed {len(analysis_results)} content parts:\n"
    for i, result in enumerate(analysis_results, 1):
        summary += f"\n  Part {i}: {result['content_type']}"
        if "text_length" in result:
            summary += f" ({result['text_length']} chars)"
        if "json_keys" in result:
            summary += f" (keys: {', '.join(result['json_keys'][:5])})"
        if "approx_size_bytes" in result:
            summary += f" (~{result['approx_size_bytes']} bytes)"

    yield Message.agent_text(summary, agent_name="multimodal")

    # Also return structured JSON
    json_response = Message(
        role="agent/multimodal",
        parts=[
            MessagePart(
                content=json.dumps({"analysis": analysis_results}, indent=2),
                content_type="application/json",
            )
        ],
    )
    yield json_response


# ==============================================================================
# Example 7: Error Handling Agent
# ==============================================================================

@server.agent(
    name="error_demo",
    description="An agent that demonstrates error handling patterns.",
    input_content_types=["text/plain"],
    output_content_types=["text/plain"],
    metadata={
        "version": "1.0.0",
        "capabilities": ["error_handling", "demo"],
        "domains": ["testing"],
        "tags": ["error", "demo", "testing"],
    },
)
async def error_demo_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Agent demonstrating error handling patterns.

    Demonstrates:
    - Graceful error handling
    - Different error scenarios
    - Proper error messaging

    Send "error" to trigger an error, "timeout" for simulated timeout.
    """
    logger.info(f"Error demo agent invoked for run {context.run_id}")

    last_msg = context.get_last_user_message()
    command = context.get_message_text(last_msg).lower().strip() if last_msg else ""

    if command == "error":
        # Simulate an error
        raise ValueError("This is a simulated error for demonstration purposes")

    elif command == "timeout":
        # Simulate a long-running operation
        yield Message.agent_text("Starting long operation...", agent_name="error_demo")
        await asyncio.sleep(300)  # This would normally timeout
        yield Message.agent_text("Operation completed", agent_name="error_demo")

    elif command == "partial":
        # Demonstrate partial success before error
        yield Message.agent_text("Step 1: Initialization complete", agent_name="error_demo")
        yield Message.agent_text("Step 2: Processing...", agent_name="error_demo")
        raise RuntimeError("Error during step 2!")

    else:
        yield Message.agent_text(
            "Error Demo Agent\n"
            "Commands:\n"
            "  - 'error': Trigger a ValueError\n"
            "  - 'timeout': Simulate a long-running operation\n"
            "  - 'partial': Partial success before error\n"
            "  - anything else: This help message",
            agent_name="error_demo"
        )


# ==============================================================================
# Example 8: Comprehensive Task Agent
# ==============================================================================

@server.agent(
    name="task_processor",
    description="A comprehensive task processing agent with full feature demonstration.",
    input_content_types=["text/plain", "application/json"],
    output_content_types=["text/plain", "application/json"],
    metadata=AgentMetadata(
        version="2.0.0",
        license="MIT",
        documentation="https://example.com/docs/task_processor",
        capabilities=[
            "task_processing",
            "structured_output",
            "progress_tracking",
            "context_aware",
        ],
        domains=["productivity", "automation"],
        tags=["comprehensive", "demo", "production_ready"],
        created_by="ACP Examples Team",
    ),
)
async def task_processor_agent(
    input: list[Message],
    context: Context,
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Comprehensive task processing agent.

    Demonstrates:
    - Full AgentMetadata usage
    - Structured task processing
    - Progress tracking with thoughts
    - Complex output generation
    """
    logger.info(f"Task processor agent invoked for run {context.run_id}")

    # Get task from input
    last_msg = context.get_last_user_message()
    task_text = context.get_message_text(last_msg) if last_msg else ""

    # Try to parse as JSON task
    try:
        task = json.loads(task_text)
        task_type = task.get("type", "generic")
        task_data = task.get("data", {})
    except json.JSONDecodeError:
        task_type = "text"
        task_data = {"text": task_text}

    # Initialize task tracking
    task_id = str(uuid4())[:8]
    context.set_context_value(f"task_{task_id}", {
        "type": task_type,
        "status": "processing",
        "started_at": datetime.utcnow().isoformat(),
    })

    # Processing steps with progress
    steps = ["Validation", "Analysis", "Processing", "Completion"]

    for i, step in enumerate(steps, 1):
        yield {"thought": f"Step {i}/{len(steps)}: {step}"}
        await asyncio.sleep(0.3)  # Simulate work

        yield Message.agent_text(
            f"[{step}] Task {task_id}: Progress {i*25}%",
            agent_name="task_processor"
        )

    # Build result
    result = {
        "task_id": task_id,
        "type": task_type,
        "status": "completed",
        "input_data": task_data,
        "processed_at": datetime.utcnow().isoformat(),
        "run_id": str(context.run_id),
        "session_id": str(context.session_id) if context.session_id else None,
    }

    # Update task context
    context.set_context_value(f"task_{task_id}", {
        **result,
        "status": "completed",
    })

    # Yield final results
    yield Message.agent_text(
        f"Task {task_id} completed successfully!\n"
        f"Type: {task_type}\n"
        f"Processed at: {result['processed_at']}",
        agent_name="task_processor"
    )

    yield Message(
        role="agent/task_processor",
        parts=[
            MessagePart(
                content=json.dumps(result, indent=2),
                content_type="application/json",
            )
        ],
    )


# ==============================================================================
# Helper Functions
# ==============================================================================

def register_example_agents(target_server: ACPServer) -> None:
    """
    Register all example agents with a target ACP server.

    This allows importing the agents into a different server instance.

    Args:
        target_server: The ACP server to register agents with
    """
    # Get all registered agents from our example server
    agents, _ = server.registry.list_agents()

    for agent_manifest in agents:
        handler = server.registry.get(agent_manifest.name)
        if handler:
            try:
                target_server.registry.register(handler)
                logger.info(f"Registered agent: {agent_manifest.name}")
            except ValueError as e:
                logger.warning(f"Could not register {agent_manifest.name}: {e}")


def list_example_agents() -> list[str]:
    """
    List all example agent names.

    Returns:
        List of agent names
    """
    agents, _ = server.registry.list_agents()
    return [a.name for a in agents]


# ==============================================================================
# Main Entry Point
# ==============================================================================

async def main():
    """Run a demo of the example agents."""
    print("=" * 60)
    print("ACP Agent Examples")
    print("=" * 60)

    # List registered agents
    agents = list_example_agents()
    print(f"\nRegistered {len(agents)} example agents:")
    for name in agents:
        manifest = server.registry.get_manifest(name)
        if manifest:
            print(f"\n  - {name}")
            print(f"    Description: {manifest.description}")
            print(f"    Capabilities: {', '.join(manifest.metadata.capabilities)}")

    print("\n" + "=" * 60)
    print("To use these agents, start an ACP server and register them:")
    print("=" * 60)
    print("""
    from examples.acp_agent_examples import server, register_example_agents

    # Option 1: Use the pre-configured server
    from app.acp.integration.fastapi import create_acp_router
    router = create_acp_router(server)

    # Option 2: Register with your own server
    from app.acp.server import ACPServer
    my_server = ACPServer()
    register_example_agents(my_server)
    """)


if __name__ == "__main__":
    asyncio.run(main())
