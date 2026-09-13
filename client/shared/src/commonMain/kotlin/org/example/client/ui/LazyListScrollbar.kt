package org.example.client.ui

import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
expect fun LazyListScrollbar(
    listState: LazyListState,
    modifier: Modifier,
)
