from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

class Worker(QObject):
    """Worker class to process LLM messages in a separate thread"""
    finished = pyqtSignal(str)  # Signal to emit the response
    error = pyqtSignal(str)     # Signal to emit errors

    def __init__(self, llm, message):
        super().__init__()
        self.llm = llm
        self.message = message

    def run(self):
        """Run the LLM processing"""
        try:
            response = self.llm.process_message_threaded(self.message)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))

class LLM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.cache_dir = os.path.join(os.path.expanduser("~"), ".aina_cache", "models", self.model_name.replace("/", "_"))
        self.prompt = self.parent.config["llm_prompt"]
        self.min_length = self.parent.config["llm_min_length"]
        self.max_length = self.parent.config["llm_max_length"]
        self.top_k = self.parent.config["llm_top_k"]
        self.temperature = self.parent.config["llm_temperature"]
        self.top_p = self.parent.config["llm_top_p"]
        
        self.conversation_history = []
        self.max_history_length = 10
        self.thread = None
        self.worker = None

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
        """Start processing message in a separate thread"""
        if self.thread and self.thread.isRunning():
            print("LLM is already processing a message")
            return

        # Create worker and thread
        self.thread = QThread()
        self.worker = Worker(self, message)
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)  # Reset thread
        
        # Start thread
        self.thread.start()

    def process_message_threaded(self, message):
        """Process user message and return response (runs in worker thread)"""
        if self.model == self.mock_model or self.tokenizer is None:
            full_prompt = f"{self.prompt}\nUser: {message}\nAINA:"
            return self.mock_model(full_prompt)[:self.max_length]

        self.conversation_history.append(f"<|user|> {message} <|assistant|>")
        
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]
        
        full_prompt = f"<|system|> {self.prompt} "
        history_prompt = ""
        current_length = len(self.tokenizer.encode(full_prompt, add_special_tokens=False))
        for entry in reversed(self.conversation_history):
            entry_tokens = len(self.tokenizer.encode(entry, add_special_tokens=False))
            if current_length + entry_tokens < self.max_length * 0.8:
                history_prompt = entry + history_prompt
                current_length += entry_tokens
            else:
                break
        full_prompt += history_prompt
        
        inputs = self.tokenizer(
            full_prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=int(self.max_length * 0.8)
        ).to(self.device)

        # Generate response
        with torch.no_grad():
            outputs = self.model.generate(
                input_ids=inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=self.max_length + len(inputs["input_ids"][0]),
                min_length=self.min_length,
                top_k=self.top_k,
                top_p=self.top_p,
                temperature=self.temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
                num_return_sequences=1,
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        response = response[len(full_prompt):].strip()
        
        self.conversation_history[-1] += f" {response}"
        
        return response[:self.max_length]

    def on_processing_finished(self, response):
        """Handle completed processing"""
        self.parent.process_message_response(response)

    def on_processing_error(self, error):
        """Handle processing errors"""
        print(f"LLM processing error: {error}")
        self.parent.process_message_response(f"Error: {error}")

    def on_thread_finished(self):
        """Reset thread after it finishes"""
        self.thread = None
        self.worker = None

    def mock_model(self, prompt):
        """Temporary mock model response"""
        return f"AINA says: I received '{prompt.split('User: ')[-1].split('AINA:')[0].strip()}'"

    def new_chat(self):
        """Clear current chat bubble and reset conversation history"""
        self.conversation_history = []
        self.parent.chat_bubble.setText("")
        self.parent.chat_bubble.setVisible(False)
        self.parent.chat_input.clear()