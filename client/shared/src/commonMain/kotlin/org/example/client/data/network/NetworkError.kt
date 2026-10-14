package org.example.client.data.network

import org.example.client.Error

sealed interface NetworkError : Error {
    data object NetworkFailure : NetworkError
    data class HttpError(val statusCode: Int) : NetworkError
}