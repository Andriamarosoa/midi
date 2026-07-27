from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from src.product.audio_io import (
    audio_devices,
    open_input_stream,
    resolve_wdm_ks_device,
    resolve_wasapi_device,
)
from src.product.audio_output import FluidSynthWasapiSink
from src.product.decoder import MidiEvent


class _FakeStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.latency = 0.022
        self.started = False
        self.stopped = False
        self.closed = False
        self.active = False

    def start(self):
        self.started = True
        self.active = True
        callback = self.kwargs.get("callback")
        if callback is not None and hasattr(self, "direction"):
            frames = int(self.kwargs["blocksize"])
            channels = int(self.kwargs["channels"])
            for _ in range(16):
                block = np.zeros((frames, channels), dtype=np.float32)
                callback(block, frames, None, False)

    def stop(self):
        self.stopped = True
        self.active = False

    def close(self):
        self.closed = True
        self.active = False


class _FakeSoundDevice:
    def __init__(
        self,
        fail_input_devices=(),
        fail_output_devices=(),
        stream_latencies=None,
        include_wdm=False,
    ):
        self.hostapis = [
            {"name": "MME", "default_input_device": 0, "default_output_device": 1},
            {"name": "Windows WASAPI", "default_input_device": 2, "default_output_device": 3},
        ]
        self.devices = [
            self._device("External Microphone (Realtek(R)", 0, 1, 0, 44100, 0.090, 0.0),
            self._device("Headphones (Realtek(R) Audio)", 0, 0, 2, 44100, 0.0, 0.090),
            self._device("External Microphone (Realtek(R) Audio)", 1, 2, 0, 48000, 0.003, 0.0),
            self._device("Headphones (Realtek(R) Audio)", 1, 0, 2, 48000, 0.0, 0.003),
        ]
        if include_wdm:
            self.hostapis.append({
                "name": "Windows WDM-KS",
                "default_input_device": 4,
                "default_output_device": 5,
            })
            self.devices.extend([
                self._device(
                    "Microphone (Realtek HD Audio Mic input)",
                    2, 1, 0, 44100, 0.010, 0.0,
                ),
                self._device(
                    "Headphones 1 (Realtek HD Audio output)",
                    2, 0, 2, 44100, 0.0, 0.010,
                ),
                self._device(
                    "Headphones 2 (Realtek HD Audio output)",
                    2, 0, 2, 44100, 0.0, 0.010,
                ),
            ])
        self.default = SimpleNamespace(device=[0, 1])
        self.fail_input_devices = set(fail_input_devices)
        self.fail_output_devices = set(fail_output_devices)
        self.stream_latencies = dict(stream_latencies or {})
        self.input_streams = []
        self.output_streams = []

    @staticmethod
    def _device(name, hostapi, inputs, outputs, rate, in_latency, out_latency):
        return {
            "name": name,
            "hostapi": hostapi,
            "max_input_channels": inputs,
            "max_output_channels": outputs,
            "default_samplerate": float(rate),
            "default_low_input_latency": in_latency,
            "default_low_output_latency": out_latency,
        }

    def query_hostapis(self):
        return self.hostapis

    def query_devices(self, device=None, kind=None):
        if device is None and kind is None:
            return self.devices
        if device is None:
            index = self.default.device[0 if kind == "input" else 1]
        else:
            index = int(device)
        result = dict(self.devices[index])
        result["index"] = index
        return result

    @staticmethod
    def WasapiSettings(**kwargs):
        return ("wasapi", kwargs)

    def InputStream(self, **kwargs):
        if kwargs.get("device") in self.fail_input_devices:
            raise RuntimeError("input open failed")
        stream = _FakeStream(**kwargs)
        stream.direction = "input"
        stream.latency = self.stream_latencies.get(
            ("input", kwargs.get("device")), stream.latency
        )
        self.input_streams.append(stream)
        return stream

    def OutputStream(self, **kwargs):
        if kwargs.get("device") in self.fail_output_devices:
            raise RuntimeError("output open failed")
        stream = _FakeStream(**kwargs)
        stream.direction = "output"
        stream.latency = self.stream_latencies.get(
            ("output", kwargs.get("device")), stream.latency
        )
        self.output_streams.append(stream)
        return stream


