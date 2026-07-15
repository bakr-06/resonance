package org.example.client.core.data

import org.example.client.Error

sealed interface NetworkError : Error {
    data object NoInternet : NetworkError
    data object Timeout : NetworkError
    data class ServerError(val code: Int, val message: String?) : NetworkError
    data object NotFound : NetworkError
    data class Unknown(val cause: Throwable) : NetworkError
}
