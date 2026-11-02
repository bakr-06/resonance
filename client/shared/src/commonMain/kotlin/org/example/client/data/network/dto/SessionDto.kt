package org.example.client.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class SessionDto(
    val id: String,
    @SerialName("user_id") val userId: String,
    val title: String?,
    @SerialName("created_at") val createdAt: String,
    @SerialName("ended_at") val endedAt: String? = null,
    @SerialName("is_active") val isActive: Boolean,
    val messages: List<MessageDto> = emptyList(),
)
