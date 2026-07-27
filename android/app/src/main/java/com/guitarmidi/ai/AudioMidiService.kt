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

class AudioMidiService(
    private val context: Context,
    private val listener: (String, ProductFrame?) -> Unit,
) : AutoCloseable {
    @Volatile private var running = false
    private var worker: Thread? = null
    private var recorder: AudioRecord? = null
    private var engine: ProductEngine? = null
    private var midi: AndroidMidiSink? = null

    @SuppressLint("MissingPermission")
    fun start() {
        if (running) return
        check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)
        val minimum = AudioRecord.getMinBufferSize(
            Contract.SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_FLOAT,
        )
        fun createRecorder(source: Int) = AudioRecord(
            source, Contract.SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_FLOAT,
            max(minimum * 2, Contract.HOP * 16 * 4),
        )
        var audioRecord = createRecorder(MediaRecorder.AudioSource.UNPROCESSED)
        if (audioRecord.state != AudioRecord.STATE_INITIALIZED) {
            audioRecord.release()
            audioRecord = createRecorder(MediaRecorder.AudioSource.MIC)
        }
        check(audioRecord.state == AudioRecord.STATE_INITIALIZED) { "AudioRecord 44,1 kHz indisponible" }
        recorder = audioRecord
        engine = ProductEngine(context)
        midi = AndroidMidiSink(context)
        running = true
        audioRecord.startRecording()
        worker = Thread({ loop(audioRecord) }, "guitar-midi-audio").also { it.start() }
    }

    private fun loop(audioRecord: AudioRecord) {
        Process.setThreadPriority(Process.THREAD_PRIORITY_AUDIO)
        val hop = FloatArray(Contract.HOP)
        var filled = 0
        try {
            while (running) {
                val count = audioRecord.read(
                    hop, filled, Contract.HOP - filled, AudioRecord.READ_BLOCKING,
                )
                if (count < 0) error("Lecture audio Android: $count")
                filled += count
                if (filled < Contract.HOP) continue
                filled = 0
                val frame = requireNotNull(engine).process(hop)
                frame.decoder?.events?.forEach { requireNotNull(midi).send(it) }
                listener(if (frame.calibrated) "Actif" else "Calibration: reste silencieux", frame)
            }
        } catch (error: Throwable) {
            listener("Erreur: ${error.message}", null)
        } finally {
            requireNotNull(engine).panicEvents().forEach { midi?.send(it) }
            midi?.panic()
        }
    }

    fun stop() {
        if (!running) return
        running = false
        recorder?.stop()
        worker?.join(1500)
        recorder?.release(); recorder = null
        engine?.close(); engine = null
        midi?.close(); midi = null
        worker = null
        listener("Arrêté", null)
    }

    override fun close() = stop()
}
