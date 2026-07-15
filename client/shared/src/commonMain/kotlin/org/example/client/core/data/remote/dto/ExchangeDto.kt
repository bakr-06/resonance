package org.example.client.core.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class ExchangeDto(
    val id: String,
    val sessionId: String,
    val transcript: String,
    val reflection: String,
    val detectedMode: String? = null,
    val createdAt: String,
    val filename: String = "",
    val contentType: String? = null,
)
