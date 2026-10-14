package org.example.client.ui

import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import org.example.client.data.network.NetworkError
import org.example.client.data.network.dto.ExchangeDto
import kotlin.time.Instant

data class ExchangeUiState(
    val title: String = "",
    val exchanges: List<ExchangeUi> = emptyList(),
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

data class ExchangeUi(
    val id: String,
    val transcript: String,
    val reflection: String,
    val timestamp: String,
)

// TODO(recording): toExchangeUi() is a DTO→UI mapping function living inside the UI-state file.
//  "Files are promises" — this file claims to define state, but it also owns mapping logic. If more
//  mappings appear (session→UI, errors→messages), this file bloats. Fix when improving: extract
//  mapping into a dedicated mapper (or each DTO's own toUi()). Kept here for now for brevity.
fun ExchangeDto.toExchangeUi(): ExchangeUi = ExchangeUi(
    id = id,
    transcript = transcript,
    reflection = reflection,
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