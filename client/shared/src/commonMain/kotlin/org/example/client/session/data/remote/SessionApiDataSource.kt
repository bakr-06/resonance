package org.example.client.session.data.remote

import io.ktor.client.HttpClient
import io.ktor.client.call.body
import io.ktor.client.request.delete
import io.ktor.client.request.get
import io.ktor.client.request.post
import io.ktor.client.statement.HttpResponse
import io.ktor.client.statement.bodyAsText
import io.ktor.http.HttpStatusCode
import org.example.client.Result
import org.example.client.core.data.NetworkError
import org.example.client.core.data.remote.dto.SessionDto
import java.net.ConnectException
import java.util.concurrent.TimeoutException

class SessionApiDataSource(private val httpClient: HttpClient) {

    suspend fun createSession(): Result<SessionDto, NetworkError> =
        executeRequest { httpClient.post("/sessions") }

    suspend fun getSessions(): Result<List<SessionDto>, NetworkError> =
        executeRequest { httpClient.get("/sessions") }

    suspend fun getSession(id: String): Result<SessionDto, NetworkError> =
        executeRequest { httpClient.get("/sessions/$id") }

    suspend fun endSession(id: String): Result<SessionDto, NetworkError> =
        executeRequest { httpClient.post("/sessions/$id/end") }

    suspend fun deleteSession(id: String): Result<Unit, NetworkError> =
        executeRequest<Unit> { httpClient.delete("/sessions/$id") }

    private suspend inline fun <reified T> executeRequest(
        block: suspend () -> HttpResponse,
    ): Result<T, NetworkError> {
        return try {
            val response = block()
            when (response.status) {
                HttpStatusCode.OK, HttpStatusCode.Created -> {
                    Result.Success(response.body())
                }
                HttpStatusCode.NoContent -> {
                    @Suppress("UNCHECKED_CAST")
                    Result.Success(Unit as T)
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
