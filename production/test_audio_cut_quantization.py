"""Copied AAC accepts only the deterministic sample-grid origin, never loose sync."""

from fractions import Fraction
import unittest

from verify_preview import packet_timing_matches, quantized_audio_origin


class AudioCutQuantizationTests(unittest.TestCase):
    def test_zero_and_exact_tick_origins_unchanged(self):
        tb = Fraction(1, 44100)
        self.assertEqual(quantized_audio_origin(Fraction(0), tb), 0)
        self.assertEqual(quantized_audio_origin(Fraction(54), tb), 54)

    def test_observed_dance_and_raised_origins(self):
        tb = Fraction(1, 44100)
        self.assertEqual(quantized_audio_origin(Fraction(33833, 1000), tb), 1492035 * tb)
        self.assertEqual(quantized_audio_origin(Fraction(51042, 1000), tb), 2250952 * tb)
        self.assertEqual((quantized_audio_origin(Fraction(33833, 1000), tb) -
                          Fraction(33833, 1000)) / tb, Fraction(-3, 10))

    def test_round_up_and_half_tick_are_deterministic(self):
        tb = Fraction(1, 44100)
        self.assertEqual(quantized_audio_origin(Fraction(18, 10) * tb, tb), 2 * tb)
        self.assertEqual(quantized_audio_origin(Fraction(3, 2) * tb, tb), 2 * tb)

    def test_every_packet_has_exact_shift_and_duration(self):
        tb = Fraction(1, 44100)
        origin = quantized_audio_origin(Fraction(33833, 1000), tb)
        for index in range(4):
            source = {"pts": 1446912 + index * 1024, "dts": 1446912 + index * 1024,
                      "duration": 1024}
            actual = {"pts": source["pts"] - 1492035, "dts": source["dts"] - 1492035,
                      "duration": 1024}
            self.assertTrue(packet_timing_matches(actual, source, tb, tb, origin))
            for key in ("pts", "dts", "duration"):
                altered = {**actual, key: actual[key] + 1}
                self.assertFalse(packet_timing_matches(altered, source, tb, tb, origin))

    def test_invalid_origins_rejected(self):
        for origin, tb in [(Fraction(-1), Fraction(1, 44100)), (Fraction(0), Fraction(0))]:
            with self.assertRaises(ValueError):
                quantized_audio_origin(origin, tb)


if __name__ == "__main__":
    unittest.main()
