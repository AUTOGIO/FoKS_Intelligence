# ARCHITECTURAL CONTRACT — FoKS Intelligence

**Status:** LOCKED — This document defines the canonical architectural boundaries for FoKS Intelligence.
**Last Updated:** 2025-01-27
**Authority:** Principal Systems Engineer — Final System Consolidation

---

## 🎯 SYSTEM ROLE

**FoKS Intelligence** is the **control plane** for system automation.

### Core Responsibilities

1. **Coordination**

   - Coordinates execution across multiple systems
   - Delegates execution to FBP Backend
   - Manages high-level workflow orchestration

2. **Delegation**

   - Routes automation requests to appropriate systems
   - Provides unified interface for external clients
   - Handles integration with LM Studio, macOS, and FBP

3. **Interface Management**

   - Exposes HTTP API for external clients (Shortcuts, n8n, scripts)
   - Manages conversation state for chat interactions
   - Provides task routing and execution delegation

4. **Control Plane Logic**
   - Decision-making about which system to use
   - Error handling and retry coordination
   - State tracking for coordination (NOT execution state)

---

## ✅ MUST (Required Behaviors)

- **MUST** coordinate and delegate execution to FBP
- **MUST** provide unified interface for external clients
- **MUST** manage conversation state and chat interactions
- **MUST** route tasks to appropriate systems (FBP, LM Studio, macOS)
- **MUST** handle coordination-level error recovery
- **MUST** optimize for ARM64-native Python behavior
- **MUST** support async I/O and controlled concurrency

---

## ❌ MUST NOT (Forbidden Patterns)

- **MUST NOT** execute automation directly (delegate to FBP)
- **MUST NOT** own execution state (FBP owns execution state)
- **MUST NOT** implement execution logic (FBP owns execution)
- **MUST NOT** use workflow engines or background job frameworks
- **MUST NOT** implement schedulers or worker pools
- **MUST NOT** store execution state outside coordination boundaries
- **MUST NOT** implement browser automation (delegate to FBP)
- **MUST NOT** own long-running execution processes

---

## 🔗 SYSTEM RELATIONSHIPS

### FoKS ↔ FBP Backend

- **FoKS Role:** Control plane (coordinates and delegates)
- **FBP Role:** Execution authority
- **Interface:** UNIX socket (`/tmp/fbp.sock`) or TCP (configurable)
- **Protocol:** HTTP-like requests with JSON payloads

**Boundary Rules:**

- FoKS **MUST** delegate execution to FBP
- FoKS **MUST NOT** execute automation directly
- FoKS **MUST NOT** own execution state
- FBP **MUST** accept execution requests from FoKS
- FBP **MUST** own all execution state

### FoKS ↔ n8n

- **FoKS Role:** API provider
- **n8n Role:** Scheduling and triggering ONLY
- **Interface:** HTTP endpoints (`/tasks`, `/chat`, etc.)

**Boundary Rules:**

- n8n **MUST** trigger FoKS via HTTP requests
- n8n **MUST NOT** own execution state
- n8n **MUST NOT** implement execution logic
- FoKS **MUST** respond to n8n triggers
- FoKS **MUST** delegate execution to FBP (not execute directly)

### FoKS ↔ LM Studio

- **FoKS Role:** Client and coordinator
- **LM Studio Role:** LLM inference provider
- **Interface:** HTTP (OpenAI-compatible API)

**Boundary Rules:**

- FoKS **MUST** coordinate LLM requests
- FoKS **MUST NOT** execute automation based on LLM output (delegate to FBP)

---

## 🏗️ ARCHITECTURAL LAYERS

### Layer 1: Router (FastAPI)

- HTTP endpoints for external clients
- Request validation and response formatting
- **MUST NOT** contain business logic

### Layer 2: Service (Coordination)

- Coordinates execution across systems
- Delegates to FBP, LM Studio, macOS
- **MUST NOT** execute automation directly
- **MUST NOT** own execution state

### Layer 3: Core (Infrastructure)

- FBP client (delegation interface)
- LM Studio client (LLM coordination)
- Task runner (macOS automation coordination)
- **MUST** provide coordination primitives only

---

## 🔒 HARDWARE & OS CONSTRAINTS

**Target Environment:**

- Model: iMac (Mac15,5)
- Chip: Apple M3 (4P + 4E cores)
- Memory: 16 GB
- OS: macOS 26.0 Beta

**Optimization Requirements:**

- Async I/O (no blocking operations)
- Deterministic coordination (no race conditions)
- Controlled concurrency (no worker pools)
- ARM64-native Python behavior

---

## 📋 ENFORCEMENT

This contract is enforced through:

1. **Documentation:** This contract document
2. **Code Comments:** Guardrails in coordination modules
3. **AI Guardrails:** `.cursor/ARCHITECTURAL_GUARDRAILS.md`

**Violations of this contract are architectural bugs, not features.**

---

## 🔄 EVOLUTION

This contract may evolve, but changes **MUST**:

- Preserve control plane boundaries
- Maintain delegation patterns
- Respect hardware/OS constraints
- Be approved by Principal Systems Engineer

**Last Review:** 2025-01-27
**Next Review:** As needed (architectural changes)
