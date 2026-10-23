# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.weibao.cram_mode import CramSession, split_sides


def ids(*n: int) -> list:
    return list(n)


def test_known_removes_and_again_requeues():
    s = CramSession(ids(1, 2, 3), shuffle=False)
    s.mark_again()
    assert list(s.queue) == ids(2, 3, 1)
    s.mark_known()
    s.mark_known()
    s.mark_known()
    assert s.done and s.known == 3 and s.missed == {1}


def test_undo_restores_order():
    s = CramSession(ids(1, 2, 3), shuffle=False)
    s.mark_again()
    s.mark_known()
    assert s.undo() and s.undo()
    assert list(s.queue) == ids(1, 2, 3) and s.known == 0
    assert not s.undo()


def test_split_sides():
    assert split_sides("Q", "Q<hr id=answer>A") == ("Q", "A")
    assert split_sides("Q", "plain") == ("Q", "plain")
