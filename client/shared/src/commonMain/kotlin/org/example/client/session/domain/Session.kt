package org.example.client.session.domain

import org.example.client.core.data.remote.dto.SessionDto
import org.example.client.exchange.domain.Exchange
import org.example.client.exchange.domain.toDomain

data class Session(
    val id: String,
    val title: String? = null,
    val createdAt: String,
    val endedAt: String? = null,
    val isActive: Boolean,
    val exchanges: List<Exchange> = emptyList(),
)

fun SessionDto.toDomain(): Session = Session(
    id = id,
    title = title,
    createdAt = createdAt,
    endedAt = endedAt,
    isActive = isActive,
    exchanges = exchanges.map { it.toDomain() },
)
