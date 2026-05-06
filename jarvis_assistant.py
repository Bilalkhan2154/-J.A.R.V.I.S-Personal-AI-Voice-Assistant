"""
╔══════════════════════════════════════════════════════════╗
║          J.A.R.V.I.S  —  Personal AI Assistant          ║
║    Just A Rather Very Intelligent System  v2.0           ║
╚══════════════════════════════════════════════════════════╝

SETUP:  pip install -r requirements_jarvis.txt
        Set your ANTHROPIC_API_KEY in the .env file or as an env var.
"""

import os
import sys
import time
import datetime
import threading
import subprocess
import webbrowser
import json
import math
import re
import random
import platform
import psutil
import requests
import wikipedia
import pyttsx3
import speech_recognition as sr
from anthropic import Anthropic
from dotenv import load_dotenv
from colorama import Fore, Back, Style, init as colorama_init

# ─── Init ────────────────────────────────────────────────────────────────────
load_dotenv()
colorama_init(autoreset=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
WAKE_WORD        = "jarvis"          # Say "Jarvis" to wake the assistant
VOICE_RATE       = 175               # Words per minute (150–200 is comfortable)
VOICE_VOLUME     = 1.0               # 0.0 – 1.0
VOICE_INDEX      = 0                 # 0 = first system voice; change if you prefer another
LISTEN_TIMEOUT   = 8                 # Seconds to wait for speech
PHRASE_LIMIT     = 15                # Max seconds of a single utterance

# Conversation memory (sent to Claude every turn)
conversation_history: list[dict] = []

SYSTEM_PROMPT = """
You are J.A.R.V.I.S., a highly intelligent, witty, and helpful personal AI assistant — 
inspired by Tony Stark's AI from Iron Man. 

Personality:
- Speak concisely and confidently. Your answers are sharp, never padded.
- Add occasional dry wit or light sarcasm when appropriate (never mean).
- Address the user as "sir" or "ma'am" (alternate naturally, or let them tell you which they prefer).
- When asked about yourself, you are J.A.R.V.I.S., not Claude.
- Keep responses SHORT for voice: 1–4 sentences unless detail is requested.
- For technical or list-heavy answers, offer to elaborate.

You have access to real-time capabilities (weather, time, system info, web) 
that are handled by separate functions — the user will tell you results when relevant.
"""

# ─── Banner ──────────────────────────────────────────────────────────────────
def print_banner():
    banner = f"""
{Fore.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   {Fore.YELLOW}     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗         {Fore.CYAN}      ║
║   {Fore.YELLOW}     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝         {Fore.CYAN}      ║
║   {Fore.YELLOW}     ██║███████║██████╔╝██║   ██║██║███████╗         {Fore.CYAN}      ║
║   {Fore.YELLOW}██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║        {Fore.CYAN}       ║
║   {Fore.YELLOW}╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║        {Fore.CYAN}       ║
║   {Fore.YELLOW} ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝       {Fore.CYAN}       ║
║                                                              ║
║   {Fore.GREEN}Just A Rather Very Intelligent System  v2.0{Fore.CYAN}            ║
║   {Fore.WHITE}Wake word: "{WAKE_WORD.upper()}"   |   Say "quit" to exit{Fore.CYAN}          ║
╚══════════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""
    print(banner)

# ─── Text-to-Speech ──────────────────────────────────────────────────────────
class VoiceEngine:
    def __init__(self):
        self.engine = pyttsx3.init()
        self._configure()
        self._lock = threading.Lock()

    def _configure(self):
        self.engine.setProperty("rate",   VOICE_RATE)
        self.engine.setProperty("volume", VOICE_VOLUME)
        voices = self.engine.getProperty("voices")
        if voices and VOICE_INDEX < len(voices):
            self.engine.setProperty("voice", voices[VOICE_INDEX].id)

    def speak(self, text: str, silent: bool = False):
        """Print and optionally speak text."""
        print(f"\n{Fore.CYAN}🤖 JARVIS:{Style.RESET_ALL} {text}\n")
        if not silent:
            with self._lock:
                self.engine.say(text)
                self.engine.runAndWait()

    def list_voices(self):
        voices = self.engine.getProperty("voices")
        for i, v in enumerate(voices):
            print(f"  [{i}] {v.name}  —  {v.id}")

# ─── Speech Recognition ──────────────────────────────────────────────────────
class EarEngine:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold  = 0.8
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        self.mic = sr.Microphone()

    def calibrate(self):
        print(f"{Fore.YELLOW}🎙  Calibrating microphone for ambient noise…{Style.RESET_ALL}")
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
        print(f"{Fore.GREEN}✔  Microphone ready.{Style.RESET_ALL}\n")

    def listen(self, prompt: bool = True) -> str | None:
        """Listen once and return transcribed text, or None on failure."""
        if prompt:
            print(f"{Fore.YELLOW}🎙  Listening…{Style.RESET_ALL}")
        try:
            with self.mic as source:
                audio = self.recognizer.listen(
                    source,
                    timeout=LISTEN_TIMEOUT,
                    phrase_time_limit=PHRASE_LIMIT,
                )
            text = self.recognizer.recognize_google(audio)
            return text.strip()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"{Fore.RED}⚠  Google Speech error: {e}{Style.RESET_ALL}")
            return None

# ─── AI Brain (Claude / Anthropic) ───────────────────────────────────────────
class Brain:
    def __init__(self):
        if not ANTHROPIC_API_KEY:
            print(f"{Fore.RED}⚠  ANTHROPIC_API_KEY not set. AI responses disabled.{Style.RESET_ALL}")
            self.client = None
        else:
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def think(self, user_input: str) -> str:
        if not self.client:
            return "I'm afraid my AI core is offline. Please set your ANTHROPIC_API_KEY."

        conversation_history.append({"role": "user", "content": user_input})

        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=conversation_history,
        )
        reply = response.content[0].text.strip()
        conversation_history.append({"role": "assistant", "content": reply})
        return reply

# ─── Built-in Skills ─────────────────────────────────────────────────────────
class Skills:

    # ── Time & Date ──────────────────────────────────────────────────────
    @staticmethod
    def get_time() -> str:
        now = datetime.datetime.now()
        return f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."

    # ── Weather (wttr.in — no key required) ──────────────────────────────
    @staticmethod
    def get_weather(city: str = "Doha") -> str:
        try:
            url = f"https://wttr.in/{city.replace(' ', '+')}?format=3"
            r = requests.get(url, timeout=6)
            if r.status_code == 200:
                return r.text.strip()
            return "I couldn't retrieve the weather right now, sir."
        except Exception:
            return "Weather service is unavailable at the moment."

    # ── Wikipedia ────────────────────────────────────────────────────────
    @staticmethod
    def wiki_summary(query: str, sentences: int = 2) -> str:
        try:
            wikipedia.set_lang("en")
            result = wikipedia.summary(query, sentences=sentences, auto_suggest=True)
            return result
        except wikipedia.DisambiguationError as e:
            return f"That term is ambiguous. Did you mean: {', '.join(e.options[:3])}?"
        except wikipedia.PageError:
            return "I couldn't find a Wikipedia article for that."
        except Exception:
            return "Wikipedia is unreachable right now."

    # ── System Info ──────────────────────────────────────────────────────
    @staticmethod
    def system_info() -> str:
        cpu   = psutil.cpu_percent(interval=1)
        mem   = psutil.virtual_memory()
        disk  = psutil.disk_usage("/")
        uname = platform.uname()
        bat   = psutil.sensors_battery()
        bat_s = f"{bat.percent:.0f}% {'(charging)' if bat.power_plugged else '(on battery)'}" if bat else "N/A"

        return (
            f"System: {uname.system} {uname.release}  |  "
            f"CPU: {cpu}%  |  "
            f"RAM: {mem.percent}% used ({mem.available // (1024**2)} MB free)  |  "
            f"Disk: {disk.percent}% used  |  "
            f"Battery: {bat_s}"
        )

    # ── Calculator ───────────────────────────────────────────────────────
    @staticmethod
    def calculate(expr: str) -> str:
        try:
            # Safe eval using math module only
            allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
            allowed.update({"abs": abs, "round": round, "pow": pow})
            result = eval(expr, {"__builtins__": {}}, allowed)  # noqa: S307
            return f"The result of {expr} is {result}."
        except Exception:
            return "I couldn't evaluate that expression."

    # ── Jokes ────────────────────────────────────────────────────────────
    @staticmethod
    def tell_joke() -> str:
        try:
            r = requests.get(
                "https://official-joke-api.appspot.com/random_joke", timeout=5
            )
            if r.status_code == 200:
                j = r.json()
                return f"{j['setup']} … {j['punchline']}"
        except Exception:
            pass
        jokes = [
            "Why don't scientists trust atoms? Because they make up everything.",
            "I told my computer I needed a break. Now it won't stop sending me Kit-Kat ads.",
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "A SQL query walks into a bar and asks: SELECT drinks FROM menu WHERE price < 5.",
        ]
        return random.choice(jokes)

    # ── Open websites ────────────────────────────────────────────────────
    @staticmethod
    def open_website(url: str) -> str:
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {url} in your browser, sir."

    # ── Google Search ────────────────────────────────────────────────────
    @staticmethod
    def google_search(query: str) -> str:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Searching Google for: {query}"

    # ── YouTube Search ───────────────────────────────────────────────────
    @staticmethod
    def youtube_search(query: str) -> str:
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        return f"Searching YouTube for: {query}"

    # ── Reminder (simple countdown) ──────────────────────────────────────
    @staticmethod
    def set_reminder(message: str, seconds: int, voice: VoiceEngine):
        def _remind():
            time.sleep(seconds)
            voice.speak(f"Reminder: {message}")
        threading.Thread(target=_remind, daemon=True).start()
        return f"Reminder set for {seconds} seconds: '{message}'."

    # ── App Launcher ─────────────────────────────────────────────────────
    @staticmethod
    def open_app(app_name: str) -> str:
        apps = {
            "notepad":      ("notepad.exe",    "gedit",       "open -a TextEdit"),
            "calculator":   ("calc.exe",        "gnome-calculator", "open -a Calculator"),
            "file manager": ("explorer.exe",    "nautilus",    "open ~"),
            "terminal":     ("cmd.exe",         "gnome-terminal", "open -a Terminal"),
            "browser":      ("start chrome",    "google-chrome","open -a 'Google Chrome'"),
        }
        name_lower = app_name.lower()
        for key, (win, lin, mac) in apps.items():
            if key in name_lower:
                sys_os = platform.system()
                cmd = win if sys_os == "Windows" else (mac if sys_os == "Darwin" else lin)
                try:
                    subprocess.Popen(cmd, shell=True)
                    return f"Launching {key}, sir."
                except Exception as e:
                    return f"Failed to launch {key}: {e}"
        return f"I don't have a shortcut for '{app_name}' in my registry."
    
    @staticmethod
    def get_news() -> str:
     try:
        api_key = "12947e78de97475c8a714c530a6f4796"

        url = f"https://newsapi.org/v2/top-headlines?country=us&apiKey={api_key}"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return "News API error, sir."

        data = r.json()
        articles = data.get("articles", [])

        if not articles:
            return "No news found, sir."

        headlines = []
        for i, article in enumerate(articles[:5]):
            title = article.get("title", "No title")
            headlines.append(f"{i+1}. {title}")

        return "Top news:\n" + "\n".join(headlines)

     except Exception as e:
        return f"News error: {str(e)}"

# ─── Command Router ───────────────────────────────────────────────────────────
class CommandRouter:
    """
    Tries to match the query to a built-in skill before calling Claude.
    Returns (response_text, handled_locally).
    """

    def __init__(self, skills: Skills, brain: Brain, voice: VoiceEngine):
        self.s = skills
        self.brain = brain
        self.voice = voice

    def route(self, query: str) -> str:
        q = query.lower().strip()

        # ── Quit ──────────────────────────────────────────────────────────
        if any(w in q for w in ["quit", "exit", "goodbye", "shut down", "stop"]):
            self.voice.speak("Shutting down. It has been a pleasure, sir. Goodbye.")
            sys.exit(0)

        # ── Clear conversation ─────────────────────────────────────────────
        if any(w in q for w in ["clear memory", "reset conversation", "forget everything"]):
            conversation_history.clear()
            return "Conversation memory cleared, sir. Fresh start."

        # ── Time ──────────────────────────────────────────────────────────
        if any(w in q for w in ["time", "current time", "what time"]):
            return self.s.get_time()

        # ── Weather ───────────────────────────────────────────────────────
        if "weather" in q:
            city = "Doha"
            # Try to extract city after "in" or "for"
            m = re.search(r"(?:weather\s+(?:in|for|at)\s+)([a-zA-Z\s]+)", q)
            if m:
                city = m.group(1).strip()
            return self.s.get_weather(city)

        # ── Wikipedia ─────────────────────────────────────────────────────
        if any(w in q for w in ["who is", "what is", "tell me about", "wikipedia", "wiki"]):
            topic = re.sub(
                r"(who is|what is|tell me about|wikipedia|wiki|jarvis)", "", q
            ).strip()
            if topic:
                return self.s.wiki_summary(topic)

        # ── System info ───────────────────────────────────────────────────
        if any(w in q for w in ["system info", "cpu", "ram", "battery", "memory usage", "disk usage"]):
            return self.s.system_info()

        # ── Calculator ────────────────────────────────────────────────────
        if any(w in q for w in ["calculate", "compute", "math", "what is", "how much is"]):
            expr = re.sub(r"(calculate|compute|math|what is|how much is)", "", q).strip()
            if any(op in expr for op in ["+", "-", "*", "/", "**", "sqrt", "^"]):
                expr = expr.replace("^", "**").replace("x", "*")
                return self.s.calculate(expr)

        # ── Joke ──────────────────────────────────────────────────────────
        if any(w in q for w in ["joke", "funny", "make me laugh", "humor"]):
            return self.s.tell_joke()

        # ── YouTube ───────────────────────────────────────────────────────
        if "youtube" in q:
            topic = re.sub(r"(youtube|play|search|find|on)", "", q).strip()
            return self.s.youtube_search(topic or "trending")

        # ── Google search ─────────────────────────────────────────────────
        if any(w in q for w in ["google", "search for", "look up"]):
            topic = re.sub(r"(google|search for|look up)", "", q).strip()
            return self.s.google_search(topic)

        # ── Open website ──────────────────────────────────────────────────
        if any(w in q for w in ["open", "go to", "visit", "launch website"]):
            m = re.search(r"(?:open|go to|visit|launch website)\s+([^\s]+)", q)
            if m:
                target = m.group(1)
                if "." in target:  # looks like a URL
                    return self.s.open_website(target)
                # maybe an app
                return self.s.open_app(target)

        # ── Reminder ──────────────────────────────────────────────────────
        if "remind" in q:
            m = re.search(r"remind\s+me\s+(?:to\s+)?(.+?)\s+in\s+(\d+)\s*(second|minute|hour)", q)
            if m:
                msg  = m.group(1)
                amt  = int(m.group(2))
                unit = m.group(3)
                secs = amt * (60 if unit == "minute" else 3600 if unit == "hour" else 1)
                return self.s.set_reminder(msg, secs, self.voice)

        # ── List voices ───────────────────────────────────────────────────
        if "list voices" in q or "available voices" in q:
            self.voice.list_voices()
            return "Voice list printed to the console, sir."
        
        if "news" in q:
         print("DEBUG: News triggered")
         return self.s.get_news()
     
# ─── Main Loop ────────────────────────────────────────────────────────────────
def main():
    print_banner()

    voice  = VoiceEngine()
    ear    = EarEngine()
    brain  = Brain()
    skills = Skills()
    router = CommandRouter(skills, brain, voice)

    ear.calibrate()
    voice.speak(
        f"J.A.R.V.I.S. online. All systems nominal. "
        f"Say '{WAKE_WORD}' to wake me, or type your command.",
        silent=False,
    )

    print(f"\n{Fore.WHITE}╔══════════════════════════════════════════════════╗")
    print(f"║  {Fore.GREEN}Mode: Voice + Text{Fore.WHITE}  |  Wake word: '{WAKE_WORD.upper()}'{Fore.WHITE}  ║")
    print(f"╚══════════════════════════════════════════════════╝{Style.RESET_ALL}\n")

    # Allow text input as well
    text_thread_active = threading.Event()
    command_queue: list[str] = []

    def text_input_loop():
        while True:
            try:
                cmd = input(f"{Fore.MAGENTA}You (text):{Style.RESET_ALL} ").strip()
                if cmd:
                    command_queue.append(cmd)
            except (EOFError, KeyboardInterrupt):
                break

    threading.Thread(target=text_input_loop, daemon=True).start()

    awake = False  # Needs wake word first in voice mode

    while True:
        # ── Process text input if available ──────────────────────────────
        if command_queue:
            cmd = command_queue.pop(0)
            print(f"\n{Fore.MAGENTA}▶ You (text):{Style.RESET_ALL} {cmd}")
            response = router.route(cmd)
            voice.speak(response)
            continue

        # ── Voice listen cycle ────────────────────────────────────────────
        spoken = ear.listen(prompt=False)

        if spoken is None:
            continue

        print(f"\n{Fore.MAGENTA}▶ You (voice):{Style.RESET_ALL} {spoken}")

        spoken_lower = spoken.lower()

        if not awake:
            if WAKE_WORD in spoken_lower:
                awake = True
                voice.speak("Yes, sir? How can I assist you?")
            continue

        # If already awake, process the command
        response = router.route(spoken)
        voice.speak(response)

        # Go back to sleep after responding (optional: comment out to stay awake)
        awake = False
        print(f"\n{Style.DIM}💤  Sleeping… Say '{WAKE_WORD}' to wake me.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚡ Interrupted. Goodbye, sir.{Style.RESET_ALL}")
        sys.exit(0)
