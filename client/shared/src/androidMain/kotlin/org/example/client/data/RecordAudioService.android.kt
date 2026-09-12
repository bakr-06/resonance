package org.example.client.data

import java.io.File

@Suppress("EXPECT_ACTUAL_CLASSIFIERS_ARE_IN_BETA_WARNING")
actual class RecordAudioService {
    actual fun startRecording() {
        throw NotImplementedError("Recording not yet implemented on Android")
    }

    actual suspend fun stopRecording(): File? {
        throw NotImplementedError("Recording not yet implemented on Android")
    }
}