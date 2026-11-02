# Store Messages Instead of Exchanges

## Context

The `exchange` table forced one row per recording to hold both the transcript and the AI reply, plus a nullable `detected_mode`. That shape cannot express the real conversation order, pretends a reply always exists, and welds a model output to a dedicated column.

## Decision

Replace `exchange` with `message(id, session_id, role, content, created_at)`, where `role` is `user` or `assistant`. ADR 0003's ownership chain `User -> Session -> Exchange` therefore becomes `User -> Session -> Message`. A recording always stores the user message (committed before analysis, so a timeout cannot lose it); the assistant message is stored only when the model returns non-empty content. `detected_mode` is retired, and the metric tables now reference `message.id`. Existing sessions and exchanges were discarded by the migration because they were development data.

## Considered Options

- **Keep `exchange` and add a second table for messages**: Rejected — two sources of truth for the same conversation.
- **One JSON `content` column holding both sides**: Rejected — roles stop being queryable and indexable.
- **Use `user` / `system` as the two roles**: Rejected — `system` is reserved for the LLM instruction prompt, which is not part of the session log.

## Consequences

- The LLM receives real role-tagged history (system prompt, then the last 12 messages, then the current recording) instead of flattened "Earlier entry N" text.
- An unanswered user message is valid history and is kept in the context window.
- The API and client vocabulary is `/messages` end to end; the unused edit endpoint is gone.
- Historical exchange data cannot be recovered after the migration.
