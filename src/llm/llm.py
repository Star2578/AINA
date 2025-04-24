from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

class LLM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".aina_cache", "models", self.model_name)
        self.prompt = self.parent.config["llm_prompt"]
        self.max_length = self.parent.config["llm_max_length"]
        self.top_k = self.parent.config["llm_top_k"]
        self.temperature = self.parent.config["llm_tempurature"]

        self.load_model()

    def load_model(self):
        """Load the model and tokenizer, using cache if available"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                local_files_only=os.path.exists(os.path.join(self.cache_dir, "tokenizer_config.json"))
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
                self.tokenizer.pad_token_id = self.tokenizer.eos_token_id
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                cache_dir=self.cache_dir,
                local_files_only=os.path.exists(os.path.join(self.cache_dir, "config.json"))
            )
            
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            self.model.eval()
            
            print(f"Model {self.model_name} loaded successfully from {self.cache_dir}")
        except Exception as e:
            print(f"Error loading model: {e}. Falling back to mock model.")
            self.model = self.mock_model
            self.tokenizer = None

    def process_message(self, message):
        """Process user message and return response"""
        if self.model == self.mock_model or self.tokenizer is None:
            full_prompt = f"{self.prompt}\nUser: {message}\nAINA:"
            return self.mock_model(full_prompt)[:self.max_length]

        # Prepare prompt
        full_prompt = (
            f"<|system|> {self.prompt} "
            f"<|user|> {message} <|assistant|>"
        )
        inputs = self.tokenizer(
            full_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_length
        ).to(self.device)

        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=self.max_length + len(inputs["input_ids"][0]),
                top_k=self.top_k,
                temperature=self.temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                num_return_sequences=1
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response[len(full_prompt):].strip()
        return response[:self.max_length]

    def mock_model(self, prompt):
        """Temporary mock model response"""
        return f"AINA says: I received '{prompt.split('User: ')[-1].split('AINA:')[0].strip()}'"

    def new_chat(self):
        """Clear current chat bubble"""
        self.parent.chat_bubble.setText("")
        self.parent.chat_bubble.setVisible(False)
        self.parent.chat_input.clear()