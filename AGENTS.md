# Resonance

Monorepo with `backend/` (Python FastAPI) and `client/` (Kotlin Multiplatform / Compose).

## Backend (`backend/`)

- **Entrypoint**: `backend/main.py` — run with `uvicorn main:app --reload` from `backend/`
- **Config**: `config.py` uses `pydantic-settings` — create `backend/.env` from `.env.example` with `OPENROUTER_API_KEY`
- **Endpoints**: `POST /create_entry` accepts form fields `song_name`, `artist_name` + file `description_file`
- **Architecture**:
  - Uploaded audio saved to temp file, deleted in `finally`
  - `stt.py` → whisper "base" model → raw text → `stt_cleanup.py` → OpenRouter `openrouter/free` for cleanup
  - On OpenRouter `401`, returns raw text with log warning
- **Validation**: Only `.wav`/`.mp3` allowed (checked by MIME type); empty files rejected
- **Testing**: No test framework configured — use `curl` or `test_main.http` (JetBrains HTTP client)

## Client (`client/`)

- Kotlin Multiplatform with Compose — targets Android (`androidApp`) and Desktop JVM (`desktopApp`)
- Shared code in `client/shared/src/commonMain/`
- **Desktop hot reload**: `./gradlew :desktopApp:hotRun --auto` from `client/`
- **Desktop run**: `./gradlew :desktopApp:run`
- **Android build**: `./gradlew :androidApp:assembleDebug`
- **Tests**: `./gradlew :shared:jvmTest` (Desktop), `./gradlew :shared:testAndroidHostTest` (Android)
- Requires JDK 17+ and Android SDK for Android builds

## Who I am
I'm a student developer who wants to genuinely understand my codebase.
I care about learning, not just shipping.

## How to help me
- Never write code without explaining what it does and why
- If I'm about to do something architecturally bad, stop me and explain why
- Ask me questions before jumping to solutions
- If there's something worth learning in what we're doing, teach it
- Keep me aware of every change made to the project and why

## What NOT to do
- Don't write large chunks of code without walking me through the logic first
- Don't make architectural decisions without my input
- Don't let me lose my mental model of the codebase
- Don't just fix things silently — always explain what was wrong