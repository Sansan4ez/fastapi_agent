# ACP (Agent Communication Protocol) Research Summary

## Overview

The **Agent Communication Protocol (ACP)** is an open protocol for agent interoperability, originally introduced by IBM's BeeAI. It enables AI agents to collaborate across teams, frameworks, technologies, and organizations through a standardized REST-based communication layer.

> **Important Note**: ACP has been merged with A2A (Agent-to-Agent) under the Linux Foundation. The ACP team is winding down active development and contributing its technology to A2A.

## Core Concepts

### Protocol Architecture

ACP implements a **layered, REST-native framework** with three primary roles:

1. **Agent Client**: Initiates discovery and constructs structured requests
2. **ACP Server**: Acts as protocol broker, maintaining registries and enforcing policies
3. **ACP Agent**: Executes domain-specific logic at the endpoint (can be stateless or stateful)

The architecture follows a **brokered client-server model** where the central server performs agent lookup, routing, and policy enforcement.

### Design Principles

- **Framework Agnostic**: Works with any agent framework (BeeAI, LangChain, CrewAI, custom code)
- **REST-based**: Uses standard HTTP patterns (not JSON-RPC like MCP)
- **MIME-typed Messages**: Supports any content type out of the box
- **No SDK Required**: Can be used with standard HTTP tools (curl, Postman, etc.)

## API Specification

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/agents` | GET | List available agents (supports pagination) |
| `/agents/{name}` | GET | Get specific agent manifest |
| `/runs` | POST | Create and start a new agent run |
| `/runs/{run_id}` | GET | Get run status and details |
| `/runs/{run_id}` | POST | Resume a paused/awaiting run |
| `/runs/{run_id}/cancel` | POST | Cancel a specified run |
| `/runs/{run_id}/events` | GET | List events for a run |
| `/session/{session_id}` | GET | Retrieve session details |

### Run Lifecycle States

```
created → in-progress → completed
                     → failed
                     → awaiting (pause for external info)
                     → cancelling → cancelled
