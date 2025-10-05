from __future__ import annotations
import abc
import tkinter

from browser.html_parser.nodes import Text, Element


class BaseDrawCommand(abc.ABC):
    """Abstract base class for drawing commands"""

    top: float
    left: float
    bottom: float

    @abc.abstractmethod
    def execute(self, scroll: float, canvas: tkinter.Canvas) -> None:
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
            raise ValueError(self.__not_computed_message("x"))
        return self._x

    @property
    def y(self) -> float:
        if self._y is None:
            raise ValueError(self.__not_computed_message("y"))
        return self._y

    @property
    def width(self) -> float:
        if self._width is None:
            raise ValueError(self.__not_computed_message("Width"))
        return self._width

    @property
    def height(self) -> float:
        if self._height is None:
            raise ValueError(self.__not_computed_message("Height"))
        return self._height

    def __not_computed_message(self, field: str) -> str:
        return f"{field} has not been computed. Call layout() first."
