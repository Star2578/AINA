# AINA: Emotion-Aware Chatbot Desktop Application

AINA is a chatbot application developed for an NLP course project. It integrates emotion classification to trigger visual emotes in response to user input, creating a more interactive and expressive chatbot experience.

## Features

- Emotion classification from user input using a fine-tuned Thai language model
- Visual emotes corresponding to classified emotions
- Local desktop interface, runs offline on Windows
- Chat system powered by a local LLM (Ollama)

## Dataset

AINA uses a custom Thai-language emotion classification dataset available on Hugging Face:

https://huggingface.co/KittiphopKhankaew/Aina-emotion-classification-WangChanBERTa

## Emotion Classification Model

We use a fine-tuned version of WangChanBERTa for Thai emotion detection:

https://huggingface.co/KittiphopKhankaew/Aina-emotion-classification-WangChanBERTa

## Supported Emotions

- Idle / Happy  
- Smirk  
- Sad  
- Surprise  
- Angry

Each emotion triggers a different visual emote.

## System Requirements

- Python 3.12  
- Ollama 0.6.8  
- Windows environment

This project is built and tested exclusively for Windows platforms.

## Installation and Running

1. Install Python 3.12 and make sure it is added to your system PATH.
2. Install Ollama version 0.6.8 from https://ollama.com
3. Clone or download this repository.
4. Run `Start.bat` to launch the application.

## Development Notes

- Emotion classification is performed using the Hugging Face Transformers library.
- Emotes are linked to the classified emotion output.
- A small local language model is used to generate chatbot responses via Ollama.
- After updated the model name in setting, restart the app to make it active.

## Credits

- Developed for: NLP Course Project  
- Team: Nuttapol Sinsuwan, Kittiphop Khankaew, Monthawat sawarak
