package org.example.client.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.lifecycle.ViewModelStore
import androidx.lifecycle.ViewModelStoreOwner
import androidx.lifecycle.viewmodel.compose.LocalViewModelStoreOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import org.example.client.data.AppDependencies

@Composable
fun App(
    appDependencies: AppDependencies,
) {
    val viewModelStoreOwner = remember {
        object : ViewModelStoreOwner {
            override val viewModelStore: ViewModelStore = ViewModelStore()
        }
    }

    CompositionLocalProvider(
        LocalViewModelStoreOwner provides viewModelStoreOwner,
    ) {
        val exchangeViewModel: ExchangeViewModel = viewModel {
            ExchangeViewModel(appDependencies.sessionsRepository)
        }
        SessionsScreen(viewModel = exchangeViewModel)
    }
}