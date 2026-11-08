"""A scheduled task's files are named by its id only: an id that could leave the store's folder
(a backslash on Windows, a slash, a dot) is not a task id."""

from __future__ import annotations

from pathlib import Path

import pytest

from coscribe.tools.bookkeeping.folder_watch import FolderWatch
from coscribe.tools.bookkeeping.scheduled_tasks import ScheduledTriggerStore
from coscribe.tools.bookkeeping.task_memory import TaskMemory
from coscribe.tools.bookkeeping.task_versions import TaskVersions

LEAVING = ["..\\..\\secret", "../secret", "a/b", "..", "x.y", "", "a" * 65]


@pytest.mark.parametrize("bad", LEAVING)
def test_an_id_that_could_leave_the_folder_is_refused_by_every_task_store(
    tmp_path: Path, bad: str
) -> None:
    store = ScheduledTriggerStore(tmp_path)
    assert store.load(bad) is None
    assert store.delete(bad) is False
    for other in (TaskVersions(tmp_path), TaskMemory(tmp_path)):
        with pytest.raises(ValueError, match="is not a task id"):
            other.delete(bad)
    with pytest.raises(ValueError, match="is not a task id"):
        FolderWatch(tmp_path).forget(bad)


def test_the_ids_coscribe_makes_and_tests_use_are_task_ids(tmp_path: Path) -> None:
    store = ScheduledTriggerStore(tmp_path)
    for good in ("3f9a0c1b2d4e", "t1", "trig-1", "does_not_exist"):
        assert store.load(good) is None
        assert store.delete(good) is False
