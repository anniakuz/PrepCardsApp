import pytest

from quiz.levels import apply_answer, candidate_levels
from quiz.models import TopicProgress


def progress(level=1):
    return TopicProgress(level=level, max_level=level)


def test_five_correct_in_a_row_raise_level():
    p = progress()
    assert [apply_answer(p, True) for _ in range(5)] == [None, None, None, None, "up"]
    assert p.level == 2 and p.max_level == 2 and p.correct_streak == 0


def test_three_wrong_in_a_row_lower_level():
    p = progress(3)
    assert [apply_answer(p, False) for _ in range(3)] == [None, None, "down"]
    assert p.level == 2 and p.max_level == 3


def test_a_hit_breaks_the_wrong_streak():
    p = progress(3)
    for correct in (False, False, True, False, False):
        assert apply_answer(p, correct) is None
    assert p.level == 3


def test_level_never_leaves_1_to_5():
    low, high = progress(1), progress(5)
    for _ in range(3):
        apply_answer(low, False)
        apply_answer(high, True)
    assert low.level == 1 and high.level == 5


def test_candidate_levels_prefer_lower_neighbour():
    assert candidate_levels(3) == [3, 2, 4, 1, 5]
    assert candidate_levels(1) == [1, 2, 3, 4, 5]