class AudioInputSelectionTests(unittest.TestCase):
    def _open(self, sd, preferred=None, **kwargs):
        return open_input_stream(
            preferred_device=preferred,
            channels=1,
            samplerate=44100,
            blocksize=256,
            dtype="float32",
            latency="low",
            callback=lambda *_args: None,
            _sd=sd,
            **kwargs,
        )

    def test_auto_resolves_wasapi_counterpart_with_shared_conversion(self):
        sd = _FakeSoundDevice()
        self.assertEqual(resolve_wasapi_device("input", _sd=sd), 2)
        stream, info = self._open(sd)
        self.assertEqual(stream.kwargs["device"], 2)
        self.assertEqual(
            stream.kwargs["extra_settings"],
            ("wasapi", {"exclusive": False, "auto_convert": True}),
        )
        self.assertTrue(info.automatic_selection)
        self.assertTrue(info.wasapi_shared)
        self.assertTrue(info.conversion_active)

    def test_auto_falls_back_to_system_default_if_wasapi_fails(self):
        sd = _FakeSoundDevice(fail_input_devices=(2,))
        stream, info = self._open(sd)
        self.assertIsNone(stream.kwargs["device"])
        self.assertEqual(info.device_index, 0)
        self.assertFalse(info.wasapi_shared)

    def test_auto_uses_lowest_negotiated_latency_not_advertised_default(self):
        sd = _FakeSoundDevice(stream_latencies={
            ("input", 2): 0.022,
            ("input", None): 0.017,
        })
        stream, info = self._open(sd)
        self.assertIsNone(stream.kwargs["device"])
        self.assertEqual(info.host_api, "MME")
        self.assertAlmostEqual(info.latency_ms, 17.0)

    def test_wasapi_default_is_not_reopened_without_shared_settings(self):
        sd = _FakeSoundDevice()
        sd.default.device = [2, 3]
        stream, info = self._open(sd)
        self.assertEqual(stream.kwargs["device"], 2)
        self.assertIn("extra_settings", stream.kwargs)
        self.assertTrue(info.wasapi_shared)

    def test_explicit_mme_is_honoured_without_conversion_settings(self):
        sd = _FakeSoundDevice()
        stream, info = self._open(sd, 0)
        self.assertEqual(stream.kwargs["device"], 0)
        self.assertNotIn("extra_settings", stream.kwargs)
        self.assertFalse(info.automatic_selection)

    def test_explicit_wasapi_gets_auto_convert(self):
        sd = _FakeSoundDevice()
        stream, info = self._open(sd, 2)
        self.assertEqual(stream.kwargs["device"], 2)
        self.assertIn("extra_settings", stream.kwargs)
        self.assertTrue(info.wasapi_shared)

    def test_explicit_failure_is_not_silently_rerouted(self):
        sd = _FakeSoundDevice(fail_input_devices=(2,))
        with self.assertRaisesRegex(RuntimeError, "input open failed"):
            self._open(sd, 2)

    def test_device_listing_exposes_host_api_and_low_latency(self):
        rows = audio_devices("input", _sd=_FakeSoundDevice())
        self.assertEqual([row["index"] for row in rows], [0, 2])
        self.assertEqual(rows[1]["host_api"], "Windows WASAPI")
        self.assertEqual(rows[1]["low_latency_ms"], 3.0)

    def test_auto_skips_wdm_ks_input_because_it_can_bypass_microphone_gain(self):
        sd = _FakeSoundDevice(
            include_wdm=True,
            stream_latencies={
                ("input", 4): 0.003,
                ("input", 2): 0.022,
                ("input", None): 0.017,
            },
        )
        self.assertEqual(
            resolve_wdm_ks_device(
                "input", samplerate=44100, _sd=sd
            ),
            4,
        )
        stream, info = self._open(sd)
        self.assertIsNone(stream.kwargs["device"])
        self.assertEqual(info.host_api, "MME")
        self.assertFalse(info.kernel_streaming)
        self.assertAlmostEqual(info.latency_ms, 17.0)

    def test_auto_can_explicitly_opt_in_to_matching_native_wdm_ks(self):
        sd = _FakeSoundDevice(
            include_wdm=True,
            stream_latencies={
                ("input", 4): 0.003,
                ("input", 2): 0.022,
                ("input", None): 0.017,
            },
        )
        stream, info = self._open(sd, prefer_kernel_streaming=True)
        self.assertEqual(stream.kwargs["device"], 4)
        self.assertEqual(stream.kwargs["latency"], 0.002)
        self.assertTrue(info.kernel_streaming)
        self.assertFalse(info.conversion_active)
        self.assertAlmostEqual(info.latency_ms, 3.0)

    def test_auto_falls_back_when_matching_wdm_ks_cannot_open(self):
        sd = _FakeSoundDevice(
            include_wdm=True,
            fail_input_devices=(4,),
            stream_latencies={
                ("input", 2): 0.022,
                ("input", None): 0.017,
            },
        )
        stream, info = self._open(sd, prefer_kernel_streaming=True)
        self.assertIsNone(stream.kwargs["device"])
        self.assertEqual(info.host_api, "MME")
        self.assertFalse(info.kernel_streaming)

    def test_explicit_wdm_ks_uses_low_latency_request(self):
        sd = _FakeSoundDevice(
            include_wdm=True,
            stream_latencies={("input", 4): 0.003},
        )
        stream, info = self._open(sd, 4)
        self.assertEqual(stream.kwargs["latency"], 0.002)
        self.assertTrue(info.kernel_streaming)
        self.assertEqual(info.requested_latency_ms, 2.0)

    def test_tied_wdm_ks_names_prefer_the_host_default_pin(self):
        sd = _FakeSoundDevice(include_wdm=True)
        self.assertEqual(
            resolve_wdm_ks_device(
                "output", samplerate=44100, _sd=sd
            ),
            5,
        )
        sd.hostapis[2]["default_output_device"] = 3
        self.assertIsNone(resolve_wdm_ks_device(
            "output", samplerate=44100, _sd=sd
        ))


