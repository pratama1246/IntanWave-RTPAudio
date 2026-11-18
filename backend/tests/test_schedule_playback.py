import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from app.audio_engine import AudioEngine


class SchedulePlaybackTests(unittest.TestCase):
    def setUp(self):
        self.engine = AudioEngine()
        self.monitor = self.engine._monitor_session
        self.audio_path = str(Path(__file__).resolve())
        self.settings = {"multicast_ip": "239.255.0.1", "multicast_port": "5004"}
        self.enterContext(patch("app.audio_engine.get_settings", return_value=self.settings))
        self.enterContext(patch("app.audio_engine.log_event"))
        self.enterContext(patch("app.audio_engine.subprocess.Popen"))
        self.enterContext(patch.object(self.engine, "_monitor_session"))
        self.enterContext(patch.object(self.engine, "get_audio_duration", return_value=5))
        self.addCleanup(self.engine.stop)

    def play(self, title, endpoints, **options):
        return self.engine.play(
            self.audio_path, title, target_endpoints=endpoints, is_manual=False, **options
        )

    def test_simultaneous_unicast_plays_in_parallel(self):
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(self.play, "A", ["192.0.2.1:5004"], enable_multicast=True)
            second = executor.submit(self.play, "B", ["192.0.2.2:5004"], enable_multicast=True)
            self.assertEqual([first.result()["status"], second.result()["status"]],
                             ["STREAMING", "STREAMING"])
        self.assertEqual(len(self.engine.active_sessions), 2)
        self.assertEqual(self.engine.playback_queue, [])

    def test_overlap_waits_then_starts_when_the_active_schedule_finishes(self):
        first = self.play("A", ["192.0.2.1:5004", "192.0.2.2:5004"])
        second = self.play("B", ["192.0.2.2:5004"], category="safety")
        self.assertEqual(second["status"], "QUEUED")
        self.assertEqual(list(self.engine.active_sessions), [first["session_id"]])

        with patch("app.audio_engine.time.sleep"):
            self.monitor(self.engine.active_sessions[first["session_id"]])

        self.assertEqual([s.title for s in self.engine.active_sessions.values()], ["B"])
        self.assertEqual(self.engine.playback_queue, [])

    def test_multicast_and_shared_local_output_each_require_a_queue(self):
        self.play("A", ["192.0.2.1:5004"], enable_local=True)
        self.assertEqual(self.play("B", ["239.255.0.1:5004"])["status"], "QUEUED")
        self.assertEqual(
            self.play("C", ["192.0.2.2:5004"], enable_local=True)["status"], "QUEUED"
        )
