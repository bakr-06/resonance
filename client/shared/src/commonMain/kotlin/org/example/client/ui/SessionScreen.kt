package org.example.client.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

@Composable
fun SessionScreen(
    viewModel: ExchangeViewModel,
    onSessionEnded: (sessionId: String) -> Unit,
) {
    val uiState by viewModel.uiState.collectAsState()

    LaunchedEffect(uiState.isSessionEnded) {
        val sessionId = uiState.activeSessionId
        if (uiState.isSessionEnded && sessionId != null) {
            onSessionEnded(sessionId)
        }
    }

    Column(
        modifier = Modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            IconButton(onClick = { /* TODO(menu): session history / settings */ }) {
                Icon(
                    imageVector = Icons.Default.Menu,
                    contentDescription = "Menu",
                )
            }

            Text(
                text = if (uiState.isSessionEnded) "Session ended" else uiState.title,
                modifier = Modifier.weight(1f),
                textAlign = TextAlign.Center,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )

            if (uiState.isSessionEnded) {
                TextButton(onClick = {}, enabled = false) {
                    Text(text = "Ended")
                }
            } else {
                Button(
                    onClick = viewModel::onEndSession,
                    enabled = !uiState.isEndingSession && uiState.recordingStatus == RecordingStatus.Idle,
                ) {
                    if (uiState.isEndingSession) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(18.dp),
                            strokeWidth = 2.dp,
                            color = MaterialTheme.colorScheme.onPrimary,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(text = if (uiState.isEndingSession) "Ending…" else "End")
                }
            }
        }

        Box(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            contentAlignment = Alignment.Center,
        ) {
            when {
                uiState.errorMessage != null ->
                    Text(text = uiState.errorMessage ?: "Something went wrong")

                uiState.isLoadingDetails -> Text(text = "Loading exchanges…")
                uiState.exchanges.isNotEmpty() -> ExchangeChat(exchanges = uiState.exchanges)
                else -> Text(text = "No exchanges yet")
            }
        }

        val isUploading = uiState.recordingStatus == RecordingStatus.Uploading
        val buttonContainerColor = when (uiState.recordingStatus) {
            RecordingStatus.Idle -> MaterialTheme.colorScheme.primary
            RecordingStatus.Capturing -> MaterialTheme.colorScheme.error
            RecordingStatus.Uploading -> MaterialTheme.colorScheme.surfaceVariant
        }
        val buttonLabel = when (uiState.recordingStatus) {
            RecordingStatus.Idle -> "Record"
            RecordingStatus.Capturing -> "Recording…"
            RecordingStatus.Uploading -> "Uploading…"
        }

        Button(
            onClick = viewModel::onRecordClick,
            enabled = !isUploading && !uiState.isSessionEnded,
            colors = ButtonDefaults.buttonColors(
                containerColor = buttonContainerColor,
            ),
        ) {
            if (isUploading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(text = buttonLabel)
        }
    }
}
