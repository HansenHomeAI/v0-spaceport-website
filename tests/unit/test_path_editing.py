"""Mirror path segment math from `pathEditing.ts` / `pathAnimation.ts` for regression checks."""

import unittest


def path_segment_count(checkpoint_count: int, loop: bool) -> int:
    if checkpoint_count < 2:
        return 0
    return checkpoint_count if loop else checkpoint_count - 1


class TestPathSegmentCount(unittest.TestCase):
    def test_loop_vs_line(self):
        self.assertEqual(path_segment_count(10, True), 10)
        self.assertEqual(path_segment_count(10, False), 9)

    def test_minimum(self):
        self.assertEqual(path_segment_count(1, True), 0)
        self.assertEqual(path_segment_count(0, False), 0)


if __name__ == "__main__":
    unittest.main()
