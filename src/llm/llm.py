import json
import subprocess
import requests
import time
import os
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QThread, pyqtSignal, QObject

OLLAMA_EXECUTABLE = "ollama"  # Adjust path if needed

def is_ollama_running(base_url="http://localhost:11434"):
    """Checks if the Ollama API is reachable."""
    try:
        response = requests.get(f"{base_url}/api/version")
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        return False

def start_ollama():
    """Starts the Ollama server as a subprocess."""
    try:
        process = subprocess.Popen([OLLAMA_EXECUTABLE, "serve"])
        print("Ollama server started in the background.")
        return process
    except FileNotFoundError:
        print(f"Error: Ollama executable not found at '{OLLAMA_EXECUTABLE}'. Make sure it's in your PATH or adjust OLLAMA_EXECUTABLE.")
        return None
    except Exception as e:
        print(f"Error starting Ollama: {e}")
        return None

def stop_ollama(process):
    """Terminates the Ollama subprocess."""
    if process and process.poll() is None:
        process.terminate()
        process.wait(timeout=5)  # Give it some time to shut down
        if process.poll() is None:
            process.kill()  # Forcefully kill if it didn't terminate
        print("Ollama server stopped.")

class Worker(QObject):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, llm, message):
        super().__init__()
        self.llm = llm
        self.message = message

    def run(self):
        try:
            response = self.llm.process_message_threaded(self.message)
            self.finished.emit(response)
        except Exception as e:
            self.error.emit(str(e))

class LLM(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.model_name = self.parent.config.get("ollama_model", "codellama:7b")
        self.ollama_base_url = self.parent.config.get("ollama_base_url", "http://localhost:11434")
        self.prompt = self.parent.config["llm_prompt"]
        self.max_length = self.parent.config["llm_max_length"]
        self.temperature = self.parent.config.get("llm_temperature", 0.7)
        self.top_p = self.parent.config.get("llm_top_p", 0.95)
        self.top_k = self.parent.config.get("llm_top_k", 50)

        self.conversation_history = []
        self.max_history_length = 10
        self.thread = None
        self.worker = None
        self.ollama_process = None

        self.initialize_ollama()

    def initialize_ollama(self):
        """Checks if Ollama is running and starts it if not."""
        if not is_ollama_running(self.ollama_base_url):
            print("Ollama not running. Attempting to start...")
            self.ollama_process = start_ollama()
            if self.ollama_process:
                # Wait a few seconds for Ollama to start
                time.sleep(5)
                if not is_ollama_running(self.ollama_base_url):
                    print("Error: Failed to start Ollama.")
                    # Optionally disable LLM functionality or show an error to the user
            else:
                print("Ollama could not be started.")
                # Optionally disable LLM functionality

    def closeEvent(self, event):
        """Handles the application's closing event."""
        if self.ollama_process:
            stop_ollama(self.ollama_process)
        super().closeEvent(event)

    def process_message(self, message):
        if self.thread and self.thread.isRunning():
            print("LLM is already processing a message")
            return

        self.thread = QThread()
        self.worker = Worker(self, message)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.error.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_thread_finished)

        self.thread.start()

    def process_message_threaded(self, message):
        self.conversation_history.append({"role": "user", "content": message})
        if len(self.conversation_history) > self.max_history_length:
            self.conversation_history = self.conversation_history[-self.max_history_length:]

        prompt_with_history = f"{self.prompt}\n"
        for item in self.conversation_history:
            prompt_with_history += f"{item['role'].capitalize()}: {item['content']}\n"
        prompt_with_history += "Assistant:"

        data = {
            "prompt": prompt_with_history,
            "model": self.model_name,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "top_p": self.top_p,
                "top_k": self.top_k,
                "num_predict": self.max_length
            }
        }

        try:
            response = requests.post(f"{self.ollama_base_url}/api/generate", json=data, stream=False)
            response.raise_for_status()
            response_data = response.json()
            ollama_response = response_data.get("response", "").strip()
            self.conversation_history.append({"role": "assistant", "content": ollama_response})
            return ollama_response
        except requests.exceptions.RequestException as e:
            error_message = f"Error communicating with Ollama: {e}"
            print(error_message)
            return f"Error: {error_message}"
        except json.JSONDecodeError as e:
            error_message = f"Error decoding Ollama response: {e} - {response.text}"
            print(error_message)
            return f"Error: {error_message}"

    def on_processing_finished(self, response):
        self.parent.process_message_response(response)

    def on_processing_error(self, error):
        print(f"LLM processing error: {error}")
        self.parent.process_message_response(f"Error: {error}")

    def on_thread_finished(self):
        self.thread = None
        self.worker = None

    def new_chat(self):
        self.conversation_history = []
        self.parent.chat_bubble.setText("")
        self.parent.chat_bubble.setVisible(False)
        self.parent.chat_input.clear()