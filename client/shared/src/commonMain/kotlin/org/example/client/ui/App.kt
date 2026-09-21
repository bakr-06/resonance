package org.example.client.ui

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import org.example.client.data.AppDependencies

@Composable
fun App(
    appDependencies: AppDependencies,
) {
    val navController = rememberNavController()

    NavHost(
        navController = navController,
        startDestination = SessionDestination,
    ) {
        composable<SessionDestination> {
            val exchangeViewModel: ExchangeViewModel = viewModel {
                ExchangeViewModel(
                    sessionsRepository = appDependencies.sessionsRepository,
                    recordAudioService = appDependencies.recordAudioService,
                )
            }

            SessionScreen(
                viewModel = exchangeViewModel,
                onSessionEnded = { sessionId ->
                    println("Navigation: session ended -> Session Summary (sessionId=$sessionId)")
                    navController.navigate(SessionSummaryDestination(sessionId)) {
                        popUpTo<SessionDestination> { inclusive = true }
                    }
                },
            )
        }

        composable<SessionSummaryDestination> { backStackEntry ->
            val destination = backStackEntry.toRoute<SessionSummaryDestination>()
            SessionSummaryScreen(
                sessionId = destination.sessionId,
                onStartNewSession = {
                    println("Navigation: starting a new session")
                    navController.navigate(SessionDestination) {
                        popUpTo<SessionSummaryDestination> { inclusive = true }
                    }
                },
            )
        }
    }
}