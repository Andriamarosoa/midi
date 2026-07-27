package com.guitarmidi.ai

import android.content.Context
import android.media.midi.MidiDevice
import android.media.midi.MidiDeviceInfo
import android.media.midi.MidiInputPort
import android.media.midi.MidiManager

class AndroidMidiSink(context: Context) : AutoCloseable {
    private val manager = context.getSystemService(MidiManager::class.java)
    private var device: MidiDevice? = null
    private var port: MidiInputPort? = null
    @Volatile var deviceName: String = "Aucune sortie MIDI (affichage seul)"
        private set

    init { connectFirst() }

    @Synchronized private fun connectFirst() {
        val info = manager.devices.firstOrNull { candidate ->
            candidate.ports.any { it.type == MidiDeviceInfo.PortInfo.TYPE_INPUT }
        } ?: return
        val portNumber = info.ports.first { it.type == MidiDeviceInfo.PortInfo.TYPE_INPUT }.portNumber
        manager.openDevice(info, { opened ->
            if (opened != null) {
                device = opened
                port = opened.openInputPort(portNumber)
                deviceName = info.properties.getString(MidiDeviceInfo.PROPERTY_NAME)
                    ?: "Sortie MIDI Android"
            }
        }, null)
    }

    @Synchronized fun send(event: MidiEvent) {
        val status = if (event.on) 0x90 else 0x80
        port?.send(
            byteArrayOf(status.toByte(), event.pitch.toByte(), event.velocity.toByte()),
            0, 3, System.nanoTime(),
        )
    }

    @Synchronized fun panic() {
        port?.send(byteArrayOf(0xB0.toByte(), 123, 0), 0, 3, System.nanoTime())
        for (pitch in 0..127) {
            port?.send(byteArrayOf(0x80.toByte(), pitch.toByte(), 0), 0, 3, System.nanoTime())
        }
    }

    override fun close() {
        panic(); port?.close(); device?.close(); port = null; device = null
    }
}
