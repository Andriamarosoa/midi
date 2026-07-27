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

class MainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var pitch: TextView
    private lateinit var details: TextView
    private lateinit var button: Button
    private var service: AudioMidiService? = null
    private var active = false

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val padding = (24 * resources.displayMetrics.density).toInt()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(padding, padding * 2, padding, padding)
            setBackgroundColor(Color.rgb(244, 247, 245))
        }
        fun label(text: String, size: Float) = TextView(this).apply {
            this.text = text; textSize = size; gravity = Gravity.CENTER
            setTextColor(Color.rgb(16, 37, 30))
        }
        root.addView(label("Guitar MIDI AI", 28f), ViewGroup.LayoutParams(-1, -2))
        root.addView(label("Modèle ${Contract.PRODUCT_VERSION} · guitare mono propre", 14f))
        status = label("Arrêté", 18f).also { root.addView(it) }
        pitch = label("—", 72f).also { root.addView(it) }
        details = label("44,1 kHz · hop 256 · profil anti-fantômes", 13f)
            .also { root.addView(it) }
        button = Button(this).apply {
            text = "Démarrer"
            setOnClickListener { if (active) stopEngine() else ensurePermissionAndStart() }
        }
        root.addView(button, LinearLayout.LayoutParams(-1, -2).apply { topMargin = padding })
        root.addView(label(
            "Au démarrage, reste silencieux une seconde. Une sortie MIDI USB/Bluetooth est utilisée automatiquement si elle est disponible.",
            13f,
        ).apply { setPadding(0, padding, 0, 0) })
        setContentView(root)
    }

    private fun ensurePermissionAndStart() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 7)
        } else startEngine()
    }

    private fun startEngine() {
        if (active) return
        service = AudioMidiService(this) { text, frame ->
            runOnUiThread {
                status.text = text
                pitch.text = frame?.decoder?.pitch?.takeIf { it >= 0 }?.toString() ?: "—"
                details.text = frame?.let {
                    "fenêtre ${it.visibleWindow} · inférence %.2f ms".format(it.inferenceMs)
                } ?: "44,1 kHz · hop 256 · profil anti-fantômes"
            }
        }
        try {
            service?.start(); active = true; button.text = "Arrêter"
        } catch (error: Throwable) {
            status.text = "Erreur: ${error.message}"; service?.close(); service = null
        }
    }

    private fun stopEngine() {
        service?.close(); service = null; active = false; button.text = "Démarrer"
        pitch.text = "—"; status.text = "Arrêté"
    }

    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, permissions, results)
        if (code == 7 && results.firstOrNull() == PackageManager.PERMISSION_GRANTED) startEngine()
        else status.text = "Permission microphone requise"
    }

    override fun onStop() { stopEngine(); super.onStop() }
}
