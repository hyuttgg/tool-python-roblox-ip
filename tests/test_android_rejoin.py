# -*- coding: utf-8 -*-
"""
Unit tests for Android Roblox Rejoin Engine (DroidBlox Architecture)
Using standard unittest framework.
"""

import unittest
import time
from devices.android_rejoin import (
    LogcatPatterns,
    AndroidRobloxWatcher,
    AndroidRejoinController,
    RejoinState,
    RobloxSessionInfo
)


class TestAndroidRejoin(unittest.TestCase):

    def test_logcat_patterns_joining_game(self):
        line = "[FLog::Output] ! Joining game '7a8b9c0d-1234-5678-90ab-cdef12345678' place 2753915549 at 128.116.50.2"
        match = LogcatPatterns.GAME_JOINING.search(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "7a8b9c0d-1234-5678-90ab-cdef12345678")
        self.assertEqual(match.group(2), "2753915549")
        self.assertEqual(match.group(3), "128.116.50.2")

    def test_logcat_patterns_universe_and_user(self):
        line = "[FLog::GameJoinLoadTime] Report game_join_loadtime: ... userid:123456789, ... universeid:987654321"
        match = LogcatPatterns.GAME_JOINING_UNIVERSE.search(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "123456789")
        self.assertEqual(match.group(2), "987654321")

    def test_logcat_patterns_udmux(self):
        line = "[FLog::Network] UDMUX Address = 128.116.100.5"
        match = LogcatPatterns.GAME_JOINING_UDMUX.search(line)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "128.116.100.5")

    def test_logcat_patterns_disconnect(self):
        line = "[FLog::Network] Time to disconnect replication data: 12ms. Error Code: 277"
        self.assertIn(LogcatPatterns.GAME_DISCONNECTED_KEYWORD, line)
        match_err = LogcatPatterns.ERROR_CODE_PATTERN.search(line)
        self.assertIsNotNone(match_err)
        self.assertEqual(match_err.group(1), "277")

    def test_watcher_event_flow(self):
        events = []

        def on_event(name, data):
            events.append((name, data))

        watcher = AndroidRobloxWatcher(on_event_callback=on_event)

        # 1. Evaluate join line
        join_line = "[FLog::Output] ! Joining game '11112222-3333-4444-5555-666677778888' place 13772394625 at 10.0.0.1"
        watcher.evaluate_line(join_line)
        self.assertEqual(watcher.session.place_id, 13772394625)
        self.assertEqual(watcher.session.job_id, "11112222-3333-4444-5555-666677778888")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], "GAME_JOINING")

        # 2. Evaluate serverId (Joined)
        joined_line = "[FLog::Network] serverId: 12345"
        watcher.evaluate_line(joined_line)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[1][0], "GAME_JOINED")

        # 3. Evaluate Disconnect
        dc_line = "[FLog::Network] Time to disconnect replication data: 5ms"
        watcher.evaluate_line(dc_line)
        self.assertEqual(len(events), 3)
        self.assertEqual(events[2][0], "GAME_DISCONNECTED")

    def test_intent_command_builder(self):
        controller = AndroidRejoinController(
            default_place_id=2753915549,
            default_job_id="test-job-id",
            user_slot=999,
            adb_bin="/usr/bin/adb",
            device_id="emulator-5554"
        )

        cmd = controller.build_launch_intent_cmd()
        self.assertIn("/usr/bin/adb", cmd)
        self.assertIn("-s", cmd)
        self.assertIn("emulator-5554", cmd)
        self.assertIn("shell", cmd)
        self.assertIn("--user", cmd)
        self.assertIn("999", cmd)
        self.assertIn("-n", cmd)
        self.assertIn("com.roblox.client/com.roblox.client.ActivityProtocolLaunch", cmd)
        
        # Verify URI contains placeId and gameInstanceId
        d_index = cmd.index("-d")
        uri = cmd[d_index + 1]
        self.assertIn("roblox://experiences/start?placeId=2753915549", uri)
        self.assertIn("gameInstanceId=test-job-id", uri)

    def test_circuit_breaker_logic(self):
        controller = AndroidRejoinController(
            default_place_id=2753915549,
            max_consecutive_fails=2,
            circuit_cooldown_sec=1
        )

        self.assertEqual(controller.consecutive_fails, 0)

        # Simulate 1 fail
        controller.consecutive_fails = 1
        controller.state = RejoinState.IN_GAME

        # Event game joined resets fails
        controller._handle_watcher_event("GAME_JOINED", {})
        self.assertEqual(controller.consecutive_fails, 0)
        self.assertEqual(controller.state, RejoinState.IN_GAME)


if __name__ == "__main__":
    unittest.main()
