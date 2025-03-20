from PyQt6.QtWidgets import QApplication
from src.main_ui import AINA
import sys

def load_stylesheet():
    with open("styles/main.qss", "r") as f:
        return f.read()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Load QSS stylesheet
    app.setStyleSheet(load_stylesheet())

    window = AINA()
    window.show()
    sys.exit(app.exec())
