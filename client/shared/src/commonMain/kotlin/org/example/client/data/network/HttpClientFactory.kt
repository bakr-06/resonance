package org.example.client.data.network

import io.ktor.client.HttpClient
import io.ktor.client.engine.HttpClientEngine
import io.ktor.client.plugins.HttpTimeout
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

internal expect fun createHttpClientEngine(): HttpClientEngine

internal fun createHttpClient(): HttpClient =
    HttpClient(createHttpClientEngine()) {
        expectSuccess = true
        install(ContentNegotiation) {
            json(Json { ignoreUnknownKeys = true })
        }
        // TODO(recording): 60s request timeout is applied globally to every request this client makes.
        //  It exists for the exchange upload (Whisper + LLM can be slow), but it also caps trivial calls
        //  like getSessions. If slow endpoints grow, move toward per-request or endpoint-specific timeouts
        //  rather than one blanket value. Revisit when the network layer gets more endpoints.
        install(HttpTimeout) {
            requestTimeoutMillis = 60_000
        }
    }