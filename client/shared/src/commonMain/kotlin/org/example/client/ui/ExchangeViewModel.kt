package org.example.client.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import org.example.client.Result
import org.example.client.data.RecordAudioService
import org.example.client.data.SessionsRepository

class ExchangeViewModel internal constructor(
    private val sessionsRepository: SessionsRepository,
    private val recordAudioService: RecordAudioService
) : ViewModel() {

    private val _uiState = MutableStateFlow(ExchangeUiState())
    val uiState: StateFlow<ExchangeUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoadingDetails = true)

            val session = when (val result = sessionsRepository.getActiveSession()) {
                is Result.Success -> result.data
                is Result.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingDetails = false,
                        errorMessage = result.error.toErrorMessage(),
                    )
                    return@launch
                }
            }

            val activeSession = session ?: when (val result = sessionsRepository.createSession()) {
                is Result.Success -> result.data
                is Result.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isLoadingDetails = false,
                        errorMessage = result.error.toErrorMessage(),
                    )
                    return@launch
                }
            }

            _uiState.value = _uiState.value.copy(
                title = activeSession.title ?: "",
                exchanges = activeSession.exchanges.map { it.toExchangeUi() },
                activeSessionId = activeSession.id,
                isLoadingDetails = false,
            )
        }
    }

    fun onRecordClick() {
        when (_uiState.value.recordingStatus) {
            RecordingStatus.Idle -> {
                _uiState.value = _uiState.value.copy(recordingStatus = RecordingStatus.Capturing)

                // TODO(recording): startRecording() can throw (LineUnavailableException when mic is busy,
                //  IllegalArgumentException etc.) and it's called AFTER the state was flipped to Capturing.
                //  If the mic fails, the UI stays stuck red "Recording…" forever — RecordingStatus has no
                //  error state and no rollback path. Fix when improving: wrap in try/catch, roll state back
                //  to Idle and surface errorMessage.
                recordAudioService.startRecording()
            }

            RecordingStatus.Capturing -> {
                _uiState.value = _uiState.value.copy(recordingStatus = RecordingStatus.Uploading)
                uploadRecording()
            }

            RecordingStatus.Uploading -> Unit
        }
    }

    fun onEndSession() {
        val sessionId = _uiState.value.activeSessionId ?: return
        val recording = _uiState.value.recordingStatus
        if (recording != RecordingStatus.Idle) return
        val alreadyEnded = _uiState.value.isSessionEnded
        val alreadyEnding = _uiState.value.isEndingSession
        if (alreadyEnded || alreadyEnding) return

        _uiState.value = _uiState.value.copy(isEndingSession = true)
        viewModelScope.launch {
            when (val result = sessionsRepository.endSession(sessionId)) {
                is Result.Success -> {
                    _uiState.value = _uiState.value.copy(
                        isEndingSession = false,
                        isSessionEnded = true,
                    )
                }

                is Result.Error -> {
                    _uiState.value = _uiState.value.copy(
                        isEndingSession = false,
                        errorMessage = result.error.toErrorMessage(),
                    )
                }
            }
        }
    }

    private fun uploadRecording() {
        viewModelScope.launch {
            val sessionId = _uiState.value.activeSessionId

            // TODO(recording): Temp-file ownership is split across two classes with an implicit protocol.
            //  RecordAudioService creates and returns the temp WAV here, but the ViewModel must remember
            //  to delete() it on all paths — forget once and the OS temp dir leaks files. The contract
            //  lives only in caller discipline (it caused a leak in the early-return path that's now
            //  hand-patched). Fix when improving: service owns cleanup (delete()/close()), or route the
            //  file's lifetime through a single owning API in a finally.
            val audioFile = recordAudioService.stopRecording()
            if (audioFile == null || sessionId == null) {
                audioFile?.delete()
                _uiState.value = _uiState.value.copy(
                    recordingStatus = RecordingStatus.Idle,
                    errorMessage = "Recording could not be uploaded",
                )
                return@launch
            }

            // TODO(recording): Data loss on upload failure — audioFile.delete() runs unconditionally
            //  right after createExchange, before the failure branch is examined. If createExchange fails
            //  (server down, LLM timeout, HTTP 4xx/5xx), the user's voice note is destroyed with no retry
            //  possible — the audio existed only in this temp file. Fix when improving: on Result.Error
            //  keep the file and offer a retry action, or delete lazily (only on success / when replaced).
            val result = sessionsRepository.createExchange(sessionId, audioFile)
            audioFile.delete()

            when (result) {
                is Result.Success -> {
                    val exchange = result.data.toExchangeUi()
                    _uiState.value = _uiState.value.copy(
                        recordingStatus = RecordingStatus.Idle,
                        exchanges = _uiState.value.exchanges + exchange,
                    )
                }

                is Result.Error -> {
                    _uiState.value = _uiState.value.copy(
                        recordingStatus = RecordingStatus.Idle,
                        errorMessage = result.error.toErrorMessage(),
                    )
                }
            }
        }
    }

    fun loadSessionDetails(sessionId: String) {
        _uiState.value = _uiState.value.copy(isLoadingDetails = true)
        viewModelScope.launch {
            when (val result = sessionsRepository.getSession(sessionId)) {
                is Result.Success -> {
                    _uiState.value = _uiState.value.copy(
                        title = result.data.title ?: "",
                        exchanges = result.data.exchanges.map { it.toExchangeUi() },
                        activeSessionId = result.data.id,
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
