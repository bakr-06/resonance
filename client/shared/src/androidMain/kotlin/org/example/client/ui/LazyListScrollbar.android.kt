package org.example.client.ui

import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
actual fun LazyListScrollbar(
    listState: LazyListState,
    modifier: Modifier,
) {
    // Android reaches the list by touch drag already, so no scrollbar is rendered there.
    // The Desktop (JVM) target renders a draggable VerticalScrollbar via LazyListScrollbar.jvm.kt.
}