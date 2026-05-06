🤖 J.A.R.V.I.S – Personal AI Voice Assistant 

J.A.R.V.I.S (Just A Rather Very Intelligent System) is a Python-based voice + text-controlled AI assistant inspired by Iron Man’s JARVIS. It combines speech recognition, text-to-speech, AI (Claude), and system automation to create a powerful desktop assistant that can understand and respond like a real intelligent companion.

🚀 Features

🧠 AI Brain (Claude Integration)

Natural, conversational AI responses using Anthropic Claude
Maintains conversation memory for context-aware replies

🎙 Voice Interaction

Wake word activation: "Jarvis"
Speech-to-text using Google Speech Recognition
Text-to-speech responses with customizable voice engine

💻 System Control

Get real-time system information (CPU, RAM, Disk, Battery)
Open apps and websites using voice commands

🌐 Smart Web Tools

Wikipedia search summaries
Google search & YouTube search
Live weather updates (wttr.in API)
Latest news headlines (NewsAPI)

🧮 Utility Features

Built-in calculator (safe eval with math support)
Joke generator for fun interactions
Reminder system with timers

🎛 Command Intelligence

Smart command routing system
Natural language understanding for tasks like:
“What’s the weather in Doha?”
“Search YouTube for AI tutorials”
“Tell me a joke”
“Open Chrome”
“Calculate 25 * 4”
🛠 Tech Stack
Python 3
OpenAI / Anthropic Claude API
SpeechRecognition
pyttsx3
Wikipedia API
psutil
requests
OpenCV (optional extensions)
dotenv
colorama
⚙️ Setup Instructions
1. Install dependencies
pip install -r requirements_jarvis.txt
2. Set API Key

Create a .env file and add:

ANTHROPIC_API_KEY=your_api_key_here
3. Run the assistant
python jarvis.py

🎯 How to Use
Say “Jarvis” to activate voice mode
Or type commands in the terminal
Say “quit” to exit

💡 Example Commands
“Jarvis, what’s the time?”
“Search Wikipedia for Tesla”
“Open YouTube”
“What’s the weather in Doha?”
“Calculate 45 * 12”
“Tell me a joke”
“Give me system info”

⚡ About the Project
This project was built as a step toward creating a fully functional personal AI assistant, combining voice interaction, automation, and large language models into one system.

It demonstrates real-world use of:
AI integration
Speech recognition systems
Automation workflows
Python-based system tools
