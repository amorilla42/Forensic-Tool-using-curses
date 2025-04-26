import curses
from .renderizable import Renderizable

class AwesomeInput(Renderizable):
    def render(self):
        input_win = curses.newwin(1, self.width // 2, self.height // 2, (self.width // 4))
        input_win.bkgd(' ', curses.color_pair(2))
        input_win.refresh()

        curses.echo()
        user_input = input_win.getstr(0, 0).decode("utf-8")
        curses.noecho()
        input_win.bkgd(' ', curses.color_pair(0))
        input_win.clear()
        input_win.refresh()

        return user_input
