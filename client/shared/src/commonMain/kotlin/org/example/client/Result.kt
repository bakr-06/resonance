package com.example.sportify.core.domain

typealias RootError = Error

sealed interface Result<out D, out E : RootError> {
    data class Success<D>(val data: D) : Result<D, Nothing>
    data class Error<E : RootError>(val error: E) : Result<Nothing, E>
}

inline fun <T, R, E : RootError> Result<T, E>.map(transform: (T) -> R): Result<R, E> {
    return when (this) {
        is Result.Error -> Result.Error(error)
        is Result.Success -> Result.Success(transform(data))
    }
}

fun <T, E : RootError> Result<T, E>.asEmptyDataResult(): EmptyResult<E> {
    return map { }
}

inline fun <T, E : RootError> Result<T, E>.onSuccess(action: (T) -> Unit): Result<T, E> {
    return when (this) {
        is Result.Error -> this
        is Result.Success -> {
            action(this.data)
            this
        }
    }
}

inline fun <T, E : RootError> Result<T, E>.onError(action: (E) -> Unit): Result<T, E> {
    return when (this) {
        is Result.Success -> this
        is Result.Error -> {
            action(this.error)
            this
        }
    }
}

typealias EmptyResult<E> = Result<Unit, E>