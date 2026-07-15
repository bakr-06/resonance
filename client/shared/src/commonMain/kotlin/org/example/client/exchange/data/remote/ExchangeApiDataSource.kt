package org.example.client.exchange.data.remote

import io.ktor.client.*
import io.ktor.client.call.*
import io.ktor.client.request.*
import io.ktor.client.request.forms.*
import io.ktor.client.statement.*
import io.ktor.http.*
import org.example.client.Result
import org.example.client.core.data.NetworkError
import org.example.client.core.data.remote.dto.ExchangeDto
import java.net.ConnectException
import java.util.concurrent.TimeoutException

class ExchangeApiDataSource(private val httpClient: HttpClient) {

    suspend fun createExchange(
        sessionId: String,
        fileBytes: ByteArray,
        filename: String,
        mimeType: String,
    ): Result<ExchangeDto, NetworkError> = executeRequest {
        httpClient.submitFormWithBinaryData(
            url = "/sessions/$sessionId/exchanges",
            formData = formData {
                append("file", fileBytes, headers = Headers.build {
                    append(HttpHeaders.ContentType, mimeType)
                    append(HttpHeaders.ContentDisposition, "filename=\"$filename\"")
                })
            })
    }

    suspend fun updateExchange(
        sessionId: String,
        exchangeId: String,
        transcript: String,
    ): Result<ExchangeDto, NetworkError> = executeRequest {
        httpClient.put("/sessions/$sessionId/exchanges/$exchangeId") {
            contentType(ContentType.Application.Json)
            setBody(mapOf("transcript" to transcript))
        }
    }

    private suspend inline fun <reified T> executeRequest(
        block: suspend () -> HttpResponse,
    ): Result<T, NetworkError> {
        return try {
            val response = block()
            when (response.status) {
                HttpStatusCode.OK, HttpStatusCode.Created -> {
                    Result.Success(response.body())
                }

                HttpStatusCode.NotFound -> Result.Error(NetworkError.NotFound)
                else -> Result.Error(
                    NetworkError.ServerError(
                        code = response.status.value,
                        message = response.bodyAsText(),
                    )
                )
            }
        } catch (_: ConnectException) {
            Result.Error(NetworkError.NoInternet)
        } catch (_: TimeoutException) {
            Result.Error(NetworkError.Timeout)
        } catch (e: Exception) {
            Result.Error(NetworkError.Unknown(e))
        }
    }
}
