package org.example.client.core.data.remote.dto

import kotlinx.serialization.Serializable

@Serializable
data class SessionDto(
    val id: String,
    val title: String? = null,
    val createdAt: String,
    val endedAt: String? = null,
    val isActive: Boolean,
    val exchanges: List<ExchangeDto> = emptyList(),
)
