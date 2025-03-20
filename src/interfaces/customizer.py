from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon

class Customizer(QWidget):
    def __init__(self, model_viewer):
        super().__init__()

        self.model_viewer = model_viewer  # Reference to ModelViewer instance
        self.setWindowTitle("Model Customizer")
        self.setFixedSize(200, 300)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        
        # For dragging the window
        self.old_pos = None

        self.init_ui()

    def init_ui(self):
        """Initialize the UI elements."""
        layout = QVBoxLayout()

        # Tree widget for model parts
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Model Parts")
        self.tree.setColumnCount(1)
        self.populate_tree()
        self.tree.itemChanged.connect(self.on_item_changed)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        # Add widgets to layout
        layout.addWidget(self.tree)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def populate_tree(self):
        """Populate the tree with model parts."""
        for part_id in self.model_viewer.part_visibility.keys():
            item = QTreeWidgetItem(self.tree)
            # Use stored name or fallback to part_id
            name = self.model_viewer.part_names.get(part_id, f"Part {part_id}")
            item.setText(0, name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked if self.model_viewer.part_visibility[part_id] else Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, part_id)  # Still store part_id for reference
        self.tree.expandAll()

    def on_item_changed(self, item, column):
        """Handle changes to tree items (e.g., checkbox toggled)."""
        part_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_visible = item.checkState(0) == Qt.CheckState.Checked
        self.model_viewer.part_visibility[part_id] = is_visible
        self.model_viewer.update()  # Trigger repaint in ModelViewer

    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.pos() + delta)
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging."""
        self.old_pos = None