package org.example.client.exchange.data

import org.example.client.Result
import org.example.client.core.data.NetworkError
import org.example.client.core.data.remote.dto.ExchangeDto
import org.example.client.exchange.data.remote.ExchangeApiDataSource
import org.example.client.exchange.domain.Exchange
import org.example.client.exchange.domain.toDomain
import org.example.client.map

class ExchangeRepository(private val dataSource: ExchangeApiDataSource) {

    suspend fun createExchange(
        sessionId: String,
        fileBytes: ByteArray,
        filename: String,
        mimeType: String,
    ): Result<Exchange, NetworkError> =
        dataSource.createExchange(sessionId, fileBytes, filename, mimeType)
            .map(ExchangeDto::toDomain)

    suspend fun updateExchange(
        sessionId: String,
        exchangeId: String,
        transcript: String,
    ): Result<Exchange, NetworkError> =
        dataSource.updateExchange(sessionId, exchangeId, transcript)
            .map(ExchangeDto::toDomain)
}
