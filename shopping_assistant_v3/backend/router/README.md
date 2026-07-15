# router

Job orchestration and controlled intent routing. Classifies the Vietnamese user
message, produces a normalized English query, and invokes tools in a fixed
order. No free-form ReAct loop.

MVP executes only `search_deals`. Other intents return safe Vietnamese
fallback. Contract: `shopping_assistant_v3/guides/agent_architecture.md`.

Implemented in Phase 5 (orchestration skeleton may arrive in Phase 3). No code
yet.
