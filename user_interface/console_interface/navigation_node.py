from abc import ABC, abstractmethod

from .focus_area import FocusArea
from .console_ui_context import ConsoleUIContext

class NavigationNode(ABC):
    def __init__(self, context: ConsoleUIContext):
        self.context = context

    @property
    @abstractmethod
    def focus_area(self) -> FocusArea:
        pass

    def handle_input(self, key: str):
        pass