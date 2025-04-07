from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt

class LLM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.init_ui()
        self.model = self.mock_model
        self.prompt = self.parent.config["llm_prompt"]
        self.max_length = self.parent.config["llm_max_length"]
        self.top_k = self.parent.config["llm_top_k"]

    def init_ui(self):
        # No visible UI needed since it's integrated into AINA
        pass

    def process_message(self, message):
        """Process user message and return response"""
        full_prompt = f"{self.prompt}\nUser: {message}\nAINA:"
        return self.model(full_prompt)[:self.max_length]

    def mock_model(self, prompt):
        """Temporary mock model response"""
        return f"AINA says: I received '{prompt.split('User: ')[-1].split('AINA:')[0].strip()}'"

    def new_chat(self):
        """Clear current chat bubble"""
        self.parent.chat_bubble.setText("")
        self.parent.chat_input.clear()