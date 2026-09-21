package org.example.client.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SessionDto(
    val id: String,
    val title: String?,
    @SerialName("created_at") val createdAt: String,
    @SerialName("ended_at") val endedAt: String? =  null,
    @SerialName("is_active") val isActive: Boolean,
     wq
    val exchanges: List<ExchangeDto> = emptyList(),
)