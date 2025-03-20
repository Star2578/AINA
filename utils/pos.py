from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect

def get_screen_size():
    """Returns the screen width and height as a tuple (width, height)."""
    screen = QApplication.primaryScreen()
    screen_rect = screen.geometry()
    return screen_rect.width(), screen_rect.height()

def vh(percent: float):
    """Convert percentage (like 10vh) into pixel height."""
    screen_height = get_screen_size()[1]
    return int(screen_height * (percent / 100))

def vw(percent: float):
    """Convert percentage (like 10vw) into pixel width."""
    screen_width = get_screen_size()[0]
    return int(screen_width * (percent / 100))

def place_at(widget, x_percent: float, y_percent: float):
    """Move widget to a position relative to the screen size (like absolute positioning in CSS)."""
    x = vw(x_percent)
    y = vh(y_percent)
    widget.move(x, y)
