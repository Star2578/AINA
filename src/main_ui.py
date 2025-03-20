from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QApplication, QToolButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QCursor
from src.model_viewer import ModelViewer
from src.interfaces.customizer import Customizer
from src.interfaces.settings import Settings
from utils.pos import place_at, vw, vh
import json
import os

class AINA(QWidget):
    def __init__(self):
        super().__init__()
        self.config_file = "config.json"
        # self.default_model_path = "assets/models/Karelia/Karelia.gltf"
        self.default_model_path = "assets/models/tau/Tau_Mpct9yh.gltf"
        self.viewer = None
        self.drag_area_height = 20
        
        self.load_config()

        self.setWindowTitle("AINA - Desktop Pet")
        self.setFixedSize(self.config["width"], self.config["height"])
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setMouseTracking(True)
        
        self.init_ui()
        self.move(self.config.get("pos_x", vw(70)), self.config.get("pos_y", vh(70)))
        
        self.customizer = Customizer(self.viewer)
        self.settings = Settings(self)
        self.old_pos = None

    def init_ui(self):
        """Initialize the UI elements."""
        main_layout = QHBoxLayout()

        # Draggable area (top bar)
        self.drag_area = QWidget(self)
        self.drag_area.setFixedHeight(self.drag_area_height)
        self.drag_area.setAutoFillBackground(True)  # Ensures background color is applied
        self.drag_area.setStyleSheet("background-color: rgba(50, 50, 50, 255);")  # Ensure full opacity

        main_layout.addWidget(self.drag_area)
        
        content_layout = QHBoxLayout()

        self.viewer = ModelViewer(self.config.get("model_path", self.default_model_path), 
                                self.config.get("part_visibility", {}))
        
        if "part_visibility" in self.config:
            self.viewer.part_visibility.update(self.config["part_visibility"])

        main_layout.addWidget(self.viewer, stretch=2)
        
        # Buttons (Right)
        button_layout = QVBoxLayout()
        
        # Exit Button
        self.exit_button = QToolButton()
        self.exit_button.setIcon(QIcon("assets/icons/exit.png"))
        self.exit_button.setToolTip("Exit AINA")
        self.exit_button.clicked.connect(self.close)

        # Customize Button
        self.customize_button = QToolButton()
        self.customize_button.setIcon(QIcon("assets/icons/custom.png"))
        self.customize_button.setToolTip("Customize Model")
        self.customize_button.clicked.connect(self.open_customizer)
        
        # Setting Button
        self.setting_button = QToolButton()
        self.setting_button.setIcon(QIcon("assets/icons/cog.png"))
        self.setting_button.setToolTip("Settings")
        self.setting_button.clicked.connect(self.open_settings)

        # Add buttons to layout
        button_layout.addWidget(self.customize_button)
        button_layout.addWidget(self.setting_button)
        button_layout.addWidget(self.exit_button)
        button_layout.addStretch()
        
        content_layout.addLayout(button_layout)
        main_layout.addLayout(content_layout)

        self.setLayout(main_layout)
        self.setMinimumSize(200, 200 + self.drag_area_height)

    def load_config(self):
        """Load settings from config file, using defaults if not found."""
        self.config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    self.config = json.load(f)
                print(f"Loaded config from {self.config_file}")
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
        else:
            print(f"No config file found at {self.config_file}. Initializing with defaults.")

        self.config.setdefault("width", vw(30))
        self.config.setdefault("height", vh(30))
        self.config.setdefault("model_path", self.default_model_path)
        self.config.setdefault("part_visibility", {})
        self.config.setdefault("allow_overflow", False)
        self.config.setdefault("pos_x", vw(70))
        self.config.setdefault("pos_y", vh(70))

        if not os.path.exists(self.config_file):
            self.save_config()
            print(f"Created new config file with defaults at {self.config_file}")

    def save_config(self):
        """Save settings to config file."""
        self.config["width"] = self.width()
        self.config["height"] = self.height()
        self.config["model_path"] = self.viewer.model_path if self.viewer else self.default_model_path
        self.config["part_visibility"] = self.viewer.part_visibility if self.viewer else {}
        self.config["pos_x"] = self.x()
        self.config["pos_y"] = self.y()
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def closeEvent(self, event):
        """Override close event to save config."""
        self.save_config()
        super().closeEvent(event)

    def open_settings(self):
        """Open AINA settings interface."""
        if self.settings is None or not self.settings.isVisible():
            self.settings = Settings(self)
            self.settings.show()
        else:
            self.settings.raise_()
    
    def open_customizer(self):
        """Open the model customization interface."""
        if self.customizer is None or not self.customizer.isVisible():
            self.customizer = Customizer(self.viewer)
            self.customizer.show()
        else:
            self.customizer.raise_()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().y() < self.drag_area_height:
                self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            new_pos = self.pos() + delta
            if not self.config["allow_overflow"]:
                screen = QApplication.primaryScreen().availableGeometry()
                new_pos.setX(max(0, min(new_pos.x(), screen.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), screen.height() - self.height())))
            self.move(new_pos)
            self.old_pos = event.globalPosition().toPoint()

        # Fix cursor update logic
        cursor_y = int(event.position().y())  # Ensure integer value
        if cursor_y < self.drag_area_height:
            self.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        else:
            self.unsetCursor()
        
    def mouseReleaseEvent(self, event):
        self.old_pos = None
        # Reset cursor after dragging
        if event.position().y() >= self.drag_area_height:
            self.unsetCursor()

    def leaveEvent(self, event):
        self.unsetCursor()