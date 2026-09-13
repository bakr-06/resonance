package org.example.client.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun ExchangeChat(
    exchanges: List<ExchangeUi>,
) {
    val listState = rememberLazyListState()

    LaunchedEffect(exchanges.size) {
        if (exchanges.isNotEmpty()) {
            listState.animateScrollToItem(exchanges.size * 2 - 1)
        }
    }

    Box(modifier = Modifier.fillMaxSize()) {
        LazyColumn(
            state = listState,
            modifier = Modifier.fillMaxSize().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(exchanges, key = { it.id }) { exchange ->
                ExchangeBubble(
                    text = exchange.transcript,
                    timestamp = exchange.timestamp,
                    isUser = true,
                )
                ExchangeBubble(
                    text = exchange.reflection,
                    timestamp = exchange.timestamp,
                    isUser = false,
                )
            }
        }

        LazyListScrollbar(
            listState = listState,
            modifier = Modifier.align(Alignment.CenterEnd).fillMaxHeight(),
        )
    }
}

@Composable
private fun ExchangeBubble(
    text: String,
    timestamp: String,
    isUser: Boolean,
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Column(
            modifier = Modifier
                .widthIn(max = 400.dp)
                .background(
                    color = if (isUser) {
                        MaterialTheme.colorScheme.primaryContainer
                    } else {
                        MaterialTheme.colorScheme.secondaryContainer
                    },
                    shape = RoundedCornerShape(12.dp),
                )
                .padding(horizontal = 12.dp, vertical = 8.dp),
        ) {
            Text(
                text = text,
                color = if (isUser) {
                    MaterialTheme.colorScheme.onPrimaryContainer
                } else {
                    MaterialTheme.colorScheme.onSecondaryContainer
                },
            )
            Text(
                text = timestamp,
                modifier = Modifier.align(Alignment.End),
                style = MaterialTheme.typography.labelSmall,
                color = if (isUser) {
                    MaterialTheme.colorScheme.onPrimaryContainer
                } else {
                    MaterialTheme.colorScheme.onSecondaryContainer
                },
            )
        }
    }
}