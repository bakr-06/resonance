package org.example.client.ui

import androidx.compose.foundation.VerticalScrollbar
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.rememberScrollbarAdapter
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
actual fun LazyListScrollbar(
    listState: LazyListState,
    modifier: Modifier,
) {
    VerticalScrollbar(
        adapter = rememberScrollbarAdapter(listState),
        modifier = modifier,
    )
}