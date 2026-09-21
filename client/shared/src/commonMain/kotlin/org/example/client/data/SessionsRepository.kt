package org.example.client.data

import io.ktor.client.plugins.ResponseException
import org.example.client.Result
import org.example.client.data.network.NetworkError
import org.example.client.data.network.SessionsApi
import org.example.client.data.network.dto.ExchangeDto
import org.example.client.data.network.dto.SessionDto
import java.io.File
import kotlin.math.exp

class SessionsRepository(
    private val sessionsApi: SessionsApi,
) {
    suspend fun getSessions(): Result<List<SessionDto>, NetworkError> =
        try {
            Result.Success(sessionsApi.getSessions())
        } catch (exception: ResponseException) {
            println("SessionsRepository.getSessions: HTTP error (${exception.message})")
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            println("SessionsRepository.getSessions: network failure (${exception.message})")
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun getSession(sessionId: String): Result<SessionDto, NetworkError> =
        try {
            Result.Success(sessionsApi.getSession(sessionId))
        } catch (exception: ResponseException) {
            println("SessionsRepository.getSession: HTTP error (${exception.message})")
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            println("SessionsRepository.getSession: network failure (${exception.message})")
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun getActiveSession(): Result<SessionDto?, NetworkError> =
        try {
            Result.Success(sessionsApi.getActiveSession())
        } catch (exception: ResponseException) {
            println("SessionsRepository.getActiveSession: HTTP error (${exception.message})")
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            println("SessionsRepository.getActiveSession: network failure (${exception.message})")
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun createSession(): Result<SessionDto, NetworkError> =
        try {
            Result.Success(sessionsApi.createSession())
        } catch (exception: ResponseException) {
            println("SessionsRepository.createSession: HTTP error (${exception.message})")
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            println("SessionsRepository.createSession: network failure (${exception.message})")
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun endSession(sessionId: String): Result<SessionDto, NetworkError> =
        try {
            Result.Success(sessionsApi.endSession(sessionId))
        } catch (exception: ResponseException) {
            println("SessionsRepository.endSession: HTTP error (${exception.message})")
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            println("SessionsRepository.endSession: network failure (${exception.message})")
            Result.Error(NetworkError.NetworkFailure)
        }

    suspend fun createExchange(sessionId: String, audioFile: File): Result<ExchangeDto, NetworkError> =
        try {
            Result.Success(sessionsApi.createExchange(sessionId, audioFile))
        } catch (exception: ResponseException) {
            println("SessionsRepository.createExchange: HTTP error (${exception.message})")
            Result.Error(NetworkError.HttpError(exception.response.status.value))
        } catch (exception: Exception) {
            println("SessionsRepository.createExchange: network failure (${exception.message})")
            Result.Error(NetworkError.NetworkFailure)
        }
}