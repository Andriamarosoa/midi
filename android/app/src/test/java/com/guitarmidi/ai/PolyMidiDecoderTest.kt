package com.guitarmidi.ai

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PolyMidiDecoderTest {
    private fun prediction(
        frames: Map<Int, Float>,
        onsets: Map<Int, Float> = emptyMap(),
        harmonicBase: Int? = null,
        harmonicNumber: Int = 2,
    ): PolyPrediction {
        val frame = FloatArray(PolyContract.PITCH_CLASSES)
        val onset = FloatArray(PolyContract.PITCH_CLASSES)
        frames.forEach { (pitch, value) -> frame[pitch - PolyContract.MIN_PITCH] = value }
        onsets.forEach { (pitch, value) -> onset[pitch - PolyContract.MIN_PITCH] = value }
        val harmonics = FloatArray(PolyContract.PITCH_CLASSES * PolyContract.HARMONICS)
        if (harmonicBase != null) {
            harmonics[
                (harmonicBase - PolyContract.MIN_PITCH) * PolyContract.HARMONICS +
                    harmonicNumber - 1
            ] = 1f
        }
        return PolyPrediction(frame, onset, harmonics, FloatArray(harmonics.size), 0.0)
    }

    private fun decoder(maximumPolyphony: Int = 6) = PolyMidiDecoder(
        PolyDecoderConfig(
            frameOnThreshold = 0.50f,
            strongFrameThreshold = 0.80f,
            frameOffThreshold = 0.25f,
            onsetThreshold = 0.50f,
            activationFrames = 2,
            releaseFrames = 2,
            minimumRetriggerFrames = 2,
            maximumPolyphony = maximumPolyphony,
        ),
    )

    @Test fun simultaneousOnsetsEmitAChord() {
        val result = decoder().step(
            prediction(
                mapOf(40 to 0.9f, 44 to 0.9f, 47 to 0.9f),
                mapOf(40 to 0.9f, 44 to 0.9f, 47 to 0.9f),
            ),
            audioActive = true,
        )
        assertEquals(3, result.events.count { it.on })
        assertArrayEquals(intArrayOf(40, 44, 47), result.activePitches)
    }

    @Test fun harmonicTailIsSuppressedButDirectOnsetSurvives() {
        val decoder = decoder()
        decoder.step(
            prediction(mapOf(40 to 0.9f), mapOf(40 to 0.9f)),
            audioActive = true,
        )
        repeat(2) {
            val result = decoder.step(
                prediction(mapOf(40 to 0.9f, 52 to 0.60f), harmonicBase = 40),
                audioActive = true,
            )
            assertFalse(result.activePitches.contains(52))
        }
        val realNote = decoder.step(
            prediction(
                mapOf(40 to 0.9f, 52 to 0.60f),
                mapOf(52 to 0.90f),
                harmonicBase = 40,
            ),
            audioActive = true,
        )
        assertTrue(realNote.activePitches.contains(52))
    }

    @Test fun maximumPolyphonyAndPanicAreGlobal() {
        val decoder = decoder(maximumPolyphony = 2)
        val result = decoder.step(
            prediction(
                mapOf(40 to 0.7f, 44 to 0.8f, 47 to 0.9f),
                mapOf(40 to 0.7f, 44 to 0.8f, 47 to 0.9f),
            ),
            audioActive = true,
        )
        assertArrayEquals(intArrayOf(44, 47), result.activePitches)
        val panic = decoder.panic()
        assertEquals(2, panic.size)
        assertTrue(panic.all { !it.on })
    }

    @Test fun silenceReleasesEveryActivePitch() {
        val decoder = decoder()
        decoder.step(
            prediction(mapOf(40 to 0.9f, 47 to 0.9f), mapOf(40 to 0.9f, 47 to 0.9f)),
            audioActive = true,
        )
        decoder.step(prediction(emptyMap()), audioActive = false)
        val release = decoder.step(prediction(emptyMap()), audioActive = false)
        assertEquals(2, release.events.size)
        assertTrue(release.events.all { !it.on })
        assertEquals(0, release.activePitches.size)
    }

    @Test fun inactiveHopCannotCreateANoteFromStrongPredictions() {
        val result = decoder().step(
            prediction(mapOf(40 to 0.99f), mapOf(40 to 0.99f)),
            audioActive = false,
        )
        assertEquals(0, result.events.size)
        assertEquals(0, result.activePitches.size)
    }

    @Test fun inactiveHopBreaksConsecutiveActivationVotes() {
        val decoder = decoder()
        val frameOnly = prediction(mapOf(40 to 0.75f))
        assertEquals(0, decoder.step(frameOnly, audioActive = true).events.size)
        assertEquals(0, decoder.step(frameOnly, audioActive = false).events.size)
        assertEquals(0, decoder.step(frameOnly, audioActive = true).events.size)
        assertEquals(1, decoder.step(frameOnly, audioActive = true).events.size)
    }
}
