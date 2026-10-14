package org.example.client.data

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.io.File
import javax.sound.sampled.AudioFileFormat
import javax.sound.sampled.AudioFormat
import javax.sound.sampled.AudioInputStream
import javax.sound.sampled.AudioSystem
import javax.sound.sampled.DataLine
import javax.sound.sampled.TargetDataLine

@Suppress("EXPECT_ACTUAL_CLASSIFIERS_ARE_IN_BETA_WARNING")
actual class RecordAudioService {

    private val recordingScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private var line: TargetDataLine? = null
    private var writeJob: Job? = null
    private var outputFile: File? = null

    // TODO(recording): startRecording() has no reentrancy guard — calling it twice without stopRecording()
    //  leaks the previous TargetDataLine (mic stays held) and leaves the old writeJob running, while
    //  outputFile is silently overwritten and the old recording is orphaned. Also nothing cleans up if
    //  getLine/open/start throws halfway (a line opened but never written, a temp file created but empty).
    //  Fix when improving: require the service to be idle first (`require(line == null)` or return a status),
    //  and clean up partial state on failure.
    actual fun startRecording() {
        // Whisper-friendly format: 16kHz, 16-bit, Mono
        val format = AudioFormat(16000f, 16, 1, true, false)
        val info = DataLine.Info(TargetDataLine::class.java, format)

        val newLine = AudioSystem.getLine(info) as TargetDataLine
        newLine.open(format)
        newLine.start()

        val tmpFile = File.createTempFile("resonance-exchange", ".wav")
        outputFile = tmpFile
        line = newLine

        writeJob = recordingScope.launch {
            // Blocks and streams mic input directly to the WAV file.
            // Closing the line (in stopRecording) makes this return and flush the file.
            AudioSystem.write(AudioInputStream(newLine), AudioFileFormat.Type.WAVE, tmpFile)
        }
    }

    actual suspend fun stopRecording(): File? {
        val currentLine = line ?: return null

        currentLine.stop()
        currentLine.close() // Ends the AudioInputStream, letting AudioSystem.write() terminate

        writeJob?.join() // Wait for the WAV to be fully flushed before returning the file
        writeJob = null
        line = null

        return outputFile
    }
}