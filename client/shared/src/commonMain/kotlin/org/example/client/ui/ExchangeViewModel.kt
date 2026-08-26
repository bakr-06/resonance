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

    private val _uiState = MutableStateFlow(ExchangeUiState())
    val uiState: StateFlow<ExchangeUiState> = _uiState.asStateFlow()

    fun loadSessionDetails(sessionId: String) {
        _uiState.value = _uiState.value.copy(isLoadingDetails = true)
        viewModelScope.launch {
            when (val result = sessionsRepository.getSession(sessionId)) {
                is Result.Success -> {
                    _uiState.value = _uiState.value.copy(
                        exchanges = result.data.exchanges.map { it.toExchangeUi() },
                        isLoadingDetails = false,
                    )
                }
                is Result.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingDetails = false,
                        errorMessage = result.error.toErrorMessage(),
                    )
                }
            }
        }
    }
}
