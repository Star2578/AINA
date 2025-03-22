from PyQt6.QtWidgets import QApplication, QWidget, QProgressBar, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from src.main_ui import AINA
import sys
import io

class LoadingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading AINA")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        
        # Layout
        layout = QVBoxLayout()
        
        title = QLabel()
        title.setText("AINA")
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
            }                   
        """)
        layout.addWidget(title)
        
        # Progress bar
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        
        # Log display
        self.log_display = QTextEdit(self)
        self.log_display.setReadOnly(True)
        self.log_display.setFixedHeight(200)
        layout.addWidget(self.log_display)
        
        self.setLayout(layout)
        
        # Redirect stdout to log display
        self.stdout = sys.stdout
        sys.stdout = self
        
    def write(self, text):
        """Capture print statements and append to log display."""
        self.log_display.append(text.strip())
        QApplication.processEvents()
        
    def flush(self):
        """Required for stdout compatibility."""
        pass
        
    def closeEvent(self, event):
        """Restore stdout when closing."""
        sys.stdout = self.stdout
        super().closeEvent(event)
        
    def update_progress(self, value, message=""):
        """Update progress bar and log a message."""
        self.progress.setValue(value)
        if message:
            self.write(message)
        QApplication.processEvents()

def load_stylesheet():
    with open("styles/main.qss", "r") as f:
        return f.read()

def main():
    app = QApplication(sys.argv)
    
    # Load QSS stylesheet
    app.setStyleSheet(load_stylesheet())
    
    # Show loading window
    loading = LoadingWindow()
    loading.show()
    
    # Create AINA instance once
    window = AINA()
    
    # Simulate loading steps
    steps = [
        (20, "Initializing application..."),
        (40, "Loading configuration..."),
        (60, "Setting up model viewer..."),
        (80, "Finalizing UI..."),
        (100, "Complete!")
    ]
    current_step = 0
    
    timer = QTimer()
    
    def load_step():
        nonlocal current_step
        if current_step < len(steps):
            value, message = steps[current_step]
            loading.update_progress(value, message)
            current_step += 1
        else:
            # Stop the timer and finalize
            timer.stop()
            window.show()
            loading.close()
    
    timer.timeout.connect(load_step)
    timer.start(500)  # 500ms delay per step
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()