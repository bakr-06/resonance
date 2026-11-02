# Pass the User Profile as System Context

## Context

ADR 0003 added `resonance_user` and gave every session an owner, explicitly so that user data could be injected into LLM calls. The profile already stores `name`, `social_status`, and `date_of_birth`, but the analysis path never read it: the system prompt was a static string and the message log held only user and assistant turns.

The profile needed to reach the model without breaking the message model established in ADR 0004.

## Decision

Load the session's user once per recording and append a rendered profile block to the analysis system prompt:

```
About the person you are talking to:
- Name: Bakr
- Age: 20
- Social status: single
```

The model receives name, derived age, occupation, and social status. `age` is computed from `date_of_birth` at request time and never stored, so it cannot go stale. The raw birth date is not sent. If the user row is missing, the recording proceeds with the base prompt and a warning is logged, because a broken ownership row is a data-integrity bug that must not cost the user their entry.

## Considered Options

- **Put the profile in the context window as a pseudo-message**: Rejected — the window is a log of turns. It counts against the 12-message limit, gets turn alignment applied so it cannot start with an orphaned reply, and is lazily reloaded from `message` rows. A profile is none of those things, and it would be duplicated as the window slides.
- **Add a second system message**: Rejected for now — the character budget in `_build_messages` reserves one system prompt, and rendering depends on how Ollama combines multiple system entries. Folding it into the same string keeps accounting correct without touching the drop logic.
- **Store age on the user row**: Rejected — a stored age is wrong one day later.
- **Send the raw date of birth**: Rejected — the model only needs age, and the exact date is more personal data than the task requires.

## Consequences

- The system prompt is assembled per request, so a `PUT /users/{id}` edit takes effect on the next message with no cache invalidation.
- `_build_messages` needs no change: the longer system prompt is reserved inside the existing character budget.
- The message log and context window remain pure conversation; nothing about the profile is persisted per message.
- Session titles stay entry-based and ignore the profile, because a title should describe the session, not the person.
- The profile is a snapshot at request time; editing the user mid-session does not rewrite earlier prompts.
