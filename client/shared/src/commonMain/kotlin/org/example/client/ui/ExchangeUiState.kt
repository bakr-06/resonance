package org.example.client.ui

import kotlinx.datetime.TimeZone
import kotlinx.datetime.toLocalDateTime
import org.example.client.data.network.NetworkError
import org.example.client.data.network.dto.ExchangeDto
import kotlin.time.Instant

data class ExchangeUiState(
    val exchanges: List<ExchangeUi> = emptyList(),
    val isLoadingDetails: Boolean = false,
    val errorMessage: String? = null,
)

data class ExchangeUi(
    val id: String,
    val transcript: String,
    val reflection: String,
    val timestamp: String,
)

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
    is NetworkError.HttpError -> "Failed to load sessions (HTTP ${statusCode})"
    is NetworkError.NetworkFailure -> "Could not connect to the server"
}