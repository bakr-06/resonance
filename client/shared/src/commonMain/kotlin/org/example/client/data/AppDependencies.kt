package org.example.client.data

import org.example.client.data.network.SessionsApi
import org.example.client.data.network.createHttpClient

class AppDependencies(
    val sessionsRepository: SessionsRepository,
)

fun createAppDependencies(): AppDependencies {
    val httpClient = createHttpClient()
    val sessionsApi = SessionsApi(
        httpClient = httpClient,
        baseUrl = "http://localhost:8000",
    )
    return AppDependencies(
        sessionsRepository = SessionsRepository(sessionsApi),
    )
}