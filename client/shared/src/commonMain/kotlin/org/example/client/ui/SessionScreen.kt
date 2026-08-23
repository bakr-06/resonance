package org.example.client.ui

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.PermanentDrawerSheet
import androidx.compose.material3.PermanentNavigationDrawer
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier

@Composable
fun SessionScreen(
    viewModel: ExchangeViewModel,
) {
    val uiState by viewModel.sessions.collectAsState()

    PermanentNavigationDrawer(
        drawerContent = {
            PermanentDrawerSheet {
                uiState.sessions.forEach { session ->
                    NavigationDrawerItem(
                        label = { Text(session.title) },
                        selected = session.id == uiState.selectedSessionId,
                        onClick = { viewModel.selectSession(session.id) },
                    )
                }
            }
        },
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
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
    }
}