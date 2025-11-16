from __future__ import annotations
from collections import deque
from typing import TYPE_CHECKING, Callable, Any
import threading

if TYPE_CHECKING:
    from browser.tab import Tab


class Task:
    """Represent a unit of work to be executed by the TaskRunner."""

    def __init__(self, task_code: Callable[..., Any], *args):
        self.task_code: Callable[..., Any] | None = task_code
        self.args: tuple | None = args

    def run(self):
        """Execute the task and clear references."""
        if self.task_code:
            self.task_code(*self.args)
            self.task_code = None
            self.args = None


class TaskRunner:
    """
    A simple task runner for a given browser tab.
    Tasks are executed in FIFO order.
    """

    def __init__(self, tab: Tab):
        self.tab = tab
        self.tasks: deque[Task] = deque()

        # Condition object providing:
        # - A lock to prevent multiple threads accessing the task queue simultaneously
        # - A wait/notify mechanism so threads can sleep until new tasks arrive
        self.condition = threading.Condition()

    def schedule_task(self, task: Task):
        """Add a task to the queue for later execution."""
        self.condition.acquire(blocking=True)
        self.tasks.append(task)
        self.condition.notify_all()  # Wake up waiting threads
        self.condition.release()

    def run(self):
        """Execute the next scheduled task."""
        task: Task | None = None
        self.condition.acquire(blocking=True)

        if len(self.tasks) > 0:
            task = self.tasks.popleft()

        self.condition.release()  # Release lock before running task
        if task:
            task.run()
