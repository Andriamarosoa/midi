package com.guitarmidi.ai

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

class PolyMainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var notes: TextView
    private lateinit var details: TextView
    private lateinit var button: Button
    private var service: PolyAudioMidiService? = null
    private var active = false

    private fun noteName(pitch: Int): String {
        val names = arrayOf("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
        return "${names[pitch % 12]}${pitch / 12 - 1}"
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val padding = (24 * resources.displayMetrics.density).toInt()
        fun label(text: String, size: Float) = TextView(this).apply {
            this.text = text
            textSize = size
            gravity = Gravity.CENTER
            setTextColor(Color.rgb(16, 37, 30))
        }
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(padding, padding * 2, padding, padding)
            setBackgroundColor(Color.rgb(244, 247, 245))
        }
        root.addView(label("Guitar MIDI AI", 28f), ViewGroup.LayoutParams(-1, -2))
        root.addView(label("Modèle ${PolyContract.PRODUCT_VERSION} · guitare polyphonique", 14f))
        status = label("Arrêté", 18f).also { root.addView(it) }
        notes = label("—", 46f).also { root.addView(it) }
        details = label("44,1 kHz · hop 256 · jusqu’à six notes", 13f)
            .also { root.addView(it) }
        button = Button(this).apply {
            text = "Démarrer"
            setOnClickListener {
                if (active) stopEngine() else ensurePermissionAndStart()
            }
        }
        root.addView(
            button,
            LinearLayout.LayoutParams(-1, -2).apply { topMargin = padding },
        )
        root.addView(label(
            "Au démarrage, reste silencieux une seconde. Une interface guitare USB propre est recommandée.",
            13f,
        ).apply { setPadding(0, padding, 0, 0) })
        setContentView(root)
    }

    private fun ensurePermissionAndStart() {
        if (
            checkSelfPermission(Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 7)
        } else {
            startEngine()
        }
    }

    private fun startEngine() {
        if (active) return
        service = PolyAudioMidiService(this) { text, frame ->
            runOnUiThread {
                status.text = text
                val pitches = frame?.decoder?.activePitches ?: intArrayOf()
                notes.text = if (pitches.isEmpty()) "—" else pitches.joinToString("  ") {
                    noteName(it)
                }
                details.text = frame?.let {
                    "${pitches.size} note(s) · fenêtre ${it.visibleWindow} · inférence %.2f ms"
                        .format(it.inferenceMs)
                } ?: "44,1 kHz · hop 256 · jusqu’à six notes"
            }
        }
        try {
            service?.start()
            active = true
            button.text = "Arrêter"
        } catch (error: Throwable) {
            status.text = "Erreur: ${error.message}"
            service?.close()
            service = null
        }
    }

    private fun stopEngine() {
        service?.close()
        service = null
        active = false
        button.text = "Démarrer"
        notes.text = "—"
        status.text = "Arrêté"
        details.text = "44,1 kHz · hop 256 · jusqu’à six notes"
    }

    override fun onRequestPermissionsResult(
        code: Int,
        permissions: Array<out String>,
        results: IntArray,
    ) {
        super.onRequestPermissionsResult(code, permissions, results)
        if (code == 7 && results.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            startEngine()
        } else {
            status.text = "Permission microphone requise"
        }
    }

    override fun onStop() {
        stopEngine()
        super.onStop()
    }
}
