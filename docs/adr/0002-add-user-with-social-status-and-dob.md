# Add User with Social Status and Date of Birth

## Context

The application needs to track user information with social status and date of birth. All existing data in the database is dummy/test data and should be removed. Date of birth requires validation to ensure only past dates are accepted. No minimum age restriction is required.

## Decision

We add a new `User` entity to the backend with the following fields:
- `social_status`: Enum with values `single` and `married` (stored as PostgreSQL enum)
- `date_of_birth`: Date stored in PostgreSQL, validated to be in the past
- Timestamps for audit trail (`created_at`, `updated_at`)

Validation is enforced at both the database model level and the Pydantic schema level. Pydantic schemas validate that `date_of_birth` is strictly before the current date. The database schema enforces non-null constraints.

As part of this migration, we truncate all existing dummy data from `analysis_metrics`, `transcription_metrics`, `exchange`, and `session` tables using `TRUNCATE ... CASCADE` to remove all orphaned data.

User management endpoints are added to allow creating, reading, updating, and deleting users. The token/OAuth URL configuration remains at defaults as specified.

## Considered Options

- **Store DOB as string vs Date type**: We chose the native `Date` type for proper validation and type safety. String would require manual parsing and validation.
- **Enum storage**: Using PostgreSQL enum type ensures data integrity at the database level.
- **Validation location**: Validating in both Pydantic schemas (API layer) and having proper types in the model provides defense in depth.
- **Data cleanup approach**: Truncating all tables is appropriate since all data is dummy/test data as stated.

## Consequences

- A new `user` table is created in the database
- All existing session and exchange data is deleted as part of the migration
- API consumers can now manage users via `/users` endpoints
- DOB validation rejects current or future dates at the API level
- The schema now includes a new enum type `socialstatus`
