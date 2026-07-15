package org.example.client.core.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class SessionDto(
    val id: String,
    val title: String? = null,
    val created_at: String,
    val ended_at: String? = null,
    val is_active: Boolean,
    val exchanges: List<ExchangeDto> = emptyList(),
)
