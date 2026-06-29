# From Flat Entries to Sessions and Exchanges

The original domain had a single `Entry` entity — a voice recording that was transcribed and analyzed. As the product
grew beyond isolated recordings toward a journaling workflow, `Entry` no longer captured the idea of a bounded
journaling session containing multiple related recordings. We introduced `Session` as a container and renamed `Entry` to
`Exchange` to reflect that each recording is one turn in a conversation with oneself.

## Considered Options

- **Keep a single `Entry` model, add an optional `session_id` column.** This would avoid renaming but would leave the
  old `Entry` name in place, creating confusion between sessions of entries and individual entries. The rename was worth
  the churn because "exchange" better describes a back-and-forth with the AI reflection.

- **Implicit session creation on first exchange.** We considered having `POST /exchanges` auto-create a session when no
  `session_id` is provided. We rejected this because it conflates two operations — the two-step flow (`POST /sessions`
  then `POST /sessions/{id}/exchanges`) keeps each endpoint responsible for one resource.

- **Define session end purely by `ended_at` (nullable) without `is_active`.** We kept both because `is_active` enables
  efficient querying (indexed boolean filter) without checking `ended_at IS NULL` everywhere. They always align — never
  diverge.

## Consequences

- The background job for 10-hour session timeout needs to be built separately; it isn't covered by any current endpoint
  logic.
- `POST /sessions/{id}/end` calls the LLM synchronously for title regeneration, which means the endpoint blocks for the
  duration of the LLM call (acceptable since ending a session is an infrequent user action).
- Exchanges now fail the entire request on LLM error (unlike the old `Entry` which would return raw text), which is a
  breaking API change — clients must now handle 5xx on exchange creation.
- The cascade-delete behavior means losing a session accidentally loses all its exchanges; there is no soft-delete or
  recovery mechanism in this version.
