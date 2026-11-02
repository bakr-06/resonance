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
import io.ktor.http.contentType
import org.example.client.data.network.dto.CreateMessagesDto
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
        httpClient.post("$baseUrl/sessions") {
            contentType(ContentType.Application.Json)
            setBody(mapOf("user_id" to "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))
        }.body()

    suspend fun endSession(sessionId: String): SessionDto =
        httpClient.post("$baseUrl/sessions/$sessionId/end").body()

    suspend fun createMessages(sessionId: String, audioFile: File): CreateMessagesDto {
        val audioBytes = audioFile.readBytes()

        return httpClient.post("$baseUrl/sessions/$sessionId/messages") {
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