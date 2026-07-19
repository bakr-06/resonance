package org.example.client.exchange.domain

import org.example.client.core.data.remote.dto.ExchangeDto

data class Exchange(
    val id: String,
    val transcript: String,
    val reflection: String,
    val detectedMode: String?,
    val createdAt: String,
)

fun ExchangeDto.toDomain(): Exchange = Exchange(
    id = id,
    transcript = transcript,
    reflection = reflection,
    detectedMode = detectedMode,
    createdAt = createdAt,
)
