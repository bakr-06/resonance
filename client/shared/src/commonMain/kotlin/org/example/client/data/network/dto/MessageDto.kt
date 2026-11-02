package org.example.client.data.network.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class MessageRole {
    @SerialName("user") User,
    @SerialName("assistant") Assistant,
}

@Serializable
data class MessageDto(
    val id: String,
    @SerialName("session_id") val sessionId: String,
    val role: MessageRole,
    val content: String,
    @SerialName("created_at") val createdAt: String,
)

@Serializable
data class CreateMessagesDto(
    val messages: List<MessageDto>,
)
