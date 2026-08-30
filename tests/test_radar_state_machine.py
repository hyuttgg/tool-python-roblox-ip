# -*- coding: utf-8 -*-
"""
Unit Tests for Radar State Machine and Anomaly Scorer
Kiểm tra các trạng thái chuyển đổi: NOT_RUNNING -> STARTING -> RUNNING -> FROZEN / CRASHED / DISCONNECTED.
"""

import unittest
from monitoring.radar.state_machine import StateTracker, RobloxState
from monitoring.radar.anomaly_scorer import AnomalyScorer


class TestRadarStateMachine(unittest.TestCase):

    def test_state_transitions_lifecycle(self):
        tracker = StateTracker("ROBLOX-TAG-TEST")
        self.assertEqual(tracker.state, RobloxState.NOT_RUNNING)

        # 1. Phát hiện process -> STARTING
        st = tracker.update(process_alive=True, anomaly_score=0, triggered_signals=[], severity="NORMAL")
        self.assertEqual(st, RobloxState.STARTING)

        # 2. Sau 3 chu kỳ ổn định -> RUNNING
        for _ in range(3):
            st = tracker.update(process_alive=True, anomaly_score=5, triggered_signals=[], severity="NORMAL")
        self.assertEqual(st, RobloxState.RUNNING)

        # 3. Mất kết nối (log disconnect) -> DISCONNECTED
        st = tracker.update(process_alive=True, anomaly_score=45, triggered_signals=["log_disconnect"], severity="SUSPICIOUS")
        self.assertEqual(st, RobloxState.DISCONNECTED)

        # 4. Tiến trình biến mất đột ngột -> CRASHED
        st = tracker.update(process_alive=False, anomaly_score=80, triggered_signals=["process_dead"], severity="CRITICAL")
        self.assertEqual(st, RobloxState.CRASHED)

    def test_anomaly_scorer(self):
        scorer = AnomalyScorer()
        
        # Kết quả bình thường
        dummy_filter_res = {
            "cpu": {"raw": 20, "filtered": 20, "cfar_anomaly": False, "mti_delta": 0.5},
            "ram": {"raw": 500, "filtered": 500, "cfar_anomaly": False, "mti_delta": 1.0},
            "ping": {"raw": 45, "filtered": 45, "cfar_anomaly": False, "mti_delta": 0.2},
            "fps": {"raw": 60, "filtered": 60, "cfar_anomaly": False, "mti_delta": 0.0},
        }
        res_normal = scorer.evaluate(dummy_filter_res, process_alive=True)
        self.assertLess(res_normal.score, 20)
        self.assertEqual(res_normal.severity, "NORMAL")

        # Kết quả phát hiện Byfron Kick / Disconnect
        res_kick = scorer.evaluate(dummy_filter_res, process_alive=True, log_disconnect=True)
        self.assertGreaterEqual(res_kick.score, 40)
        self.assertIn("log_disconnect", res_kick.triggered_signals)


if __name__ == "__main__":
    unittest.main()
