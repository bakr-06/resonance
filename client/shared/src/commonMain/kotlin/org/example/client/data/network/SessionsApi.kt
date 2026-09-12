package org.example.client.data.network

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.forms.MultiPartFormDataContent
import io.ktor.client.request.forms.append
import io.ktor.client.request.forms.formData
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.http.ContentType
import org.example.client.data.network.dto.ExchangeDto
import org.example.client.data.network.dto.SessionDto
import java.io.File

class SessionsApi(
    private val httpClient: HttpClient,
    private val baseUrl: String,
) {
    suspend fun getSessions(): List<SessionDto> =
        httpClient.get("$baseUrl/sessions").body()

    suspend fun getSession(sessionId: String): SessionDto =
        httpClient.get("$baseUrl/sessions/$sessionId").body()

    suspend fun getActiveSession(): SessionDto? =
        httpClient.get("$baseUrl/sessions/active").body()

    suspend fun createSession(): SessionDto =
        httpClient.post("$baseUrl/sessions").body()

    suspend fun createExchange(sessionId: String, audioFile: File): ExchangeDto {
        val audioBytes = audioFile.readBytes()

        return httpClient.post("$baseUrl/sessions/$sessionId/exchanges") {
            setBody(
                MultiPartFormDataContent(
                    formData {
                        append(
                            key = "file",
                            filename = audioFile.name,
                            contentType = ContentType.parse("audio/wav"),
                        ) {
                            write(audioBytes)
                        }
                    }
                )
            )
        }.body()
    }
}