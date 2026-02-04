# Comprehensive ACP (Agent Communication Protocol) Research Document

## Executive Summary

This document provides an in-depth analysis of the **Agent Communication Protocol (ACP)**, an open protocol originally developed by IBM's BeeAI for enabling AI agent interoperability. The research covers protocol architecture, implementation patterns, security considerations, and a detailed migration strategy for integrating ACP into our existing pi-coding-agent based technical support system.

> **Status Update**: As of late 2024, ACP has been merged with A2A (Agent-to-Agent) under the Linux Foundation. While active ACP development is winding down, its concepts and technology are being incorporated into the unified A2A standard.

---

## Table of Contents

1. [Protocol Overview](#1-protocol-overview)
2. [Core Architecture](#2-core-architecture)
3. [API Specification Deep Dive](#3-api-specification-deep-dive)
4. [Message Format and Data Structures](#4-message-format-and-data-structures)
5. [Execution Modes and Patterns](#5-execution-modes-and-patterns)
6. [Session Management](#6-session-management)
7. [Discovery Mechanisms](#7-discovery-mechanisms)
8. [Security Model](#8-security-model)
9. [Protocol Comparisons](#9-protocol-comparisons)
10. [SDK Implementation Guide](#10-sdk-implementation-guide)
11. [Migration Strategy](#11-migration-strategy)
12. [Implementation Roadmap](#12-implementation-roadmap)
13. [References and Resources](#13-references-and-resources)

---

## 1. Protocol Overview

### 1.1 What is ACP?

The **Agent Communication Protocol (ACP)** is a standardized, REST-based protocol designed to enable seamless communication and collaboration between AI agents across different frameworks, technologies, teams, and organizations. Unlike proprietary solutions, ACP provides a framework-agnostic approach to agent interoperability.

### 1.2 Key Characteristics

| Characteristic | Description |
|---------------|-------------|
| **Protocol Type** | REST-native HTTP/HTTPS |
| **Message Format** | MIME-typed multipart messages |
| **Architecture** | Brokered client-server model |
| **SDK Requirement** | None (works with standard HTTP tools) |
| **Framework Support** | Any (LangChain, CrewAI, BeeAI, custom) |
| **Transport** | HTTP/1.1, HTTP/2, WebSocket, SSE |

### 1.3 Design Philosophy

ACP follows these core principles:

1. **Framework Agnosticism**: Agents built with any framework can communicate
2. **MIME-typed Messages**: Support for any content type (text, images, JSON, binary)
3. **REST-native**: Standard HTTP patterns, no JSON-RPC complexity
4. **Progressive Enhancement**: Works with curl, scales to enterprise deployments
5. **Observability First**: Built-in support for OpenTelemetry tracing

### 1.4 Protocol Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (Agent Logic, Domain-Specific Processing, Business Rules)   │
├─────────────────────────────────────────────────────────────┤
│                    ACP Protocol Layer                        │
│  (Message Format, Run Lifecycle, Session Management)         │
├─────────────────────────────────────────────────────────────┤
│                    Transport Layer                           │
│  (HTTP/HTTPS, WebSocket, SSE for streaming)                  │
├─────────────────────────────────────────────────────────────┤
│                    Security Layer                            │
│  (TLS, JWT/Bearer Tokens, Capability Tokens)                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Architecture

### 2.1 Three-Tier Architecture

ACP implements a three-role architecture:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  ACP Client  │────▶│  ACP Server  │────▶│  ACP Agent   │
│              │◀────│   (Broker)   │◀────│              │
└──────────────┘     └──────────────┘     └──────────────┘
      │                    │                     │
      │                    │                     │
   Initiates            Routes &              Executes
   Requests           Manages State         Domain Logic
```

#### 2.1.1 ACP Client

**Responsibilities:**
- Initiates discovery requests to find available agents
- Constructs and sends structured requests
- Handles responses (sync, async, streaming)
- Manages client-side session state

**Implementation Pattern:**
```python
from acp_sdk.client import Client

async def client_example():
    async with Client(base_url="http://localhost:8000") as client:
        # Discovery
        agents = await client.agents()

        # Execution
        run = await client.run_sync(
            agent="support_agent",
            input=[Message(role="user", parts=[...])]
        )
```

#### 2.1.2 ACP Server (Broker)

**Responsibilities:**
- Maintains agent registry
- Routes requests to appropriate agents
- Enforces policies (rate limiting, access control)
- Manages run lifecycle and session state
- Provides monitoring and observability hooks

**Key Features:**
- Agent registration and deregistration
- Load balancing across agent instances
- Request queuing and prioritization
- Health checking and failover

#### 2.1.3 ACP Agent

**Responsibilities:**
- Registers with the server (publishes manifest)
- Processes incoming requests
- Yields intermediate results (streaming)
- Manages domain-specific logic
- Reports completion or failure

**Agent Types:**
- **Stateless**: Each request is independent
- **Stateful**: Maintains conversation context via sessions
- **Hybrid**: Session-aware but can operate statelessly

### 2.2 Brokered vs Direct Communication

| Aspect | Brokered (ACP) | Direct (MCP) |
|--------|---------------|--------------|
| Discovery | Centralized registry | Manual/static URLs |
| Routing | Server handles | Client handles |
| Scalability | Built-in load balancing | Manual |
| Security | Centralized policy | Per-agent |
| Complexity | Higher infrastructure | Lower infrastructure |

---

## 3. API Specification Deep Dive

### 3.1 Complete Endpoint Reference

#### Agent Management Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/agents` | GET | List all registered agents | `AgentList` |
| `/agents/{name}` | GET | Get agent manifest | `AgentManifest` |
| `/agents/{name}` | PUT | Register/update agent | `AgentManifest` |
| `/agents/{name}` | DELETE | Deregister agent | `204 No Content` |

#### Run Management Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/runs` | POST | Create new run | `Run` |
| `/runs/{run_id}` | GET | Get run status | `Run` |
| `/runs/{run_id}` | POST | Resume awaiting run | `Run` |
| `/runs/{run_id}/cancel` | POST | Cancel run | `Run` |
| `/runs/{run_id}/events` | GET | Get run events | `EventList` |

#### Session Endpoints

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/sessions` | POST | Create new session | `Session` |
| `/sessions/{session_id}` | GET | Get session details | `Session` |
| `/sessions/{session_id}` | DELETE | End session | `204 No Content` |
| `/sessions/{session_id}/history` | GET | Get conversation history | `MessageList` |

### 3.2 Run Lifecycle State Machine

```
                                    ┌─────────────────┐
                                    │                 │
                                    ▼                 │
┌─────────┐    ┌─────────────┐    ┌───────────┐      │
│ created │───▶│ in-progress │───▶│ completed │      │
└─────────┘    └─────────────┘    └───────────┘      │
                     │                               │
                     │  ┌───────────────────────────┐│
                     │  │                           ││
                     ├──┼───▶ ┌────────┐            ││
                     │  │     │ failed │            ││
                     │  │     └────────┘            ││
                     │  │                           ││
                     │  └───▶ ┌──────────┐  Resume  ││
                     │        │ awaiting │──────────┘│
                     │        └──────────┘           │
                     │                               │
                     └───▶ ┌────────────┐    ┌───────────┐
                          │ cancelling │───▶│ cancelled │
                          └────────────┘    └───────────┘
```

#### State Descriptions

| State | Description | Transitions |
|-------|-------------|-------------|
| `created` | Run initialized, not started | → `in-progress` |
| `in-progress` | Agent actively processing | → `completed`, `failed`, `awaiting`, `cancelling` |
| `awaiting` | Paused for external input | → `in-progress` (on resume) |
| `completed` | Successfully finished | Terminal |
| `failed` | Error occurred | Terminal |
| `cancelling` | Cancel requested | → `cancelled` |
| `cancelled` | Run was cancelled | Terminal |

### 3.3 Agent Lifecycle States

```
┌──────────────┐    ┌────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ INITIALIZING │───▶│ ACTIVE │───▶│ DEGRADED │───▶│ RETIRING │───▶│ RETIRED │
└──────────────┘    └────────┘    └──────────┘    └──────────┘    └─────────┘
                         │                              ▲
                         └──────────────────────────────┘
                              (Can skip DEGRADED)
```

---

## 4. Message Format and Data Structures

### 4.1 Message Structure

```json
{
  "role": "user | agent | agent/{agent_name}",
  "parts": [
    {
      "content": "string | base64_encoded_data",
      "content_type": "text/plain",
      "content_encoding": "plain | base64",
      "content_url": "https://example.com/resource",
      "name": "artifact_name",
      "metadata": {
        "type": "citation | trajectory",
        "data": {}
      }
    }
  ],
  "created_at": "2025-01-01T00:00:00Z",
  "completed_at": "2025-01-01T00:00:01Z"
}
```

### 4.2 Role Types

| Role | Description | Use Case |
|------|-------------|----------|
| `user` | Message from human/client | User queries, instructions |
| `agent` | Message from current agent | Responses, outputs |
| `agent/{name}` | Message from specific agent | Multi-agent scenarios |

### 4.3 Content Types Support

ACP supports any MIME type through its multipart message format:

| Content Type | Use Case | Encoding |
|--------------|----------|----------|
| `text/plain` | Simple text messages | plain |
| `text/markdown` | Formatted responses | plain |
| `application/json` | Structured data | plain |
| `image/png`, `image/jpeg` | Visual content | base64 |
| `audio/wav`, `audio/mp3` | Voice messages | base64 |
| `application/pdf` | Documents | base64 |
| `application/octet-stream` | Binary data | base64 |

### 4.4 Metadata Types

#### CitationMetadata

For tracking sources and references:

```json
{
  "type": "citation",
  "data": {
    "source_id": "kb-article-123",
    "source_type": "knowledge_base",
    "url": "https://docs.example.com/article",
    "title": "Troubleshooting Guide",
    "excerpt": "...",
    "confidence": 0.95
  }
}
```

#### TrajectoryMetadata

For recording agent reasoning and tool usage:

```json
{
  "type": "trajectory",
  "data": {
    "step": 3,
    "action": "tool_call",
    "tool": "crm_lookup",
    "input": {"customer_id": "12345"},
    "output": {"balance": 100.50, "status": "active"},
    "reasoning": "Looking up customer account to check balance",
    "duration_ms": 150
  }
}
```

### 4.5 Complete Request/Response Examples

#### Run Creation Request

```json
{
  "agent": "technical_support_agent",
  "input": [
    {
      "role": "user",
      "parts": [
        {
          "content": "У меня не работает интернет",
          "content_type": "text/plain"
        }
      ]
    }
  ],
  "session_id": "telegram-user-123456",
  "mode": "stream",
  "config": {
    "timeout_ms": 30000,
    "max_tokens": 2048,
    "temperature": 0.7
  }
}
```

#### Run Response

```json
{
  "run_id": "run-abc123",
  "agent_name": "technical_support_agent",
  "session_id": "telegram-user-123456",
  "status": "completed",
  "output": [
    {
      "role": "agent",
      "parts": [
        {
          "content": "Здравствуйте! Давайте проверим состояние вашего подключения. Пожалуйста, назовите ваш лицевой счёт или номер телефона.",
          "content_type": "text/plain",
          "metadata": {
            "type": "trajectory",
            "data": {
              "steps": [
                {"action": "identify_intent", "result": "connectivity_issue"},
                {"action": "initiate_identification", "result": "awaiting_customer_id"}
              ]
            }
          }
        }
      ],
      "created_at": "2025-01-01T10:00:00Z"
    }
  ],
  "error": null,
  "created_at": "2025-01-01T10:00:00Z",
  "completed_at": "2025-01-01T10:00:02Z",
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 45,
    "total_tokens": 195
  }
}
```

---

## 5. Execution Modes and Patterns

### 5.1 Synchronous Mode

**Characteristics:**
- Blocking HTTP request
- Response returned when complete
- Simple to implement
- Best for quick operations

```python
# Client usage
run = await client.run_sync(
    agent="support_agent",
    input=[message],
    timeout=30.0
)
print(run.output)
```

**HTTP Flow:**
```
Client                          Server
   │                               │
   │  POST /runs (mode=sync)       │
   │──────────────────────────────▶│
   │                               │  Process...
   │                               │
   │  200 OK + Complete Response   │
   │◀──────────────────────────────│
   │                               │
```

### 5.2 Asynchronous Mode

**Characteristics:**
- Non-blocking request
- Returns run_id immediately
- Poll for status/results
- Best for long-running tasks

```python
# Start run
run = await client.run_async(
    agent="analysis_agent",
    input=[message]
)

# Poll for completion
while True:
    status = await client.get_run(run.run_id)
    if status.status in ["completed", "failed"]:
        break
    await asyncio.sleep(1)

print(status.output)
```

**HTTP Flow:**
```
Client                          Server
   │                               │
   │  POST /runs (mode=async)      │
   │──────────────────────────────▶│
   │                               │
   │  202 Accepted + run_id        │
   │◀──────────────────────────────│
   │                               │
   │  GET /runs/{run_id}           │
   │──────────────────────────────▶│
   │  200 OK + status=in-progress  │
   │◀──────────────────────────────│
   │                               │
   │  GET /runs/{run_id}           │
   │──────────────────────────────▶│
   │  200 OK + status=completed    │
   │◀──────────────────────────────│
```

### 5.3 Streaming Mode

**Characteristics:**
- Real-time incremental updates
- Server-Sent Events (SSE) or WebSocket
- Best for chat interfaces
- Shows "thinking" progress

```python
# Streaming with SSE
async for event in client.run_stream(
    agent="chat_agent",
    input=[message]
):
    if event.type == "text_delta":
        print(event.data, end="", flush=True)
    elif event.type == "thought":
        print(f"[Thinking: {event.data}]")
    elif event.type == "tool_call":
        print(f"[Using tool: {event.tool}]")
    elif event.type == "complete":
        break
```

**SSE Event Types:**

| Event Type | Description | Data |
|------------|-------------|------|
| `run_start` | Run initiated | `run_id`, `agent_name` |
| `thought` | Agent reasoning | `content` |
| `tool_call_start` | Tool invocation begins | `tool_name`, `input` |
| `tool_call_end` | Tool invocation ends | `tool_name`, `output` |
| `text_delta` | Incremental text | `content` |
| `message_complete` | Full message done | `message` |
| `run_complete` | Run finished | `status`, `output` |
| `error` | Error occurred | `error` |

**SSE Wire Format:**
```
event: run_start
data: {"run_id": "abc123", "agent_name": "support_agent"}

event: thought
data: {"content": "Analyzing customer request..."}

event: tool_call_start
data: {"tool_name": "crm_lookup", "input": {"phone": "123456789"}}

event: tool_call_end
data: {"tool_name": "crm_lookup", "output": {"customer_id": "C123", "balance": 100}}

event: text_delta
data: {"content": "Здрав"}

event: text_delta
data: {"content": "ствуйте, "}

event: text_delta
data: {"content": "Иван!"}

event: message_complete
data: {"message": {...}}

event: run_complete
data: {"status": "completed"}
```

### 5.4 Await/Resume Pattern

For scenarios requiring external input:

```python
# Server-side agent
@server.agent()
async def human_in_loop_agent(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    # Process initial request
    yield {"thought": "Analyzing request..."}

    # Need human approval
    resume_data = yield Await(
        type="approval",
        message="Customer requests a $500 credit. Approve?",
        options=["approve", "deny", "escalate"]
    )

    if resume_data.choice == "approve":
        yield Message(role="agent", parts=[
            MessagePart(content="Credit approved and applied.")
        ])
    else:
        yield Message(role="agent", parts=[
            MessagePart(content="Credit request was not approved.")
        ])
```

**Resume Flow:**
```
Client                          Server                          Agent
   │                               │                               │
   │  POST /runs                   │                               │
   │──────────────────────────────▶│                               │
   │                               │  Start run                    │
   │                               │──────────────────────────────▶│
   │                               │                               │
   │                               │  Await(approval)              │
   │                               │◀──────────────────────────────│
   │  200 OK (status=awaiting)     │                               │
   │◀──────────────────────────────│                               │
   │                               │                               │
   │  POST /runs/{id} (choice)     │                               │
   │──────────────────────────────▶│                               │
   │                               │  Resume with data             │
   │                               │──────────────────────────────▶│
   │                               │                               │
   │                               │  Complete                     │
   │                               │◀──────────────────────────────│
   │  200 OK (status=completed)    │                               │
   │◀──────────────────────────────│                               │
```

---

## 6. Session Management

### 6.1 Session Lifecycle

```
┌──────────────┐     ┌────────────┐     ┌──────────────┐
│    CREATE    │────▶│   ACTIVE   │────▶│   EXPIRED    │
│  POST /sess  │     │   (runs)   │     │ (timeout/del)│
└──────────────┘     └────────────┘     └──────────────┘
```

### 6.2 Session Data Structure

```json
{
  "session_id": "sess-abc123",
  "created_at": "2025-01-01T10:00:00Z",
  "updated_at": "2025-01-01T10:30:00Z",
  "expires_at": "2025-01-02T10:00:00Z",
  "metadata": {
    "channel": "telegram",
    "user_id": "tg-123456",
    "language": "ru"
  },
  "context": {
    "customer_id": "C12345",
    "customer_name": "Иван Петров",
    "current_intent": "technical_support",
    "identified": true
  },
  "history": [
    {
      "run_id": "run-1",
      "timestamp": "2025-01-01T10:00:00Z",
      "input_summary": "Internet not working",
      "output_summary": "Requested customer ID"
    }
  ]
}
```

### 6.3 Session Management Patterns

#### Pattern 1: Session per Conversation (Telegram)

```python
async def handle_telegram_message(update: Update):
    chat_id = update.message.chat.id

    # Get or create session
    session_id = await get_session_for_chat(chat_id)
    if not session_id:
        session = await acp_client.create_session(
            metadata={"channel": "telegram", "chat_id": chat_id}
        )
        session_id = session.session_id
        await save_session_mapping(chat_id, session_id)

    # Run with session context
    run = await acp_client.run_stream(
        agent="support_agent",
        input=[Message(role="user", parts=[
            MessagePart(content=update.message.text)
        ])],
        session_id=session_id
    )
```

#### Pattern 2: Session with Expiration

```python
async def get_or_create_session(user_id: str, ttl_hours: int = 24):
    # Try to get existing session
    session_data = await redis.get(f"session:{user_id}")

    if session_data:
        session = json.loads(session_data)
        # Extend TTL on activity
        await redis.expire(f"session:{user_id}", ttl_hours * 3600)
        return session["session_id"]

    # Create new session
    session = await acp_client.create_session(
        metadata={"user_id": user_id},
        ttl_seconds=ttl_hours * 3600
    )

    await redis.setex(
        f"session:{user_id}",
        ttl_hours * 3600,
        json.dumps({"session_id": session.session_id})
    )

    return session.session_id
```

### 6.4 Session Context Sharing

ACP sessions can carry context that agents access:

```python
@server.agent()
async def context_aware_agent(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    # Access session context
    customer_id = context.session.get("customer_id")

    if customer_id:
        # Customer already identified
        customer_data = await crm_lookup(customer_id)
        yield {"thought": f"Known customer: {customer_data['name']}"}
    else:
        # Need identification
        yield Message(
            role="agent",
            parts=[MessagePart(
                content="Пожалуйста, назовите ваш лицевой счёт."
            )]
        )

    # Update session context
    context.session["last_interaction"] = datetime.now().isoformat()
    context.session["interaction_count"] = context.session.get("interaction_count", 0) + 1
```

---

## 7. Discovery Mechanisms

### 7.1 Registry-Based Discovery

The primary discovery method through the ACP server:

```
GET /agents HTTP/1.1
Host: acp-server.example.com
Authorization: Bearer <token>

Response:
{
  "agents": [
    {
      "name": "technical_support",
      "description": "Handles technical support inquiries",
      "status": "active",
      "version": "1.2.0",
      "capabilities": ["crm_integration", "line_diagnostics"],
      "input_content_types": ["text/plain", "audio/wav"],
      "output_content_types": ["text/plain", "application/json"]
    },
    {
      "name": "billing_agent",
      "description": "Handles billing inquiries",
      "status": "active",
      "version": "1.0.0",
      "capabilities": ["payment_processing", "invoice_generation"],
      "input_content_types": ["text/plain"],
      "output_content_types": ["text/plain", "application/pdf"]
    }
  ],
  "pagination": {
    "total": 5,
    "page": 1,
    "per_page": 10
  }
}
```

### 7.2 Well-Known URL Discovery

Agents can self-describe at standardized endpoints:

```yaml
# GET /.well-known/agent.yaml
name: technical_support
version: 1.2.0
description: AI-powered technical support agent for ISP customers
contact: support@giganet.com

capabilities:
  - crm_integration
  - line_diagnostics
  - ticket_creation
  - balance_inquiry

input_content_types:
  - text/plain
  - text/markdown
  - audio/wav
  - audio/mp3

output_content_types:
  - text/plain
  - application/json

dependencies:
  - name: crm_api
    version: ">=2.0.0"
  - name: oktell_integration
    version: ">=1.5.0"

health_endpoint: /health
metrics_endpoint: /metrics

documentation: https://docs.giganet.com/support-agent
```

### 7.3 Service Mesh Discovery

For Kubernetes environments:

```yaml
# Kubernetes Service with ACP annotations
apiVersion: v1
kind: Service
metadata:
  name: support-agent
  labels:
    acp.io/agent: "true"
  annotations:
    acp.io/name: "technical_support"
    acp.io/version: "1.2.0"
    acp.io/capabilities: "crm,diagnostics,tickets"
    acp.io/input-types: "text/plain,audio/wav"
spec:
  selector:
    app: support-agent
  ports:
    - port: 8000
      targetPort: 8000
```

---

## 8. Security Model

### 8.1 Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Security                      │
│  (Business Logic Validation, Input Sanitization)             │
├─────────────────────────────────────────────────────────────┤
│                    Authorization Layer                       │
│  (Capability Tokens, RBAC, Policy Enforcement)               │
├─────────────────────────────────────────────────────────────┤
│                    Authentication Layer                      │
│  (JWT/Bearer Tokens, mTLS, API Keys)                        │
├─────────────────────────────────────────────────────────────┤
│                    Transport Security                        │
│  (TLS 1.3, Certificate Pinning)                             │
├─────────────────────────────────────────────────────────────┤
│                    Message Integrity                         │
│  (JSON Web Signatures, Content Hashing)                      │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Authentication Methods

#### Bearer Token Authentication

```http
POST /runs HTTP/1.1
Host: acp-server.example.com
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "agent": "support_agent",
  "input": [...]
}
```

#### JWT Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "client-app-123",
    "iss": "acp-auth-server",
    "aud": "acp-server",
    "exp": 1735689600,
    "iat": 1735686000,
    "scope": ["agent:read", "run:create", "session:manage"],
    "client_type": "telegram_bot"
  }
}
```

### 8.3 Capability Tokens

Fine-grained access control through capability tokens:

```json
{
  "capability_token": {
    "id": "cap-abc123",
    "type": "agent_access",
    "resource": "agent/technical_support",
    "operations": ["run:create", "run:read", "run:cancel"],
    "constraints": {
      "rate_limit": "100/minute",
      "max_concurrent_runs": 10,
      "allowed_modes": ["sync", "stream"],
      "ip_whitelist": ["10.0.0.0/8"]
    },
    "issued_at": "2025-01-01T00:00:00Z",
    "expires_at": "2025-02-01T00:00:00Z",
    "signature": "..."
  }
}
```

### 8.4 Message Signing (JWS)

Ensuring message integrity:

```python
from jose import jws

def sign_message(message: dict, private_key: str) -> str:
    payload = json.dumps(message, sort_keys=True)
    return jws.sign(
        payload.encode(),
        private_key,
        algorithm='RS256',
        headers={'kid': 'key-id-123'}
    )

def verify_message(signed_message: str, public_key: str) -> dict:
    payload = jws.verify(signed_message, public_key, algorithms=['RS256'])
    return json.loads(payload)
```

### 8.5 Manifest Signing

Agents sign their manifests for verification:

```yaml
# Signed agent manifest
manifest:
  name: technical_support
  version: 1.2.0
  # ... other fields

signature:
  algorithm: RS256
  key_id: agent-key-001
  value: "base64-encoded-signature"
  timestamp: "2025-01-01T00:00:00Z"
```

### 8.6 Data Privacy Considerations

For handling personal data (relevant to Giganet project):

```python
@server.agent()
async def privacy_aware_agent(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    # Mask PII in logs
    sanitized_input = mask_pii(input[0].parts[0].content)
    logger.info(f"Processing request: {sanitized_input}")

    # Process with full data
    customer_data = await get_customer_data(context.session["customer_id"])

    # Mask PII in stored trajectory
    yield {
        "thought": f"Retrieved customer data for {mask_name(customer_data['name'])}",
        "metadata": {
            "customer_id_hash": hash_pii(customer_data['id'])
        }
    }

    # Response doesn't include full PII
    yield Message(
        role="agent",
        parts=[MessagePart(
            content=f"Здравствуйте, {customer_data['first_name']}! Ваш баланс: {customer_data['balance']} руб."
        )]
    )
```

---

## 9. Protocol Comparisons

### 9.1 ACP vs MCP vs A2A

| Dimension | ACP | MCP | A2A (Google) |
|-----------|-----|-----|--------------|
| **Primary Use Case** | Agent-to-agent communication | LLM-to-tool integration | Enterprise task delegation |
| **Architecture** | Brokered client-server | Direct client-server | Peer-like federation |
| **Protocol Base** | REST/HTTP | JSON-RPC 2.0 | JSON-RPC + REST hybrid |
| **Discovery** | Centralized registry | Manual/static | Agent Cards |
| **Session Support** | Native with run tracking | Stateless + context | Session-aware hybrid |
| **Streaming** | SSE/WebSocket native | Implementation-specific | Native streaming |
| **Message Format** | MIME multipart | JSON-RPC messages | JSON-RPC + artifacts |
| **SDK Required** | No | Yes (preferred) | Yes |
| **Observability** | OpenTelemetry native | Manual | Built-in tracing |
| **Security Model** | Capability tokens + JWT | Implementation-specific | Enterprise IAM |

### 9.2 When to Use Each Protocol

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Protocol Selection Guide                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Need LLM tool integration?                                             │
│    └─▶ MCP (Model Context Protocol)                                     │
│                                                                         │
│  Need agent-to-agent orchestration with central management?             │
│    └─▶ ACP (Agent Communication Protocol)                               │
│                                                                         │
│  Need enterprise multi-org agent federation?                            │
│    └─▶ A2A (Agent-to-Agent / Linux Foundation)                          │
│                                                                         │
│  Need all of the above?                                                 │
│    └─▶ Hybrid: MCP for tools + ACP/A2A for agent orchestration         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Protocol Interoperability

ACP can work alongside other protocols:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Hybrid Architecture                               │
│                                                                         │
│   ┌─────────────┐                      ┌─────────────┐                  │
│   │   Client    │                      │   Client    │                  │
│   │ (Telegram)  │                      │  (Web App)  │                  │
│   └──────┬──────┘                      └──────┬──────┘                  │
│          │                                    │                          │
│          └──────────────┬─────────────────────┘                          │
│                         │                                                │
│                         ▼                                                │
│                ┌─────────────────┐                                       │
│                │   ACP Server    │                                       │
│                │    (Broker)     │                                       │
│                └────────┬────────┘                                       │
│                         │                                                │
│          ┌──────────────┼──────────────┐                                │
│          │              │              │                                │
│          ▼              ▼              ▼                                │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                       │
│   │  Support    │ │  Billing    │ │ Diagnostic  │   ACP Agents          │
│   │   Agent     │ │   Agent     │ │   Agent     │                       │
│   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                       │
│          │              │              │                                │
│          └──────────────┼──────────────┘                                │
│                         │                                                │
│                         ▼                                                │
│                ┌─────────────────┐                                       │
│                │   MCP Server    │                                       │
│                │  (Tool Access)  │                                       │
│                └────────┬────────┘                                       │
│                         │                                                │
│          ┌──────────────┼──────────────┐                                │
│          │              │              │                                │
│          ▼              ▼              ▼                                │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                       │
│   │   CRM API   │ │  Oktell API │ │   Line      │   MCP Tools           │
│   │    Tool     │ │    Tool     │ │ Diagnostic  │                       │
│   └─────────────┘ └─────────────┘ └─────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. SDK Implementation Guide

### 10.1 Python SDK Setup

```bash
pip install acp-sdk
```

### 10.2 Server Implementation

#### Basic Agent Server

```python
import asyncio
from typing import AsyncGenerator
from acp_sdk.models import Message, MessagePart, Await
from acp_sdk.server import Context, RunYield, RunYieldResume, Server

server = Server(
    name="giganet-support-server",
    version="1.0.0"
)

@server.agent(
    name="technical_support",
    description="AI-powered technical support for Giganet customers",
    input_content_types=["text/plain", "audio/wav"],
    output_content_types=["text/plain", "application/json"],
    metadata={
        "capabilities": ["crm_integration", "line_diagnostics", "ticket_creation"],
        "domains": ["technical_support", "isp"],
        "languages": ["ru", "en"]
    }
)
async def technical_support_agent(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Technical support agent for handling customer inquiries.
    """
    user_message = input[-1].parts[0].content

    # Check if customer is identified
    customer_id = context.session.get("customer_id")

    if not customer_id:
        # Attempt to identify customer
        yield {"thought": "Customer not identified, initiating identification flow"}

        # Check if message contains identification info
        identified = await attempt_identification(user_message)

        if identified:
            context.session["customer_id"] = identified["customer_id"]
            context.session["customer_name"] = identified["name"]
            customer_id = identified["customer_id"]
        else:
            yield Message(
                role="agent",
                parts=[MessagePart(
                    content="Здравствуйте! Для того чтобы помочь вам, пожалуйста, назовите ваш лицевой счёт или номер телефона.",
                    content_type="text/plain"
                )]
            )
            return

    # Customer is identified - process request
    yield {"thought": f"Processing request for customer {customer_id}"}

    # Analyze intent
    intent = await analyze_intent(user_message)
    yield {"thought": f"Detected intent: {intent['type']}"}

    if intent["type"] == "balance_inquiry":
        balance = await get_balance(customer_id)
        yield Message(
            role="agent",
            parts=[MessagePart(
                content=f"Ваш текущий баланс: {balance['amount']} руб. {balance['status_message']}",
                content_type="text/plain"
            )]
        )

    elif intent["type"] == "connectivity_issue":
        # Run diagnostics
        yield {"thought": "Running line diagnostics"}
        diagnostics = await run_diagnostics(customer_id)

        if diagnostics["requires_technician"]:
            # Create ticket
            ticket = await create_ticket(
                customer_id=customer_id,
                issue_type="connectivity",
                diagnostics=diagnostics
            )

            yield Message(
                role="agent",
                parts=[MessagePart(
                    content=f"Обнаружена проблема на линии. Создана заявка #{ticket['id']}. "
                           f"Ориентировочное время устранения: {ticket['eta']}. "
                           f"Вам позвонит специалист для уточнения времени визита.",
                    content_type="text/plain"
                )]
            )
        else:
            yield Message(
                role="agent",
                parts=[MessagePart(
                    content=f"Диагностика завершена. {diagnostics['recommendation']}",
                    content_type="text/plain"
                )]
            )

    elif intent["type"] == "operator_request":
        # Escalate to human
        yield {"thought": "Customer requested human operator"}

        resume_data = yield Await(
            type="escalation",
            message="Customer requested human operator",
            data={"customer_id": customer_id, "context": context.session}
        )

        yield Message(
            role="agent",
            parts=[MessagePart(
                content="Переключаю вас на оператора. Пожалуйста, ожидайте.",
                content_type="text/plain"
            )]
        )

    else:
        # General inquiry
        response = await generate_response(user_message, context.session)
        yield Message(
            role="agent",
            parts=[MessagePart(
                content=response,
                content_type="text/plain"
            )]
        )


# Helper functions
async def attempt_identification(message: str) -> dict | None:
    """Attempt to identify customer from message."""
    # Implementation: parse phone numbers, account IDs, etc.
    pass

async def analyze_intent(message: str) -> dict:
    """Analyze user intent from message."""
    # Implementation: intent classification
    pass

async def get_balance(customer_id: str) -> dict:
    """Get customer balance from CRM."""
    # Implementation: CRM API call
    pass

async def run_diagnostics(customer_id: str) -> dict:
    """Run line diagnostics."""
    # Implementation: diagnostic system integration
    pass

async def create_ticket(customer_id: str, issue_type: str, diagnostics: dict) -> dict:
    """Create support ticket."""
    # Implementation: ticket system integration
    pass

async def generate_response(message: str, context: dict) -> str:
    """Generate response using LLM."""
    # Implementation: LLM call
    pass


if __name__ == "__main__":
    server.run(host="0.0.0.0", port=8000)
```

### 10.3 Client Implementation

#### Telegram Bot Integration

```python
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart

# Initialize
bot = Bot(token="YOUR_BOT_TOKEN")
dp = Dispatcher()
acp_client = Client(base_url="http://localhost:8000")

# Session storage (use Redis in production)
sessions: dict[int, str] = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    # Create new ACP session for this chat
    session = await acp_client.create_session(
        metadata={
            "channel": "telegram",
            "chat_id": message.chat.id,
            "user_id": message.from_user.id,
            "username": message.from_user.username
        }
    )
    sessions[message.chat.id] = session.session_id

    await message.answer(
        "Здравствуйте! Я виртуальный помощник технической поддержки Гиганет. "
        "Чем могу помочь?"
    )

@dp.message()
async def message_handler(message: types.Message):
    chat_id = message.chat.id

    # Get or create session
    if chat_id not in sessions:
        session = await acp_client.create_session(
            metadata={"channel": "telegram", "chat_id": chat_id}
        )
        sessions[chat_id] = session.session_id

    session_id = sessions[chat_id]

    # Show typing indicator
    await bot.send_chat_action(chat_id, "typing")

    # Prepare input
    acp_input = [
        Message(
            role="user",
            parts=[MessagePart(
                content=message.text,
                content_type="text/plain"
            )]
        )
    ]

    # Handle voice messages
    if message.voice:
        voice_file = await bot.get_file(message.voice.file_id)
        voice_data = await bot.download_file(voice_file.file_path)

        acp_input = [
            Message(
                role="user",
                parts=[MessagePart(
                    content=voice_data.read(),
                    content_type="audio/ogg",
                    content_encoding="base64"
                )]
            )
        ]

    # Stream response
    response_text = ""
    sent_message = None
    last_update = 0

    async for event in acp_client.run_stream(
        agent="technical_support",
        input=acp_input,
        session_id=session_id
    ):
        if event.type == "text_delta":
            response_text += event.data["content"]

            # Update message every 0.5 seconds for smooth streaming
            now = asyncio.get_event_loop().time()
            if now - last_update > 0.5:
                if sent_message:
                    await sent_message.edit_text(response_text + "▌")
                else:
                    sent_message = await message.answer(response_text + "▌")
                last_update = now

        elif event.type == "run_complete":
            if sent_message:
                await sent_message.edit_text(response_text)
            else:
                await message.answer(response_text)

        elif event.type == "error":
            await message.answer(
                "Извините, произошла ошибка. Пожалуйста, попробуйте позже "
                "или свяжитесь с оператором."
            )

async def main():
    async with acp_client:
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
```

### 10.4 FastAPI Integration

```python
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from acp_sdk.client import Client
from acp_sdk.models import Message, MessagePart
import json

app = FastAPI(title="Giganet Support API")
acp_client = Client(base_url="http://acp-server:8000")

class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    channel: str = "api"

class ChatResponse(BaseModel):
    session_id: str
    response: str
    status: str

@app.on_event("startup")
async def startup():
    await acp_client.__aenter__()

@app.on_event("shutdown")
async def shutdown():
    await acp_client.__aexit__(None, None, None)

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Synchronous chat endpoint."""
    # Get or create session
    if request.session_id:
        session_id = request.session_id
    else:
        session = await acp_client.create_session(
            metadata={"channel": request.channel}
        )
        session_id = session.session_id

    # Run agent
    run = await acp_client.run_sync(
        agent="technical_support",
        input=[Message(
            role="user",
            parts=[MessagePart(content=request.message)]
        )],
        session_id=session_id
    )

    if run.status == "failed":
        raise HTTPException(500, detail=run.error.message)

    response_text = run.output[-1].parts[0].content

    return ChatResponse(
        session_id=session_id,
        response=response_text,
        status=run.status
    )

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint using SSE."""
    # Get or create session
    if request.session_id:
        session_id = request.session_id
    else:
        session = await acp_client.create_session(
            metadata={"channel": request.channel}
        )
        session_id = session.session_id

    async def event_generator():
        yield f"data: {json.dumps({'session_id': session_id})}\n\n"

        async for event in acp_client.run_stream(
            agent="technical_support",
            input=[Message(
                role="user",
                parts=[MessagePart(content=request.message)]
            )],
            session_id=session_id
        ):
            yield f"event: {event.type}\n"
            yield f"data: {json.dumps(event.data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@app.get("/sessions/{session_id}/history")
async def get_history(session_id: str):
    """Get conversation history for a session."""
    session = await acp_client.get_session(session_id)
    if not session:
        raise HTTPException(404, detail="Session not found")

    return {"session_id": session_id, "history": session.history}
```

---

## 11. Migration Strategy

### 11.1 Current Architecture (pi-coding-agent)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      Current Architecture                                │
│                                                                         │
│   ┌─────────────┐          ┌─────────────────────────────────┐          │
│   │   Telegram  │          │         FastAPI Server          │          │
│   │    Client   │─────────▶│                                 │          │
│   └─────────────┘          │  ┌───────────────────────────┐  │          │
│                            │  │    pi-coding-agent        │  │          │
│                            │  │    (subprocess)           │  │          │
│                            │  │                           │  │          │
│                            │  │  stdin  ───▶  JSON-RPC    │  │          │
│                            │  │  stdout ◀───  JSON Events │  │          │
│                            │  │                           │  │          │
│                            │  │  Session: --session-dir   │  │          │
│                            │  └───────────────────────────┘  │          │
│                            │                                 │          │
│                            └─────────────────────────────────┘          │
│                                                                         │
│   Pros:                          Cons:                                  │
│   - Simple implementation        - Non-standard protocol                │
│   - Direct process control       - Tight coupling                       │
│   - Low latency                  - Hard to scale                        │
│                                  - No discovery                         │
│                                  - No multi-agent support               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.2 Target Architecture (ACP)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       Target Architecture                                │
│                                                                         │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────────────────┐   │
│   │   Telegram  │     │   Web App   │     │      Voice API          │   │
│   │    Client   │     │   Client    │     │      (Oktell)           │   │
│   └──────┬──────┘     └──────┬──────┘     └───────────┬─────────────┘   │
│          │                   │                        │                 │
│          └───────────────────┼────────────────────────┘                 │
│                              │                                          │
│                              ▼                                          │
│                 ┌─────────────────────────┐                             │
│                 │      FastAPI Gateway    │                             │
│                 │    (ACP Client Layer)   │                             │
│                 └────────────┬────────────┘                             │
│                              │                                          │
│                              ▼                                          │
│                 ┌─────────────────────────┐                             │
│                 │       ACP Server        │                             │
│                 │   (Agent Registry &     │                             │
│                 │    Request Routing)     │                             │
│                 └────────────┬────────────┘                             │
│                              │                                          │
│          ┌───────────────────┼───────────────────┐                      │
│          │                   │                   │                      │
│          ▼                   ▼                   ▼                      │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐              │
│   │  Technical  │     │   Billing   │     │  Knowledge  │              │
│   │   Support   │     │    Agent    │     │    Agent    │              │
│   │    Agent    │     │             │     │             │              │
│   └─────────────┘     └─────────────┘     └─────────────┘              │
│          │                   │                   │                      │
│          └───────────────────┼───────────────────┘                      │
│                              │                                          │
│                              ▼                                          │
│                 ┌─────────────────────────┐                             │
│                 │    MCP Tool Server      │                             │
│                 │  (CRM, Oktell, Diag)    │                             │
│                 └─────────────────────────┘                             │
│                                                                         │
│   Benefits:                                                             │
│   - Standard protocol           - Multi-agent orchestration            │
│   - Agent discovery             - Horizontal scaling                    │
│   - Session management          - Observability (OpenTelemetry)         │
│   - Security model              - Framework interoperability            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 11.3 Migration Phases

#### Phase 1: Adapter Layer (Weeks 1-2)

Create an adapter that wraps pi-coding-agent in ACP interface:

```python
# acp_pi_adapter.py
from acp_sdk.server import Server, Context, RunYield, RunYieldResume
from acp_sdk.models import Message, MessagePart
import asyncio
import json

server = Server()

class PiAgentAdapter:
    """Adapter to expose pi-coding-agent via ACP protocol."""

    def __init__(self, session_dir: str = "/tmp/sessions"):
        self.session_dir = session_dir
        self.process = None

    async def start(self):
        self.process = await asyncio.create_subprocess_exec(
            "pi", "--mode", "rpc", "--session-dir", self.session_dir,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def send_command(self, command: dict) -> AsyncGenerator[dict, None]:
        self.process.stdin.write(json.dumps(command).encode() + b"\n")
        await self.process.stdin.drain()

        async for line in self.process.stdout:
            event = json.loads(line.decode())
            yield event
            if event.get("type") == "agent_end":
                break

    async def prompt(self, message: str, session_id: str = None):
        if session_id:
            await self._switch_session(session_id)

        async for event in self.send_command({
            "type": "prompt",
            "message": message
        }):
            yield event

    async def _switch_session(self, session_id: str):
        async for _ in self.send_command({
            "type": "switch_session",
            "sessionFile": f"{self.session_dir}/{session_id}.json"
        }):
            pass

# Global adapter instance
adapter = PiAgentAdapter()

@server.agent(
    name="pi_agent_wrapped",
    description="pi-coding-agent exposed via ACP"
)
async def pi_agent_acp(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """ACP wrapper for pi-coding-agent."""

    user_message = input[-1].parts[0].content
    session_id = context.session_id

    response_text = ""

    async for event in adapter.prompt(user_message, session_id):
        if event["type"] == "message_update":
            delta = event.get("text_delta", "")
            response_text += delta
            yield {"text_delta": delta}

        elif event["type"] == "agent_end":
            yield Message(
                role="agent",
                parts=[MessagePart(content=response_text)]
            )

@server.on_startup
async def startup():
    await adapter.start()

if __name__ == "__main__":
    server.run()
```

#### Phase 2: Parallel Running (Weeks 3-4)

Run both systems in parallel with traffic splitting:

```python
# traffic_splitter.py
from fastapi import FastAPI, Request
import random

app = FastAPI()

ACP_TRAFFIC_PERCENTAGE = 20  # Start with 20% to ACP

@app.post("/chat")
async def chat(request: Request):
    if random.random() < (ACP_TRAFFIC_PERCENTAGE / 100):
        return await route_to_acp(request)
    else:
        return await route_to_legacy(request)

async def route_to_acp(request: Request):
    # Route to ACP server
    pass

async def route_to_legacy(request: Request):
    # Route to existing pi-agent implementation
    pass
```

#### Phase 3: Native ACP Agents (Weeks 5-8)

Develop native ACP agents with full functionality:

```python
# native_support_agent.py
from acp_sdk.server import Server, Context
from acp_sdk.models import Message, MessagePart
from typing import AsyncGenerator

# Native implementation without pi-agent dependency
@server.agent(name="technical_support_v2")
async def native_support_agent(
    input: list[Message],
    context: Context
) -> AsyncGenerator[RunYield, RunYieldResume]:
    """
    Native ACP implementation of technical support agent.
    No longer depends on pi-coding-agent subprocess.
    """
    # Direct integration with:
    # - LLM provider (Anthropic, OpenAI, etc.)
    # - CRM system
    # - Diagnostic tools
    # - Ticket system
    pass
```

#### Phase 4: Full Migration (Weeks 9-12)

Complete migration with legacy deprecation:

```
Week 9:  Increase ACP traffic to 50%
Week 10: Increase ACP traffic to 80%
Week 11: Increase ACP traffic to 100%
Week 12: Deprecate legacy system, documentation, monitoring setup
```

### 11.4 Rollback Plan

```python
# Feature flags for quick rollback
class FeatureFlags:
    USE_ACP = os.getenv("USE_ACP", "true").lower() == "true"
    ACP_PERCENTAGE = int(os.getenv("ACP_PERCENTAGE", "100"))
    LEGACY_FALLBACK = os.getenv("LEGACY_FALLBACK", "true").lower() == "true"

async def handle_request(request):
    if not FeatureFlags.USE_ACP:
        return await legacy_handler(request)

    try:
        return await acp_handler(request)
    except Exception as e:
        if FeatureFlags.LEGACY_FALLBACK:
            logger.warning(f"ACP failed, falling back to legacy: {e}")
            return await legacy_handler(request)
        raise
```

---

## 12. Implementation Roadmap

### 12.1 Short-term (1-2 months)

| Week | Task | Deliverable |
|------|------|-------------|
| 1-2 | Set up ACP development environment | Working ACP server locally |
| 2-3 | Create pi-agent adapter | ACP-wrapped pi-agent |
| 3-4 | Implement session mapping | Sessions work with both systems |
| 4 | Deploy to staging | Staging environment with ACP |

### 12.2 Medium-term (3-4 months)

| Week | Task | Deliverable |
|------|------|-------------|
| 5-6 | Develop native support agent | ACP-native agent v1 |
| 6-7 | CRM/Oktell MCP integration | Tool server for external APIs |
| 7-8 | Implement billing agent | Separate billing functionality |
| 8-9 | Security implementation | JWT auth, capability tokens |
| 9-10 | Observability setup | OpenTelemetry, dashboards |
| 10-12 | Gradual rollout | 100% traffic on ACP |

### 12.3 Long-term (6+ months)

| Phase | Task | Impact |
|-------|------|--------|
| Q2 | Multi-agent orchestration | Complex request handling |
| Q2 | Voice integration | Oktell deep integration |
| Q3 | Knowledge agent | Self-updating knowledge base |
| Q3 | Proactive support | Outbound notifications |
| Q4 | Analytics agent | Trend analysis, predictions |

---

## 13. References and Resources

### Official Documentation

- [ACP Official Documentation](https://agentcommunicationprotocol.dev/)
- [ACP GitHub Repository](https://github.com/i-am-bee/acp)
- [OpenAPI Specification](https://github.com/i-am-bee/acp/blob/main/docs/spec/openapi.yaml)

### SDKs and Libraries

- [Python SDK (PyPI)](https://pypi.org/project/acp-sdk/)
- [TypeScript SDK (npm)](https://www.npmjs.com/package/acp-sdk)

### Technical Articles

- [IBM Think: Agent Communication Protocol](https://www.ibm.com/think/topics/agent-communication-protocol)
- [WorkOS Technical Overview](https://workos.com/blog/ibm-agent-communication-protocol-acp)
- [Academic Survey on Agent Protocols](https://arxiv.org/html/2505.02279v1)

### Related Protocols

- [MCP (Model Context Protocol)](https://modelcontextprotocol.io/)
- [A2A (Agent-to-Agent) - Linux Foundation](https://www.linuxfoundation.org/projects/a2a)
- [Google A2A Specification](https://github.com/google/a2a-spec)

### Project-Specific Resources

- [pi-coding-agent Documentation](https://github.com/mariozechner/pi-coding-agent)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Aiogram 3 Documentation](https://docs.aiogram.dev/)
- [Oktell API Documentation](https://oktell.ru/docs)

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **ACP** | Agent Communication Protocol - REST-based protocol for agent interoperability |
| **Run** | A single execution of an agent task |
| **Session** | A stateful conversation context spanning multiple runs |
| **Manifest** | Self-describing metadata published by an agent |
| **Capability Token** | Fine-grained access control token with specific permissions |
| **MCP** | Model Context Protocol - Protocol for LLM-to-tool integration |
| **A2A** | Agent-to-Agent - Unified protocol under Linux Foundation |
| **Broker** | Central server that manages agent registry and request routing |
| **SSE** | Server-Sent Events - HTTP-based streaming protocol |

---

## Appendix B: Checklist for ACP Adoption

### Pre-Implementation

- [ ] Review current architecture documentation
- [ ] Identify all integration points (CRM, Oktell, etc.)
- [ ] Define session management requirements
- [ ] Establish security requirements
- [ ] Set up development environment

### Implementation

- [ ] Install ACP SDK
- [ ] Create adapter for existing agents
- [ ] Implement session mapping layer
- [ ] Set up ACP server
- [ ] Implement authentication
- [ ] Configure monitoring/logging

### Testing

- [ ] Unit tests for agents
- [ ] Integration tests with external systems
- [ ] Load testing
- [ ] Security testing
- [ ] Failover testing

### Deployment

- [ ] Staging deployment
- [ ] Gradual traffic migration
- [ ] Monitoring setup
- [ ] Documentation update
- [ ] Team training

### Post-Deployment

- [ ] Monitor error rates
- [ ] Track latency metrics
- [ ] Gather user feedback
- [ ] Iterate on agent improvements
- [ ] Plan next phase features

---

*Document Version: 1.0*
*Last Updated: 2025*
*Author: Technical Support AI Team*
