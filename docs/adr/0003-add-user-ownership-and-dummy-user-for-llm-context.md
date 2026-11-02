# Add User Ownership and Dummy User for LLM Context

## Context

Sessions and exchanges need to be owned by a user. Also, we need to be able to inject user data (like social status, date of birth) into the context of LLM calls for testing purposes while building the app without a full authentication system.

## Decision

We add a foreign key relationship: `User` -> `Session` -> `Exchange`. A session must belong to a user (user_id is required). The backend requires `user_id` when creating sessions and validates the user exists.

For development/testing purposes while auth is not implemented, we create a dummy user:
- Name: Bakr
- Date of Birth: 2006-03-09
- Social Status: single
- ID: `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa` (hardcoded)

The client hardcodes this user ID in all session creation calls. This allows us to inject user context into LLM calls for experimentation and development.

All orphaned data (sessions without users) was deleted during the migration. The dummy user and ownership model will be replaced with proper authentication later.

## Considered Options

- **Make user_id nullable**: Rejected because ownership should be enforced.
- **Store user in session differently**: Foreign key is clean and allows proper relationships.
- **Pass user_id through headers vs body**: Body is simpler for now without auth middleware.

## Consequences

- Session creation now requires a valid user_id
- All sessions must be associated with a user
- Client is temporarily coupled to a hardcoded test user ID
- Database schema enforces referential integrity between users and sessions
- User context can be accessed for future LLM prompt injection
- This is a temporary development setup that needs to be replaced with proper auth
