package org.example.client.core.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class ExchangeDto(
    val id: String,
    val session_id: String,
    val transcript: String,
    val reflection: String,
    val detected_mode: String? = null,
    val created_at: String,
    val filename: String = "",
    val content_type: String? = null,
)
