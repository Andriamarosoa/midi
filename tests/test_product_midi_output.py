import unittest

from src.product.decoder import MidiEvent
from src.product.midi_output import CompositeMidiSink, MidiSink


class RecordingSink(MidiSink):
    def __init__(self):
        self.events = []
        self.panics = 0
        self.closes = 0

    def send(self, event):
        self.events.append(event)

    def panic(self):
        self.panics += 1

    def close(self):
        self.closes += 1


class FailingSink(RecordingSink):
    def panic(self):
        super().panic()
        raise RuntimeError("panic failed")

    def close(self):
        super().close()
        raise RuntimeError("close failed")


class CompositeMidiSinkTests(unittest.TestCase):
    def test_fans_out_and_closes_once(self):
        first = RecordingSink()
        second = RecordingSink()
        sink = CompositeMidiSink(first, second)
        event = MidiEvent("note_on", 60, 100, 0)

        sink.send(event)
        sink.panic()
        sink.close()
        sink.close()

        self.assertEqual(first.events, [event])
        self.assertEqual(second.events, [event])
        self.assertEqual(first.panics, 1)
        self.assertEqual(second.panics, 1)
        self.assertEqual(first.closes, 1)
        self.assertEqual(second.closes, 1)

    def test_cleanup_attempts_every_sink_after_one_failure(self):
        failing = FailingSink()
        healthy = RecordingSink()
        sink = CompositeMidiSink(healthy, failing)

        with self.assertRaisesRegex(RuntimeError, "panic failed"):
            sink.panic()
        self.assertEqual(healthy.panics, 1)
        self.assertEqual(failing.panics, 1)

        with self.assertRaisesRegex(RuntimeError, "close failed"):
            sink.close()
        self.assertEqual(healthy.closes, 1)
        self.assertEqual(failing.closes, 1)


if __name__ == "__main__":
    unittest.main()
