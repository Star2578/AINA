from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QLabel, QLineEdit, QFileDialog, QCheckBox, QTextEdit
from PyQt6.QtCore import Qt, QPoint

class Settings(QWidget):
    def __init__(self, aina):
        super().__init__()
        self.aina = aina
        self.setWindowTitle("AINA Settings")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        self.old_pos = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout()

        sidebar = QVBoxLayout()
        self.categories = ["General", "LLM Model", "Generation"]
        self.category_buttons = {}
        for category in self.categories:
            btn = QPushButton(category)
            btn.clicked.connect(lambda checked, c=category: self.switch_category(c))
            sidebar.addWidget(btn)
            self.category_buttons[category] = btn
        sidebar.addStretch()

        self.stack = QStackedWidget()
        self.init_category_pages()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        main_layout.addLayout(sidebar, stretch=1)
        main_layout.addWidget(self.stack, stretch=3)
        outer_layout = QVBoxLayout()
        outer_layout.addLayout(main_layout)
        outer_layout.addWidget(close_button)
        self.setLayout(outer_layout)

        self.switch_category("General")

    def init_category_pages(self):
        # General
        general_widget = QWidget()
        general_layout = QVBoxLayout()
        general_layout.addWidget(QLabel("Resolution:"))
        self.width_input = QLineEdit(str(self.aina.width()))
        self.height_input = QLineEdit(str(self.aina.height()))
        self.allow_overflow = QCheckBox("Allow Overflow")
        self.allow_overflow.setChecked(self.aina.config["allow_overflow"])
        
        general_layout.addWidget(self.width_input)
        general_layout.addWidget(self.height_input)
        general_layout.addWidget(self.allow_overflow)
        
        self.general_apply_btn = QPushButton("Apply")
        self.general_apply_btn.setStyleSheet("""
            QPushButton {background-color: #ff5733; color: white; border-radius: 5px; padding: 5px;}
            QPushButton:pressed {background-color: #ff8566;}
            QPushButton:disabled {background-color: #8c8c8c; color: #cccccc;}
        """)
        self.general_apply_btn.clicked.connect(self.apply_resolution)
        self.general_apply_btn.setEnabled(False)
        
        general_layout.addWidget(self.general_apply_btn)
        general_layout.addStretch()
        general_widget.setLayout(general_layout)
        self.stack.addWidget(general_widget)
        # TODO : Implement font, color theme
        

        # LLM Model (placeholder)
        # TODO : Implement 
        # - Overhead Prompt : How should AINA respond

        llm_widget = QWidget()
        ollama_model_layout = QVBoxLayout()
        ollama_model_layout.addWidget(QLabel("Ollama Model Name:"))
        self.ollama_model = QTextEdit(self.aina.config["ollama_model"])
        self.ollama_model.setStyleSheet("""
            background-color: #e0e0e0;
            color: black;
            border: 1px solid #808080;
            border-radius: 5px;
        """)
        self.ollama_model.setFixedHeight(30)
        
        ollama_base_url_layout = QVBoxLayout()
        ollama_base_url_layout.addWidget(QLabel("Ollama URL:"))
        self.ollama_base_url = QTextEdit(self.aina.config["ollama_base_url"])
        self.ollama_base_url.setStyleSheet("""
            background-color: #e0e0e0;
            color: black;
            border: 1px solid #808080;
            border-radius: 5px;
        """)
        self.ollama_base_url.setFixedHeight(30)
        
        llm_layout = QVBoxLayout()
        llm_layout.addWidget(QLabel("Overhead Prompt:"))
        self.llm_prompt = QTextEdit(self.aina.config["llm_prompt"])
        self.llm_prompt.setStyleSheet("""
            background-color: #e0e0e0;
            color: black;
            border: 1px solid #808080;
            border-radius: 5px;
            padding: 5px;
        """)
        self.llm_prompt.setFixedHeight(100)
        
        self.llm_apply_btn = QPushButton("Apply")
        self.llm_apply_btn.setStyleSheet("""
            QPushButton {background-color: #ff5733; color: white; border-radius: 5px; padding: 5px;}
            QPushButton:pressed {background-color: #ff8566;}
            QPushButton:disabled {background-color: #8c8c8c; color: #cccccc;}
        """)
        self.llm_apply_btn.clicked.connect(self.apply_llm_settings)
        self.llm_apply_btn.setEnabled(False)
        
        llm_layout.addWidget(self.ollama_model)
        llm_layout.addWidget(self.ollama_base_url)
        llm_layout.addWidget(self.llm_prompt)
        llm_layout.addWidget(self.llm_apply_btn)
        llm_layout.addStretch()
        llm_widget.setLayout(llm_layout)
        self.stack.addWidget(llm_widget)

        # Generation (placeholder)
        # TODO : Implement
        # - Top K : Creativity
        # - Top P : Nucleus Sampling
        # - Temperature : Randomness
        # - Max Length : Respond length
        
        gen_widget = QWidget()
        gen_layout = QVBoxLayout()
        gen_layout.addWidget(QLabel("Generation Settings:"))
        
        top_k_layout = QHBoxLayout()
        top_k_layout.addWidget(QLabel("Top K:"))
        self.top_k = QLineEdit(str(self.aina.config["llm_top_k"]))
        self.top_k.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px;")
        top_k_layout.addWidget(self.top_k)
        
        top_p_layout = QHBoxLayout()
        top_p_layout.addWidget(QLabel("Top P:"))
        self.top_p = QLineEdit(str(self.aina.config["llm_top_p"]))
        self.top_p.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px;")
        top_p_layout.addWidget(self.top_p)
        
        temperature_layout = QHBoxLayout()
        temperature_layout.addWidget(QLabel("Temperature:"))
        self.temperature = QLineEdit(str(self.aina.config["llm_temperature"]))
        self.temperature.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px;")
        temperature_layout.addWidget(self.temperature)
        
        min_length_layout = QHBoxLayout()
        min_length_layout.addWidget(QLabel("Min Length:"))
        self.min_length = QLineEdit(str(self.aina.config["llm_min_length"]))
        self.min_length.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px;")
        min_length_layout.addWidget(self.min_length)
        
        max_length_layout = QHBoxLayout()
        max_length_layout.addWidget(QLabel("Max Length:"))
        self.max_length = QLineEdit(str(self.aina.config["llm_max_length"]))
        self.max_length.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px;")
        max_length_layout.addWidget(self.max_length)
        
        self.gen_apply_btn = QPushButton("Apply")
        self.gen_apply_btn.setStyleSheet("""
            QPushButton {background-color: #ff5733; color: white; border-radius: 5px; padding: 5px;}
            QPushButton:pressed {background-color: #ff8566;}
            QPushButton:disabled {background-color: #8c8c8c; color: #cccccc;}
        """)
        self.gen_apply_btn.clicked.connect(self.apply_llm_settings)
        self.gen_apply_btn.setEnabled(False)
        
        gen_layout.addLayout(top_k_layout)
        gen_layout.addLayout(top_p_layout)
        gen_layout.addLayout(temperature_layout)
        gen_layout.addLayout(min_length_layout)
        gen_layout.addLayout(max_length_layout)
        gen_layout.addWidget(self.gen_apply_btn)
        gen_layout.addStretch()
        gen_widget.setLayout(gen_layout)
        self.stack.addWidget(gen_widget)
        
        
        # Connect signals for enabling/disabling buttons
        self.width_input.textChanged.connect(self.check_general_changes)
        self.height_input.textChanged.connect(self.check_general_changes)
        self.allow_overflow.stateChanged.connect(self.check_general_changes)
        self.llm_prompt.textChanged.connect(self.check_llm_changes)
        self.top_p.textChanged.connect(self.check_gen_changes)
        self.top_k.textChanged.connect(self.check_gen_changes)
        self.temperature.textChanged.connect(self.check_gen_changes)
        self.min_length.textChanged.connect(self.check_gen_changes)
        self.max_length.textChanged.connect(self.check_gen_changes)

    def switch_category(self, category):
        index = self.categories.index(category)
        self.stack.setCurrentIndex(index)
        for cat, btn in self.category_buttons.items():
            btn.setStyleSheet("font-weight: bold" if cat == category else "")

    def apply_resolution(self):
        try:
            width = int(self.width_input.text())
            height = int(self.height_input.text())
            self.aina.config["allow_overflow"] = self.allow_overflow.isChecked()
            self.aina.setFixedSize(width, height)
            if not self.aina.config["allow_overflow"]:
                self.aina.setMinimumSize(200, 200)  # Enforce minimum size
            else:
                self.aina.setMinimumSize(0, 0)  # Allow overflow
            self.aina.save_config()
        except ValueError:
            print("Invalid resolution values")

    def apply_llm_settings(self):
        """Apply LLM settings and save to config"""
        try:
            self.aina.llm.prompt = self.llm_prompt.toPlainText()
            self.aina.llm.top_k = int(self.top_k.text())
            self.aina.llm.max_length = int(self.max_length.text())
            self.aina.save_config()
        except ValueError:
            print("Invalid generation values")

    # def restore_default_model(self):
    #     self.aina.viewer.load_model(self.aina.default_model_path)
    #     self.aina.viewer.part_visibility.clear()
    #     for part_id in range(len(self.aina.viewer.meshes)):
    #         self.aina.viewer.part_visibility[part_id] = True
    #     self.model_path_label.setText(f"Current: {self.aina.default_model_path}")
    #     self.aina.save_config()
    #     if self.aina.customizer and self.aina.customizer.isVisible():
    #         self.aina.customizer.tree.clear()
    #         self.aina.customizer.populate_tree()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
    
    def check_general_changes(self):
        try:
            width_changed = int(self.width_input.text()) != self.aina.width()
            height_changed = int(self.height_input.text()) != self.aina.height()
            overflow_changed = self.allow_overflow.isChecked() != self.aina.config["allow_overflow"]
            self.general_apply_btn.setEnabled(width_changed or height_changed or overflow_changed)
        except ValueError:
            self.general_apply_btn.setEnabled(True)

    def check_llm_changes(self):
        self.llm_apply_btn.setEnabled(self.llm_prompt.toPlainText() != self.aina.config["llm_prompt"])

    def check_gen_changes(self):
        try:
            top_k_changed = int(self.top_k.text()) != self.aina.config["llm_top_k"]
            top_p_changed = float(self.top_p.text()) != self.aina.config["llm_top_p"]
            temperature_changed = float(self.temperature.text()) != self.aina.config["llm_temperature"]
            min_length_changed = int(self.min_length.text()) != self.aina.config["llm_min_length"]
            max_length_changed = int(self.max_length.text()) != self.aina.config["llm_max_length"]
            self.gen_apply_btn.setEnabled(top_k_changed or top_p_changed or min_length_changed or max_length_changed or temperature_changed)
        except ValueError:
            self.gen_apply_btn.setEnabled(True)