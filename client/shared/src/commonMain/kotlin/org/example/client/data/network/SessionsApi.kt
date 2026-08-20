package org.example.client.data.network

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.get
import org.example.client.data.network.dto.SessionDto

class SessionsApi(
    private val httpClient: HttpClient,
    private val baseUrl: String,
) {
    suspend fun getSessions(): List<SessionDto> =
        httpClient.get("$baseUrl/sessions").body()

    suspend fun getSession(sessionId: String): SessionDto =
        httpClient.get("$baseUrl/sessions/$sessionId").body()
}