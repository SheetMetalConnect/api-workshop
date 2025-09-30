
# Use Case Definition

## My Use Case

**The Core Idea:** Investigate how to build an API layer over the UMH (United Manufacturing Hub) I created for a metalworking factory. This API layer would speed up implementation and eliminate the need for custom coded dataflows in UMH for every new feature. Instead, I define clear API endpoints for business operations \- query orderdata, query operations, query OEE, replanning, start/stop commands to the UNS. This approach also simplifies MCP/LLM integration \- they can use straightforward API calls instead of complex hardcoded MCP servers.

**Current Architecture:**

* UNS implemented with United Manufacturing Hub
* Read path: Postgres database
* Write path: MQTT/Kafka event stream
* Legacy systems integrated and data flowing
* Existing webapp reads data but can't write
* Currently using custom UMH dataflows for each integration

**Why an API Layer:**

* Replace custom UMH dataflows with standardized endpoints
* Enable write operations for existing webapp
* Provide simple MCP integration for AI/LLM tools
* Create single maintainable codebase instead of scattered integrations
* Define business operations clearly (not raw data access)

**Technical Challenges:**

* Supporting both REST (webapp) and MCP (AI) protocols efficiently
* Translating synchronous API calls to async MQTT/Kafka operations
* Maintaining performance when API becomes the bottleneck
* Abstracting UMH complexity without losing functionality

## Questions to Explore

* How to structure one API that serves both REST and MCP protocols efficiently?

  * Do I need separate routers or can they share business logic?
  * How to handle different response formats for same data?
* Where should business logic live when writes go through MQTT but reads come from Postgres?

  * Validation rules before publishing to MQTT
  * Ensuring consistency between command and query sides
* How to handle async operations (publish to MQTT, wait for confirmation) in sync API calls?

  * When webapp sends "start machine" command, it expects immediate response
  * But MQTT publish is fire-and-forget, actual confirmation comes later via Kafka
  * Do I return "accepted" immediately or wait for confirmation?
  * How long to wait before timing out?
* What's the best pattern for correlation IDs when tracking commands through the event system?

  * Need to match the response from Kafka to original API request
  * Where to store correlation IDs while waiting?
* **Should MCP tools map directly to MQTT topics or go through abstraction layer?** \[KEY COURSE TOPIC\]

  * Direct mapping: AI tool "start\_machine" → publishes to "factory/machine/start"
    * Pros: Simple, transparent, direct control
    * Cons: MQTT topics hardcoded in MCP server, any topic restructuring breaks AI tools
  * Abstracted through API: AI calls "execute\_command" → API handles MQTT complexity
    * Pros: API server maintains topic mappings, can reorganize MQTT without touching MCP
    * Cons: Another layer to maintain, but gives flexibility
  * This abstraction is probably why the course exists \- API as the smart translation layer
* How to provide the right context depth (AI needs rich context, webapp needs fast response)?

  * Same endpoint serving different consumers with different needs
  * Caching strategies, optional parameters, or separate endpoints?

## Things to Research

* What did UMH team do for their API approach to UNS?
* FastAPI patterns for mixed authentication (webapp sessions vs AI tokens vs API keys)
* When to use WebSocket (real-time updates) vs REST (queries) vs webhooks (external events)?
* Caching strategies for frequently accessed factory data without losing real-time accuracy
* How to implement MCP tools that trigger MQTT publishes
* Best practices for correlation IDs in event-driven architectures
* Rate limiting strategies that differ by consumer type (generous for webapp, strict for AI)

## Course Expectations

**Want to understand:**

* How to design one API that handles multiple protocols (REST, MCP, WebSockets)
* Patterns for read/write split (query Postgres, command via MQTT)
* How to implement MCP alongside existing REST endpoints in FastAPI
* Handling async event-driven operations in synchronous API calls
* Best practices for abstracting business logic from data structure
* Performance optimization when API serves as the single access point
* How to evolve the API as new consumers are added over time

## Why Not Direct Integration?

**Could skip the API and connect directly:**

* MCP server → Postgres for reads
* MCP server → Kafka for writes
* Webapp → Postgres directly

**But this creates problems:**

* Business logic (validation, constraints) has nowhere to live consistently
* Each consumer needs to understand the data schema and relationships
* Protocol mismatches (MCP expects sync responses, Kafka is async)
* Security becomes distributed across multiple connection points
* Changes to business rules require updates in multiple places
* No central place for caching, rate limiting, or monitoring

**The API provides:**

* Single place for business logic and validation
* Protocol translation (REST↔MCP↔MQTT)
* Centralized security and access control
* Abstraction from underlying data structure

-
