from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QApplication, QToolButton, QLineEdit, QDialog, QTextBrowser, QTextEdit
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation
from PyQt6.QtGui import QIcon, QCursor
from src.llm.llm import LLM
from src.model_viewer import ModelViewer
from src.interfaces.customizer import Customizer
from src.interfaces.settings import Settings
from utils.pos import place_at, vw, vh
import json
import os

class AINA(QWidget):

    progress_updated = pyqtSignal(int, str)
    
    def __init__(self):
        super().__init__()
        self.config_file = "config.json"
        self.default_model_path = "assets/models/king_triton/scene.gltf"
        self.viewer = None
        self.drag_area_size = 30
        self.chat_history = []
        
        self.progress_updated.emit(20, "Initializing application...")
        self.load_config()

        self.setWindowTitle("AINA - Desktop Pet")
        self.setFixedSize(self.config["width"], self.config["height"])
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setMouseTracking(True)
        
        self.progress_updated.emit(60, "Setting up UI...")
        self.init_ui()
        self.progress_updated.emit(80, "Positioning window...")
        self.move(self.config.get("pos_x", vw(70)), self.config.get("pos_y", vh(70)))
        
        self.progress_updated.emit(90, "Initializing customizer and settings...")
        self.customizer = Customizer(self.viewer)
        self.settings = Settings(self)
        self.old_pos = None
        self.is_dragging = False
        
        self.progress_updated.emit(100, "Initialization complete!")

    def init_ui(self):
        """Initialize the UI elements."""
        outer_layout = QVBoxLayout()
        main_layout = QHBoxLayout()
    
        # Draggable area (button)
        self.drag_area = QPushButton(self)
        self.drag_area.setIcon(QIcon("assets/icons/drag.png"))
        self.drag_area.setFixedSize(self.drag_area_size, self.drag_area_size)
        self.drag_area.setStyleSheet("""
            QPushButton {
                background-color: #ff5733;
                color: white;
                border-radius: 10px;
                font-size: 16px;
                padding: 8px 8px;
            }
            QPushButton:pressed {
                background-color: #ff8566;
            }
        """)
        self.drag_area.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.drag_area.pressed.connect(self.start_drag)
        
        outer_layout.addWidget(self.drag_area)
        
        # Chat system (Left)
        chat_layout = QVBoxLayout()
        self.chat_bubble = QTextBrowser()
        self.chat_bubble.setStyleSheet("""
            background-color: #ff5733;
            color: black;
            border-radius: 10px;
            padding: 8px;
            margin: 5px;
        """)
        self.chat_bubble.setOpenExternalLinks(False)
        self.chat_bubble.setReadOnly(True)
        self.chat_bubble.setVisible(False)
        
        chat_input_layout = QHBoxLayout()
        self.chat_input = QTextEdit()
        self.chat_input.setStyleSheet("""
            background-color: #e0e0e0;
            border: 1px solid #808080;
            color: black;
            border-radius: 5px;
            padding: 5px;
        """)
        self.chat_input.setFixedWidth(300)
        self.chat_input.setFixedHeight(40)
        self.chat_input.keyPressEvent = self.handle_input_keypress
        
        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon("assets/icons/send.png"))
        self.send_button.setFixedSize(30, 30)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #ff5733;
                color: white;
                border-radius: 5px;
            }
            QPushButton:pressed {
                background-color: #ff8566;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.send_button)
        
        chat_layout.addWidget(self.chat_bubble)
        chat_layout.addStretch()
        chat_layout.addLayout(chat_input_layout)
        
        main_layout.addLayout(chat_layout, stretch=1)
        
        # Model viewer and buttons
        content_layout = QHBoxLayout()
        self.viewer = ModelViewer(self.config.get("model_path", self.default_model_path), 
                                self.config.get("part_visibility", {}))
        self.progress_updated.emit(70, "Model viewer initialized.")
        
        if "part_visibility" in self.config:
            self.viewer.part_visibility.update(self.config["part_visibility"])
    
        content_layout.addWidget(self.viewer, stretch=2)
        
        # Buttons (Right)
        button_layout = QVBoxLayout()
        
        # Exit Button
        self.exit_button = QToolButton()
        self.exit_button.setIcon(QIcon("assets/icons/exit.png"))
        self.exit_button.setToolTip("Exit AINA")
        self.exit_button.clicked.connect(self.quit)

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
        
        # New Chat Button
        self.new_chat_button = QToolButton()
        self.new_chat_button.setIcon(QIcon("assets/icons/new-message.png"))
        self.new_chat_button.setToolTip("New Chat")
        self.new_chat_button.clicked.connect(self.open_newchat)
        
        # Chat Log Button
        self.chatlogs_button = QToolButton()
        self.chatlogs_button.setIcon(QIcon("assets/icons/document.png"))
        self.chatlogs_button.setToolTip("Chat Logs")
        self.chatlogs_button.clicked.connect(self.open_chatlogs)

        # Add buttons to layout
        button_layout.addWidget(self.new_chat_button)
        button_layout.addWidget(self.chatlogs_button)
        button_layout.addWidget(self.customize_button)
        button_layout.addWidget(self.setting_button)
        button_layout.addWidget(self.exit_button)
        button_layout.addStretch()
        
        content_layout.addLayout(button_layout)
        main_layout.addLayout(content_layout)
        outer_layout.addLayout(main_layout)
    
        self.setLayout(outer_layout)
        self.setMinimumSize(300, 200 + self.drag_area_size)
        
        # Initialize LLM
        self.llm = LLM(self)

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

        self.config.setdefault("width", vw(20))
        self.config.setdefault("height", vh(20))
        self.config.setdefault("model_path", self.default_model_path)
        self.config.setdefault("part_visibility", {})
        self.config.setdefault("allow_overflow", False)
        self.config.setdefault("fade_dialogue", False)
        self.config.setdefault("pos_x", vw(70))
        self.config.setdefault("pos_y", vh(70))
        self.config.setdefault("llm_prompt", "You are AINA, a helpful desktop pet assistant.")
        self.config.setdefault("llm_max_length", 100)
        self.config.setdefault("llm_top_k", 40)
        self.config.setdefault("llm_tempurature", 0.7)

        if not os.path.exists(self.config_file):
            self.save_config()
            print(f"Created new config file with defaults at {self.config_file}")

    def save_config(self):
        """Save settings to config file."""
        self.config["width"] = self.width()
        self.config["height"] = self.height()
        self.config["model_path"] = self.viewer.model_path if self.viewer else self.default_model_path
        self.config["part_visibility"] = self.viewer.part_visibility if self.viewer else {}
        self.config["allow_overflow"] = self.settings.allow_overflow.isChecked()
        self.config["fade_dialogue"] = self.settings.fade_dialogue.isChecked()
        self.config["pos_x"] = self.x()
        self.config["pos_y"] = self.y()
        self.config["llm_prompt"] = self.settings.llm_prompt.toPlainText() if hasattr(self.settings, 'llm_prompt') else self.config["llm_prompt"]
        self.config["llm_max_length"] = int(self.settings.max_length.text()) if hasattr(self.settings, 'max_length') else self.config["llm_max_length"]
        self.config["llm_top_k"] = int(self.settings.top_k.text()) if hasattr(self.settings, 'top_k') else self.config["llm_top_k"]
        self.config["llm_tempurature"] = float(self.settings.tempurature.text()) if hasattr(self.settings, 'tempurature') else self.config["llm_tempurature"]
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def send_message(self):
        """Send message from input to LLM and display response"""
        message = self.chat_input.toPlainText().strip()
        if message:
            self.chat_input.setEnabled(False)
            self.send_button.setEnabled(False)
            self.send_button.setIcon(QIcon("assets/icons/loading.png"))
            
            QTimer.singleShot(0, lambda: self.process_message(message))

    def process_message(self, message):
        """Process the message and update UI"""
        response = self.llm.process_message(message)
        self.chat_history.append(f"User: {message}\nAINA: {response}")
        self.chat_bubble.setPlainText(response)
        self.chat_bubble.setVisible(True)
        self.chat_input.clear()
        
        self.chat_input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.send_button.setIcon(QIcon("assets/icons/send.png"))

    def quit(self):
        QApplication.quit()

    def closeEvent(self, event):
        """Override close event to save config."""
        self.save_config()
        super().closeEvent(event)

    def handle_input_keypress(self, event):
        """Custom keypress handling for QTextEdit"""
        if event.key() == Qt.Key.Key_Return and not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.send_message()
        else:
            QTextEdit.keyPressEvent(self.chat_input, event)

    def open_settings(self):
        """Open AINA settings interface."""
        if self.settings is None or not self.settings.isVisible():
            self.settings = Settings(self)
            self.settings.show()
        else:
            self.settings.raise_()
            
    def open_chatlogs(self):
        """Open AINA chatlogs interface."""
        chatlog_dialog = QDialog(self)
        chatlog_dialog.setWindowTitle("Chat Logs")
        chatlog_dialog.setFixedSize(400, 300)
        layout = QVBoxLayout()

        log_display = QTextBrowser()
        log_display.setStyleSheet("""
            background-color: #e0e0e0;
            border: 1px solid #808080;
            border-radius: 5px;
            padding: 5px;
            color: black;
        """)
        log_display.setText("\n\n".join(self.chat_history))

        close_button = QPushButton("Close")
        close_button.setStyleSheet("""
            QPushButton {background-color: #ff5733; color: white; border-radius: 5px; padding: 3px;}
            QPushButton:pressed {background-color: #ff8566;}
        """)
        close_button.clicked.connect(chatlog_dialog.close)

        layout.addWidget(log_display)
        layout.addWidget(close_button)
        chatlog_dialog.setLayout(layout)
        chatlog_dialog.exec()
        
    def open_newchat(self):
        """Call function from LLM class"""
        self.llm.new_chat()
        self.chat_history.clear()
        
    def open_customizer(self):
        """Open the model customization interface."""
        if self.customizer is None or not self.customizer.isVisible():
            self.customizer = Customizer(self.viewer)
            self.customizer.show()
        else:
            self.customizer.raise_()

    def start_drag(self):
        """Initiate dragging when the drag_area button is pressed."""
        self.is_dragging = True
        self.old_pos = QApplication.instance().overrideCursor() or QCursor.pos()  # Use global cursor pos

    def mouseMoveEvent(self, event):
        """Handle dragging when initiated by the drag_area button."""
        if self.is_dragging and self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            new_pos = self.pos() + delta
            screen = QApplication.primaryScreen().availableGeometry()
                
            if not self.config["allow_overflow"]:
                new_pos.setX(max(0, min(new_pos.x(), screen.width() - self.width())))
                new_pos.setY(max(0, min(new_pos.y(), screen.height() - self.height())))
            
            new_pos.setX(max(0, min(new_pos.x(), screen.width() - self.drag_area_size)))
            new_pos.setY(max(0, min(new_pos.y(), screen.height() - self.drag_area_size)))
            self.move(new_pos)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """End dragging when the mouse is released."""
        self.is_dragging = False
        self.old_pos = None