package org.example.client.session.data

import org.example.client.Result
import org.example.client.core.data.NetworkError
import org.example.client.core.data.remote.dto.SessionDto
import org.example.client.map
import org.example.client.session.data.remote.SessionApiDataSource
import org.example.client.session.domain.Session
import org.example.client.session.domain.toDomain

class SessionRepository(private val dataSource: SessionApiDataSource) {

    suspend fun createSession(): Result<Session, NetworkError> =
        dataSource.createSession().map(SessionDto::toDomain)

    suspend fun getSessions(): Result<List<Session>, NetworkError> =
        dataSource.getSessions().map { dtoList -> dtoList.map(SessionDto::toDomain) }

    suspend fun getSession(id: String): Result<Session, NetworkError> =
        dataSource.getSession(id).map(SessionDto::toDomain)

    suspend fun endSession(id: String): Result<Session, NetworkError> =
        dataSource.endSession(id).map(SessionDto::toDomain)

    suspend fun deleteSession(id: String): Result<Unit, NetworkError> =
        dataSource.deleteSession(id)
}
