package org.example.client.data

import java.io.File

// This service class is responsible for recording audio and interact with the OS.
// It should be able to start a recording and end it returning an audio file. No network calls

// TODO(recording): `java.io.File` in commonMain is a JVM-type leak in a multiplatform API — it
//  resolves today only because both targets (JVM, Android) happen to ship it. The moment an iOS
//  target is added, this breaks at the expect/actual boundary. Fix when improving: abstract the
//  temp-file concept (e.g. kotlinx-io Path or a platform-specific temp-file provider) so common
//  code stops naming a JVM class.
// TODO(recording): Naming inconsistency — this class is called "Service" but sits in the `data`
//  layer next to SessionsRepository, opposite a "Repository". "Service" isn't a layer this codebase
//  uses elsewhere; this is really a device port (captures audio from the OS). If naming becomes a
//  pain point, consider renaming to AudioCapturePort / AudioRecorder or giving it a home that makes
//  its role obvious. Cosmetic — deliberately deferred.
@Suppress("EXPECT_ACTUAL_CLASSIFIERS_ARE_IN_BETA_WARNING")
expect class RecordAudioService {
    constructor()
    fun startRecording()
    suspend fun stopRecording(): File?
}