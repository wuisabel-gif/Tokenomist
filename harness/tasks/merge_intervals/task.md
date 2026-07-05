# Task: merge overlapping intervals

Implement `merge_intervals(intervals)` in `solution.py`.

- Input: a list of `[start, end]` pairs (integers), in any order. `start <= end`
  for each pair.
- Output: a new list of non-overlapping `[start, end]` pairs that cover exactly
  the same points, sorted by `start` ascending.
- Intervals that merely touch, such as `[1, 3]` and `[3, 5]`, count as
  overlapping and must be merged into `[1, 5]`.
- An empty input returns an empty list.
- Do not mutate the input list.

Keep the public function name and signature exactly as `merge_intervals(intervals)`.
