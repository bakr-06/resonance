# Resonance

A voice journaling app. Users record voice notes in journaling sessions;
each recording is transcribed and analyzed by AI for reflection and mood.

## Language

**Session**:
A bounded journaling session containing one or more exchanges.
Sessions are created implicitly when journaling begins and ended
explicitly by the user or via a 10-hour inactivity timeout.
_Avoid_: Conversation, block, recording-session

**Exchange**:
A single voice recording within a session. Each exchange is
transcribed (Whisper) and analyzed (LLM) for reflection and
detected mode. An exchange cannot exist outside a session.
_Avoid_: Entry, recording, note, voice-note

**Reflection**:
The AI-generated thoughtful response to an exchange's transcript.
_Avoid_: Analysis, feedback, comment

**Detected Mode**:
The emotional/intentional mode classified by the AI analysis:
`venting`, `clarity`, or `heard`.
_Avoid_: Mood, category, type, classification
