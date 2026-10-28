from abc import ABC, abstractmethod

from .console_interface.console_ui_context import ConsoleUIContext

def _create_console_interface():
    from .console_interface.console_interface import ConsoleInterface

    return ConsoleInterface()


ui_mapping = {"console": _create_console_interface}

class UserInterface(ABC):
    def __init__(self):
        self.ui_context = ConsoleUIContext(user_interface=self)

    @abstractmethod
    def handle_input(self, key: str):
        pass

    @abstractmethod
    def render(self):
        pass

    @abstractmethod
    def run(self):
        pass