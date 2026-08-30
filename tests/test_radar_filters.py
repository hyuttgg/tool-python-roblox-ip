# -*- coding: utf-8 -*-
"""
Unit Tests for Radar Signal Processing Filters
Kiểm tra hoạt động của KalmanFilter, CFARDetector, MTIFilter và FilterBank.
"""

import unittest
from monitoring.radar.filters import KalmanFilter, CFARDetector, MTIFilter, FilterBank


class TestRadarFilters(unittest.TestCase):

    def test_kalman_filter_smoothing(self):
        kf = KalmanFilter(process_noise=0.01, measurement_noise=1.0)
        measurements = [42, 45, 43, 300] + [45] * 20
        smoothed = [kf.update(m) for m in measurements]
        
        # Spike 300 phải bị làm mượt xuống dưới 120 ngay tại thời điểm spike
        self.assertLess(smoothed[3], 120.0)
        # Giá trị sau khi chuỗi ổn định trở lại phải hội tụ về mức trung bình ~45
        self.assertTrue(40.0 <= smoothed[-1] <= 55.0)



    def test_cfar_anomaly_detection(self):
        cfar = CFARDetector(window_size=10, guard_cells=1, multiplier=2.5)
        normal_samples = [30, 31, 32, 29, 30, 31, 28, 30, 32, 31]
        for s in normal_samples:
            is_anomaly, _ = cfar.update(s)
            self.assertFalse(is_anomaly)

        is_anomaly, threshold = cfar.update(150.0)
        self.assertTrue(is_anomaly)
        self.assertLess(threshold, 150.0)

    def test_mti_filter_change_detection(self):
        mti = MTIFilter(alpha=0.4)
        for _ in range(5):
            d = mti.update(30.0)
        self.assertLess(d, 1.0)

        d_jump = mti.update(95.0)
        self.assertGreater(d_jump, 15.0)

    def test_filter_bank_multichannel(self):
        fb = FilterBank()
        res = None
        for _ in range(5):
            res = fb.process(cpu=25.0, ram=800.0, ping=45.0, fps=60.0)
            
        self.assertIn("cpu", res)
        self.assertIn("ram", res)
        self.assertIn("ping", res)
        self.assertIn("fps", res)
        self.assertAlmostEqual(res["fps"]["filtered"], 60.0, delta=5.0)


if __name__ == "__main__":
    unittest.main()
