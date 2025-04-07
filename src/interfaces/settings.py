from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, QLabel, QLineEdit, QFileDialog, QCheckBox
from PyQt6.QtCore import Qt, QPoint

class Settings(QWidget):
    def __init__(self, aina):
        super().__init__()
        self.aina = aina
        self.setWindowTitle("AINA Settings")
        self.setFixedSize(300, 200)
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
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_resolution)
        general_layout.addWidget(apply_btn)
        general_layout.addStretch()
        general_widget.setLayout(general_layout)
        self.stack.addWidget(general_widget)
        # TODO : Implement font, color theme
        

        # LLM Model (placeholder)
        # TODO : Implement 
        # - Overhead Prompt : How should AINA respond
        # #
        llm_widget = QWidget()
        llm_layout = QVBoxLayout()
        llm_layout.addWidget(QLabel("Overhead Prompt:"))
        self.llm_prompt = QLineEdit(self.aina.config["llm_prompt"])
        self.llm_prompt.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px; padding: 5px;")
        llm_layout.addWidget(self.llm_prompt)
        apply_llm_btn = QPushButton("Apply")
        apply_llm_btn.clicked.connect(self.apply_llm_settings)
        llm_layout.addWidget(apply_llm_btn)
        llm_layout.addStretch()
        llm_widget.setLayout(llm_layout)
        self.stack.addWidget(llm_widget)

        # Generation (placeholder)
        # TODO : Implement
        # - Top K : Creativity
        # - Max Length : Respond length
        # #
        gen_widget = QWidget()
        gen_layout = QVBoxLayout()
        gen_layout.addWidget(QLabel("Generation Settings:"))
        
        top_k_layout = QHBoxLayout()
        top_k_layout.addWidget(QLabel("Top K (Creativity):"))
        self.top_k = QLineEdit(str(self.aina.config["llm_top_k"]))
        self.top_k.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px; padding: 5px;")
        top_k_layout.addWidget(self.top_k)
        
        max_length_layout = QHBoxLayout()
        max_length_layout.addWidget(QLabel("Max Length:"))
        self.max_length = QLineEdit(str(self.aina.config["llm_max_length"]))
        self.max_length.setStyleSheet("background-color: #e0e0e0; border: 1px solid #808080; border-radius: 5px; padding: 5px;")
        max_length_layout.addWidget(self.max_length)
        
        apply_gen_btn = QPushButton("Apply")
        apply_gen_btn.clicked.connect(self.apply_llm_settings)
        
        gen_layout.addLayout(top_k_layout)
        gen_layout.addLayout(max_length_layout)
        gen_layout.addWidget(apply_gen_btn)
        gen_layout.addStretch()
        gen_widget.setLayout(gen_layout)
        self.stack.addWidget(gen_widget)

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
            self.aina.llm.prompt = self.llm_prompt.text()
            self.aina.llm.top_k = int(self.top_k.text())
            self.aina.llm.max_length = int(self.max_length.text())
            self.aina.save_config()
        except ValueError:
            print("Invalid generation values")

    def restore_default_model(self):
        self.aina.viewer.load_model(self.aina.default_model_path)
        self.aina.viewer.part_visibility.clear()
        for part_id in range(len(self.aina.viewer.meshes)):
            self.aina.viewer.part_visibility[part_id] = True
        self.model_path_label.setText(f"Current: {self.aina.default_model_path}")
        self.aina.save_config()
        if self.aina.customizer and self.aina.customizer.isVisible():
            self.aina.customizer.tree.clear()
            self.aina.customizer.populate_tree()

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