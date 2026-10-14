package org.example.client

import androidx.compose.ui.window.Window
import androidx.compose.ui.window.application
import org.example.client.data.createAppDependencies
import org.example.client.ui.App

fun main() = application {
    val appDependencies = createAppDependencies()

    Window(
        onCloseRequest = ::exitApplication,
        title = "Resonance",
    ) {
        App(appDependencies)
    }
}