class _FakeSynth:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.events = []
        self.deleted = False
        self.fail_render = False

    def sfload(self, path):
        self.events.append(("sfload", path))
        return 1

    def program_select(self, channel, sfid, bank, program):
        self.events.append(("program", channel, sfid, bank, program))

    def noteon(self, channel, pitch, velocity):
        self.events.append(("on", channel, pitch, velocity))

    def noteoff(self, channel, pitch):
        self.events.append(("off", channel, pitch))

    def cc(self, channel, control, value):
        self.events.append(("cc", channel, control, value))

    def get_samples(self, frames):
        if self.fail_render:
            raise RuntimeError("render failed")
        return np.full(int(frames) * 2, 1000, dtype=np.int16)

    def delete(self):
        self.deleted = True


class _FakeFluidSynth:
    def __init__(self):
        self.instances = []

    def Synth(self, **kwargs):
        synth = _FakeSynth(**kwargs)
        self.instances.append(synth)
        return synth


class FluidSynthWasapiSinkTests(unittest.TestCase):
    def test_output_auto_prefers_matching_wdm_ks(self):
        sd = _FakeSoundDevice(
            include_wdm=True,
            stream_latencies={
                ("output", 5): 0.003,
                ("output", 3): 0.022,
                ("output", None): 0.090,
            },
        )
        fluidsynth = _FakeFluidSynth()
        with tempfile.TemporaryDirectory() as directory:
            soundfont = Path(directory) / "test.sf2"
            soundfont.write_bytes(b"fake")
            sink = FluidSynthWasapiSink(
                soundfont,
                44100,
                128,
                _sd=sd,
                _fluidsynth=fluidsynth,
            )
            report = sink.diagnostics()[0]
            self.assertEqual(report["host_api"], "Windows WDM-KS")
            self.assertEqual(report["device_index"], 5)
            self.assertTrue(report["kernel_streaming"])
            self.assertEqual(report["block_size"], 128)
            sink.close()

    def test_events_are_rendered_in_output_callback_and_close_is_idempotent(self):
        sd = _FakeSoundDevice()
        fluidsynth = _FakeFluidSynth()
        with tempfile.TemporaryDirectory() as directory:
            soundfont = Path(directory) / "test.sf2"
            soundfont.write_bytes(b"fake")
            sink = FluidSynthWasapiSink(
                soundfont,
                44100,
                256,
                _sd=sd,
                _fluidsynth=fluidsynth,
            )
            sink.send(MidiEvent("note_on", 60, 100, 0))
            output = np.zeros((256, 2), dtype=np.float32)
            callback = sd.output_streams[-1].kwargs["callback"]
            callback(output, 256, None, False)
            self.assertIn(("on", 0, 60, 100), fluidsynth.instances[0].events)
            self.assertGreater(float(np.max(output)), 0.0)
            self.assertEqual(sink.diagnostics()[0]["host_api"], "Windows WASAPI")
            sink.close()
            sink.close()
            self.assertTrue(sd.output_streams[-1].closed)
            self.assertTrue(fluidsynth.instances[0].deleted)

    def test_persistent_render_failure_is_reported_as_unhealthy(self):
        sd = _FakeSoundDevice()
        fluidsynth = _FakeFluidSynth()
        with tempfile.TemporaryDirectory() as directory:
            soundfont = Path(directory) / "test.sf2"
            soundfont.write_bytes(b"fake")
            sink = FluidSynthWasapiSink(
                soundfont,
                44100,
                256,
                _sd=sd,
                _fluidsynth=fluidsynth,
            )
            fluidsynth.instances[0].fail_render = True
            callback = sd.output_streams[-1].kwargs["callback"]
            output = np.ones((256, 2), dtype=np.float32)
            for _ in range(3):
                callback(output, 256, None, False)
            self.assertTrue(np.all(output == 0.0))
            self.assertIn("ne rend plus de son", sink.health_error())
            sink.close()

    def test_repeated_portaudio_status_is_reported_as_unhealthy(self):
        sd = _FakeSoundDevice()
        fluidsynth = _FakeFluidSynth()
        with tempfile.TemporaryDirectory() as directory:
            soundfont = Path(directory) / "test.sf2"
            soundfont.write_bytes(b"fake")
            sink = FluidSynthWasapiSink(
                soundfont,
                44100,
                256,
                _sd=sd,
                _fluidsynth=fluidsynth,
            )
            callback = sd.output_streams[-1].kwargs["callback"]
            output = np.zeros((256, 2), dtype=np.float32)
            for _ in range(3):
                callback(output, 256, None, True)
            self.assertIn("incidents consecutifs", sink.health_error())
            for _ in range(16):
                callback(output, 256, None, False)
            self.assertIsNone(sink.health_error())
            sink.close()

    def test_intermittent_portaudio_status_is_reported_as_unstable(self):
        sd = _FakeSoundDevice()
        fluidsynth = _FakeFluidSynth()
        with tempfile.TemporaryDirectory() as directory:
            soundfont = Path(directory) / "test.sf2"
            soundfont.write_bytes(b"fake")
            sink = FluidSynthWasapiSink(
                soundfont,
                44100,
                256,
                _sd=sd,
                _fluidsynth=fluidsynth,
            )
            callback = sd.output_streams[-1].kwargs["callback"]
            output = np.zeros((256, 2), dtype=np.float32)
            for status in (True, False) * 4:
                callback(output, 256, None, status)
            self.assertIn("instable", sink.health_error())
            sink.close()


if __name__ == "__main__":
    unittest.main()
