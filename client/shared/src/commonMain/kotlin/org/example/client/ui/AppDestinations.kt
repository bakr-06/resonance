package org.example.client.ui

import kotlinx.serialization.Serializable

@Serializable
data object SessionDestination

@Serializable
data class SessionSummaryDestination(
    val sessionId: String,
)