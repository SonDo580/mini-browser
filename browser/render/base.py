import abc
import skia


class BaseDrawCommand(abc.ABC):
    """Abstract base class for drawing commands"""

    rect: skia.Rect

    @abc.abstractmethod
    def execute(self, canvas: skia.Canvas) -> None:
        """Draw onto the canvas"""
        ...