```

**States:**
- `created` - Run has been created but not started
- `in-progress` - Run is actively executing
- `awaiting` - Agent is paused, waiting for external information
- `cancelling` - Cancellation has been requested
- `cancelled` - Run was cancelled
- `completed` - Run finished successfully
- `failed` - Run terminated with an error

### Agent Lifecycle States

```
INITIALIZING → ACTIVE → DEGRADED → RETIRING → RETIRED
```

Lifecycle metadata (version, createdBy, successorAgent) can be emitted as OpenTelemetry spans for operational monitoring.

## Message Format

### Message Structure

```json
{
  "role": "user" | "agent" | "agent/{agent_name}",
  "parts": [
    {
      "content": "Hello, agent!",
      "content_type": "text/plain",
      "content_encoding": "plain" | "base64",
      "content_url": "https://...",
      "name": "optional_artifact_name",
      "metadata": {}
    }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T00:00:01Z"
}
```

### MessagePart

Each part can contain:
- `content` - Inline content (mutually exclusive with content_url)
- `content_url` - URL to external content
- `content_type` - MIME type (default: "text/plain")
- `content_encoding` - "plain" or "base64"
- `name` - Optional identifier for artifacts
- `metadata` - Optional (CitationMetadata or TrajectoryMetadata)

### Metadata Types

**CitationMetadata**: Inline citations with source tracking
**TrajectoryMetadata**: Agent reasoning steps or tool execution records

## Request/Response Schemas

### RunCreateRequest

```json
{
  "agent": "agent_name",
  "input": [
    {
      "role": "user",
      "parts": [
        {
          "content": "What is the weather?",
          "content_type": "text/plain"
        }
      ]
    }
  ],
  "session_id": "optional_session_id",
  "mode": "sync" | "async" | "stream"
}
```

### Run Response

```json
{
  "run_id": "uuid",
  "agent_name": "my_agent",
  "session_id": "session_uuid",
  "status": "completed",
  "output": [
    {
      "role": "agent",
      "parts": [
        {
          "content": "The weather is sunny.",
          "content_type": "text/plain"
        }
      ]
    }
  ],
  "error": null,
  "created_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T00:00:01Z"
}
```

### Error Schema

```json
{
  "code": "server_error" | "invalid_input" | "not_found",
  "message": "Error description",
  "data": {}
}
```

## Agent Manifest

Agents expose a manifest describing their capabilities:

```json
{
  "name": "weather_agent",
  "description": "Provides weather information",
  "input_content_types": ["text/plain"],
  "output_content_types": ["text/plain", "application/json"],
  "metadata": {
    "documentation": "https://...",
    "license": "MIT",
    "capabilities": ["weather", "forecasting"],
    "domains": ["weather"],
    "tags": ["weather", "api"],
    "dependencies": []
  }
}
```

## Execution Modes

### Synchronous (sync)
- Plain HTTP POST returning JSON
- Blocks until completion

### Asynchronous (async)
- Fire-and-forget with run_id
- Poll or subscribe for progress

### Streaming
- Server pushes incremental delta messages
- Uses WebSockets/SSE
- Ideal for long-running tasks with partial results

## Await Mechanism

Agents can pause execution to request external information:

1. Agent yields an `await` response with required information type
2. Run status changes to `awaiting`
3. Client provides the requested information via `POST /runs/{run_id}`
4. Agent resumes with the provided data

## Session Management

Sessions maintain state and conversation history across multiple interactions:

- Each session has a unique `session_id`
- Sessions support multi-turn conversations
- Sessions can persist across agent restarts
- The SDK automatically manages session state

## Discovery Mechanisms

### Registry-based
- Centralized API for agent lookup
- `GET /agents` returns available agents

### Well-known URLs
- Agents can publish manifests at `/.well-known/agent.yml`
- Decentralized discovery through known endpoints

### Deployment Metadata
- Container labels, service mesh annotations, etc.

## Python SDK Usage

### Installation

```bash
pip install acp-sdk
```

### Server Implementation

```python
import asyncio
from typing import AsyncGenerator
from acp_sdk.models import Message, MessagePart
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server()

@server.agent()
async def my_agent(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """A simple agent that echoes input."""
    for message in input:
        # Yield intermediate thoughts
        yield {"thought": "Processing message..."}

        # Yield the response
        yield Message(
            role="agent",
            parts=[
                MessagePart(
                    content=f"You said: {message.parts[0].content}",
                    content_type="text/plain"
                )
            ]
        )

if __name__ == "__main__":
    server.run()
```

### Client Usage

```python
import asyncio
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

async def main():
    async with Client(base_url="http://localhost:8000") as client:
        # List available agents
        agents = await client.agents()

        # Run an agent synchronously
        run = await client.run_sync(
            agent="my_agent",
            input=[
                Message(
                    role="user",
                    parts=[
                        MessagePart(
                            content="Hello, agent!",
                            content_type="text/plain"
                        )
                    ]
                )
            ]
        )

        print(f"Response: {run.output}")

asyncio.run(main())
```

## TypeScript SDK

```bash
npm install acp-sdk
```

Currently provides client libraries and type-safe model definitions (no server component yet).

## Comparison with Other Protocols

| Dimension | ACP | MCP | A2A |
|-----------|-----|-----|-----|
| **Architecture** | Brokered client-server | Direct client-server | Peer-like |
| **Discovery** | Registry-based | Manual/static URLs | Agent Card retrieval |
| **Message Model** | Multipart MIME-typed | JSON-RPC 2.0 | JSON-RPC + Artifacts |
| **Session Handling** | Session-aware with run tracking | Stateless + optional context | Session-aware/stateless hybrid |
| **Target Use** | Infrastructure-level agents | LLM tool integration | Enterprise task delegation |

### ACP vs MCP

- **MCP** standardizes model-to-tool wiring (the "USB-C port" for LLM data sources and APIs)
- **ACP** operates one layer higher: agent-to-agent messaging, task hand-off, and lifecycle management

## Security Model

- Manifest signing for agent verification
- TLS transport encryption
- Bearer token validation with scoped lifetimes
- Message integrity through JSON Web Signatures (JWS)
- Capability tokens (unforgeable, signed objects encoding resource type, ops, and expiry)
- Kubernetes RBAC bridging for consistent policy enforcement

## References

- [Official Documentation](https://agentcommunicationprotocol.dev/)
- [GitHub Repository](https://github.com/i-am-bee/acp)
- [OpenAPI Specification](https://github.com/i-am-bee/acp/blob/main/docs/spec/openapi.yaml)
- [Python SDK](https://pypi.org/project/acp-sdk/)
- [IBM Think Article](https://www.ibm.com/think/topics/agent-communication-protocol)
- [WorkOS Technical Overview](https://workos.com/blog/ibm-agent-communication-protocol-acp)
- [Academic Survey Paper](https://arxiv.org/html/2505.02279v1)

## Applicability to This Project

Given the existing project architecture using pi-coding-agent with RPC over stdin/stdout, the ACP protocol could provide:

1. **Standardized Agent Interface**: Replace custom JSON-RPC with industry-standard REST endpoints
2. **Multi-Agent Orchestration**: Native support for agent discovery and task delegation
3. **Session Management**: Built-in support for multi-turn conversations (useful for Telegram integration)
4. **Streaming Support**: Native SSE/WebSocket streaming for real-time responses
5. **Framework Interoperability**: Ability to integrate agents from different frameworks

### Migration Considerations

- Current RPC approach: JSON commands over stdin/stdout
- ACP approach: REST API with standardized endpoints
- Both support sessions and async execution
- ACP adds: discovery, manifests, standardized error handling, security model
