package org.example.client.data

import io.ktor.client.plugins.ResponseException
import org.example.client.Result
import org.example.client.data.network.NetworkError
import org.example.client.data.network.SessionsApi
import org.example.client.data.network.dto.SessionDto

class SessionsRepository(
    private val sessionsApi: SessionsApi,
) {
    suspend fun getSessions(): Result<List<SessionDto>, NetworkError> =
        try {
            Result.Success(sessionsApi.getSessions())
        } catch (exception: ResponseException) {
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun getSession(sessionId: String): Result<SessionDto, NetworkError> =
        try {
            Result.Success(sessionsApi.getSession(sessionId))
        } catch (exception: ResponseException) {
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun getActiveSession(): Result<SessionDto?, NetworkError> =
        try {
            Result.Success(sessionsApi.getActiveSession())
        } catch (exception: ResponseException) {
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun createSession(): Result<SessionDto, NetworkError> =
        try {
            Result.Success(sessionsApi.createSession())
        } catch (exception: ResponseException) {
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            Result.Error(NetworkError.NetworkFailure)
        }
}