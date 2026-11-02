# Resonance

A voice journaling app. Users record voice notes in journaling sessions;
each recording is transcribed and kept as a message alongside the AI's
replies.

## Language

**Session**:
A bounded journaling conversation made of messages. Sessions are created
implicitly when journaling begins and ended explicitly by the user or via a
10-hour inactivity timeout.
_Avoid_: Conversation, block, recording-session

**Message**:
One entry in a session's log: either a recorded voice note after
transcription or the AI's reply. Messages are ordered by time and never
change role. An unanswered user message is still a complete message.
_Avoid_: Exchange, entry, turn, recording, note, voice-note

**Role**:
Who produced a message: `user` for recorded voice notes, `assistant` for AI
replies. A role never changes after a message is stored.
_Avoid_: Speaker, author, type, sender
