from __future__ import annotations
import abc
import skia

from browser.html.nodes import Text, Element


class BaseDrawCommand(abc.ABC):
    """Abstract base class for drawing commands"""
    rect: skia.Rect

    @abc.abstractmethod
    def execute(self, canvas: skia.Canvas) -> None:
        """Draw onto the canvas"""
        ...


class BaseLayout(abc.ABC):
    """Abstract base class for layout objects."""

    node: Text | Element
    parent: BaseLayout | None
    previous: BaseLayout | None
    children: list[BaseLayout]

    def __init__(self):
        self._x: float | None = None
        self._y: float | None = None
        self._width: float | None = None
        self._height: float | None = None

    @abc.abstractmethod
    def layout(self) -> None:
        """Compute display info and recursively layout children."""
        ...

    @abc.abstractmethod
    def paint(self) -> list[BaseDrawCommand]:
        """Return drawing commands (display list) for this layout."""
        ...

    @property
    def x(self) -> float:
        if self._x is None:
            raise Exception(self.__not_computed_message("x"))
        return self._x

    @property
    def y(self) -> float:
        if self._y is None:
            raise Exception(self.__not_computed_message("y"))
        return self._y

    @property
    def width(self) -> float:
        if self._width is None:
            raise Exception(self.__not_computed_message("Width"))
        return self._width

    @property
    def height(self) -> float:
        if self._height is None:
            raise Exception(self.__not_computed_message("Height"))
        return self._height

    def __not_computed_message(self, field: str) -> str:
        return f"{field} has not been computed. Call layout() first."

    def should_paint(self) -> bool:
        """Whether to collect draw commands from current layout."""
        return True