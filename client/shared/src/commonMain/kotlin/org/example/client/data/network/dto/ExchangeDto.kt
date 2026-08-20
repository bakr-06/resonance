package org.example.client.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class ExchangeDto(
    val id: String,
    @SerialName("session_id") val sessionId: String,
    val transcript: String,
    val reflection: String,
    @SerialName("detected_mode") val detectedMode: String?,
    @SerialName("created_at") val createdAt: String,
)