package com.guitarmidi.ai

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Process
import kotlin.math.max
import kotlin.math.roundToInt

class PolyAudioMidiService(
    private val context: Context,
    private val listener: (String, PolyProductFrame?) -> Unit,
) : AutoCloseable {
    @Volatile private var running = false
    private var worker: Thread? = null
    private var recorder: AudioRecord? = null
    private var engine: PolyProductEngine? = null
    private var midi: AndroidMidiSink? = null

    @SuppressLint("MissingPermission")
    fun start() {
        if (running) return
        check(
            context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) ==
                PackageManager.PERMISSION_GRANTED,
        )
        val minimum = AudioRecord.getMinBufferSize(
            PolyContract.SAMPLE_RATE,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_FLOAT,
        )
        check(minimum > 0) { "Capture PCM float 44,1 kHz indisponible" }
        val bufferBytes = max(
            minimum, PolyContract.HOP * 4 * Float.SIZE_BYTES,
        )
        fun createRecorder(source: Int): AudioRecord = AudioRecord.Builder()
            .setAudioSource(source)
            .setAudioFormat(
                AudioFormat.Builder()
                    .setSampleRate(PolyContract.SAMPLE_RATE)
                    .setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                    .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                    .build(),
            )
            .setBufferSizeInBytes(bufferBytes)
            .build()
        var audioRecord = createRecorder(MediaRecorder.AudioSource.UNPROCESSED)
        if (audioRecord.state != AudioRecord.STATE_INITIALIZED) {
            audioRecord.release()
            audioRecord = createRecorder(MediaRecorder.AudioSource.MIC)
        }
        check(audioRecord.state == AudioRecord.STATE_INITIALIZED) {
            "AudioRecord 44,1 kHz indisponible"
        }
        try {
            val productEngine = PolyProductEngine(context)
            val midiSink = AndroidMidiSink(context)
            recorder = audioRecord
            engine = productEngine
            midi = midiSink
            running = true
            audioRecord.startRecording()
            worker = Thread({ loop(audioRecord) }, "guitar-midi-poly-audio")
                .also { it.start() }
        } catch (error: Throwable) {
            audioRecord.release()
            throw error
        }
    }

    private fun loop(audioRecord: AudioRecord) {
        Process.setThreadPriority(Process.THREAD_PRIORITY_AUDIO)
        val hop = FloatArray(PolyContract.HOP)
        var filled = 0
        val uiEveryHops = max(
            1,
            (PolyContract.SAMPLE_RATE / PolyContract.HOP.toDouble() / 10.0)
                .roundToInt(),
        )
        var uiCountdown = 0
        try {
            while (running) {
                val count = audioRecord.read(
                    hop,
                    filled,
                    PolyContract.HOP - filled,
                    AudioRecord.READ_BLOCKING,
                )
                if (count < 0) error("Lecture audio Android: $count")
                filled += count
                if (filled < PolyContract.HOP) continue
                filled = 0
                val frame = requireNotNull(engine).process(hop)
                frame.decoder?.events?.forEach { midi?.send(it) }
                val status = when {
                    !frame.calibrated -> "Calibration: reste silencieux"
                    frame.decoder == null -> "Actif"
                    else -> "Actif - ${frame.decoder.activePitches.size} note(s)"
                }
                if (uiCountdown <= 0) {
                    listener(status, frame)
                    uiCountdown = uiEveryHops
                }
                uiCountdown--
            }
        } catch (error: Throwable) {
            listener("Erreur: ${error.message}", null)
        } finally {
            engine?.panicEvents()?.forEach { midi?.send(it) }
            midi?.panic()
        }
    }

    fun stop() {
        if (!running && recorder == null && engine == null) return
        running = false
        try {
            recorder?.stop()
        } catch (_: IllegalStateException) {
            // The recorder may already have stopped after an audio error.
        }
        worker?.join(1500)
        recorder?.release()
        recorder = null
        engine?.panicEvents()?.forEach { midi?.send(it) }
        engine?.close()
        engine = null
        midi?.close()
        midi = null
        worker = null
        listener("Arrete", null)
    }

    override fun close() = stop()
}
