package org.example.client.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.example.client.Result
import org.example.client.data.SessionsRepository

class ExchangeViewModel(
    private val sessionsRepository: SessionsRepository,
) : ViewModel() {

    private val _sessions = MutableStateFlow(SessionsUiState())
    val sessions: StateFlow<SessionsUiState> = _sessions.asStateFlow()

    init {
        viewModelScope.launch {
            when (val result = sessionsRepository.getSessions()) {
                is Result.Success -> {
                    val sessions = result.data.map { it.toSessionUi() }
                    _sessions.value = SessionsUiState(
                        sessions = sessions,
                        selectedSessionId = sessions.firstOrNull()?.id,
                    )
                    val firstSessionId = sessions.firstOrNull()?.id
                    if (firstSessionId != null) {
                        loadSessionDetails(firstSessionId)
                    }
                }
                is Result.Error -> _sessions.value = SessionsUiState(
                    errorMessage = result.error.toErrorMessage(),
                )
            }
        }
    }

    fun selectSession(sessionId: String) {
        if (sessionId == _sessions.value.selectedSessionId) return
        _sessions.value = _sessions.value.copy(
            selectedSessionId = sessionId,
            exchanges = emptyList(),
            errorMessage = null,
        )
        loadSessionDetails(sessionId)
    }

    private fun loadSessionDetails(sessionId: String) {
        _sessions.value = _sessions.value.copy(isLoadingDetails = true)
        viewModelScope.launch {
            when (val result = sessionsRepository.getSession(sessionId)) {
                is Result.Success -> {
                    if (sessionId != _sessions.value.selectedSessionId) return@launch
                    _sessions.value = _sessions.value.copy(
                        exchanges = result.data.exchanges.map { it.toExchangeUi() },
                        isLoadingDetails = false,
                    )
                }
                is Result.Error -> {
                    if (sessionId != _sessions.value.selectedSessionId) return@launch
                    _sessions.value = _sessions.value.copy(
                        isLoadingDetails = false,
                        errorMessage = result.error.toErrorMessage(),
                    )
                }
            }
        }
    }
}