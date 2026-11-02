package org.example.client.ui

import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import org.example.client.data.network.NetworkError
import org.example.client.data.network.dto.MessageDto
import org.example.client.data.network.dto.MessageRole
import kotlin.time.Instant

data class SessionUiState(
    val title: String = "",
    val messages: List<MessageUi> = emptyList(),
    val isLoadingDetails: Boolean = false,
    val errorMessage: String? = null,
    val recordingStatus: RecordingStatus = RecordingStatus.Idle,
    val activeSessionId: String? = null,
    val isSessionEnded: Boolean = false,
    val isEndingSession: Boolean = false,
)

enum class RecordingStatus {
    Idle,
    Capturing,
    Uploading,
}

data class MessageUi(
    val id: String,
    val role: MessageRole,
    val content: String,
    val timestamp: String,
)

// TODO(mapping): toMessageUi() is a DTO→UI mapping function living inside the UI-state file.
//  "Files are promises" — this file claims to define state, but it also owns mapping logic. If more
//  mappings appear (session→UI, errors→messages), this file bloats. Fix when improving: extract
//  mapping into a dedicated mapper (or each DTO's own toUi()). Kept here for now for brevity.
fun MessageDto.toMessageUi(): MessageUi = MessageUi(
    id = id,
    role = role,
    content = content,
    timestamp = createdAt.toTimeHhMm(),
)

fun String.toTimeHhMm(): String {
    val time = Instant.parse(this).toLocalDateTime(TimeZone.currentSystemDefault()).time
    val hour = time.hour.toString().padStart(2, '0')
    val minute = time.minute.toString().padStart(2, '0')
    return "$hour:$minute"
}

fun NetworkError.toErrorMessage(): String = when (this) {
    is NetworkError.HttpError -> "Request failed (HTTP ${statusCode})"
    is NetworkError.NetworkFailure -> "Could not connect to the server"
}
