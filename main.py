from PyQt6.QtWidgets import QApplication, QWidget, QProgressBar, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from src.main_ui import AINA
import sys

class LoadingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading AINA")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        
        layout = QVBoxLayout()
        
        title = QLabel("AINA")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        self.log_display = QTextEdit(self)
        self.log_display.setReadOnly(True)
        self.log_display.setFixedHeight(200)
        layout.addWidget(self.log_display)
        
        self.setLayout(layout)
        
    def write(self, text):
        self.log_display.append(text.strip())
        QApplication.processEvents()
        
    def update_progress(self, value, message=""):
        self.progress.setValue(value)
        if message:
            self.write(message)
        QApplication.processEvents()

def load_stylesheet():
    with open("styles/main.qss", "r") as f:
        return f.read()

def main():
    app = QApplication(sys.argv)
    
    app.setStyleSheet(load_stylesheet())
    
    loading = LoadingWindow()
    loading.show()
    
    window = AINA()
    window.progress_updated.connect(loading.update_progress)
    
    # Show AINA and close loading window when complete
    loading.update_progress(100, "Launching AINA...")  # Ensure 100% is reached
    window.show()
    loading.close()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()