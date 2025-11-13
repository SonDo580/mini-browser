from collections import deque
from typing import TYPE_CHECKING, Callable, Any

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

    def schedule_task(self, task: Task):
        """Add a task to the queue for later execution."""
        self.tasks.append(task)

    def run(self):
        """Execute the next scheduled task."""
        if len(self.tasks) > 0:
            task = self.tasks.popleft()
            task.run()
