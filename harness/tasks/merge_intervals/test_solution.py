"""Ground-truth tests for merge_intervals. Not shown to the model."""

from solution import merge_intervals


def test_empty():
    assert merge_intervals([]) == []


def test_no_overlap_sorted():
    assert merge_intervals([[1, 2], [4, 5]]) == [[1, 2], [4, 5]]


def test_unsorted_input():
    assert merge_intervals([[4, 5], [1, 2]]) == [[1, 2], [4, 5]]


def test_overlapping():
    assert merge_intervals([[1, 4], [2, 5]]) == [[1, 5]]


def test_touching_merges():
    assert merge_intervals([[1, 3], [3, 5]]) == [[1, 5]]


def test_nested():
    assert merge_intervals([[1, 10], [2, 3], [4, 5]]) == [[1, 10]]


def test_does_not_mutate_input():
    data = [[1, 4], [2, 5]]
    snapshot = [list(x) for x in data]
    merge_intervals(data)
    assert data == snapshot
