from .ui_handler import UIHandler

class Renderizable:
    """
    Interface for renderable objects.
    """

    def __init__(self, win=None):
        """
        Initialize the Renderizable object.

        Args:
            win: The window to render in. If None, use the default window.
        """
        self.win = win if win else UIHandler().stdscr
        self.height, self.width = self.win.getmaxyx()

    def render(self) -> str:
        """
        Render the object to a string.

        Returns:
            str: The rendered string.
        """
        raise NotImplementedError("Subclasses must implement this method.")
    
    def clear(self) -> None:
        """
        Clear the rendered object from the window.
        """
        self.win.clear()
        self.win.refresh()
