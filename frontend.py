import customtkinter as ctk
import requests
import subprocess
import os


SERVER = "http://127.0.0.1:5000"
BASE_DIR = r"C:\PersonalAI"

PYTHON = os.path.join(
    BASE_DIR,
    "venv",
    "Scripts",
    "python.exe"
)

BACKGROUND = os.path.join(
    BASE_DIR,
    "background.py"
)


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class JarvisUI(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("JARVIS")
        self.geometry("1100x700")
        self.minsize(950, 600)

        self.jarvis_process = None

        # Local UI history. This prevents the chat from disappearing
        # when the backend replaces its status/message payload.
        self.chat_history = []
        self.seen_message_ids = set()

        self.current_page = "chat"
        self.server_online = False

        # =========================
        # MAIN LAYOUT
        # =========================

        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = ctk.CTkFrame(
            self,
            corner_radius=0
        )
        self.content.pack(side="right", fill="both", expand=True)

        # =========================
        # SIDEBAR
        # =========================

        logo = ctk.CTkLabel(
            self.sidebar,
            text="◉ JARVIS",
            font=("Segoe UI", 25, "bold")
        )
        logo.pack(padx=20, pady=(30, 35))

        self.chat_button = ctk.CTkButton(
            self.sidebar,
            text="💬   Chat",
            height=45,
            anchor="w",
            command=self.show_chat
        )
        self.chat_button.pack(fill="x", padx=15, pady=5)

        self.memory_button = ctk.CTkButton(
            self.sidebar,
            text="🧠   Memory",
            height=45,
            anchor="w",
            command=self.show_memory
        )
        self.memory_button.pack(fill="x", padx=15, pady=5)

        self.reminder_button = ctk.CTkButton(
            self.sidebar,
            text="🔔   Reminders",
            height=45,
            anchor="w",
            command=self.show_reminders
        )
        self.reminder_button.pack(fill="x", padx=15, pady=5)

        self.system_button = ctk.CTkButton(
            self.sidebar,
            text="⚙   System",
            height=45,
            anchor="w",
            command=self.show_system
        )
        self.system_button.pack(fill="x", padx=15, pady=5)

        self.sidebar_status = ctk.CTkLabel(
            self.sidebar,
            text="● CONNECTING",
            font=("Segoe UI", 12)
        )
        self.sidebar_status.pack(side="bottom", pady=25)

        # =========================
        # HEADER
        # =========================

        header = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        header.pack(fill="x", padx=30, pady=(25, 5))

        self.page_title = ctk.CTkLabel(
            header,
            text="Chat",
            font=("Segoe UI", 28, "bold")
        )
        self.page_title.pack(side="left")

        self.connection = ctk.CTkLabel(
            header,
            text="● CONNECTING",
            font=("Segoe UI", 13)
        )
        self.connection.pack(side="right")

        # =========================
        # STATUS
        # =========================

        self.status_frame = ctk.CTkFrame(self.content)
        self.status_frame.pack(fill="x", padx=30, pady=15)

        self.status_title = ctk.CTkLabel(
            self.status_frame,
            text="◉ STARTING",
            font=("Segoe UI", 30, "bold")
        )
        self.status_title.pack(pady=(20, 5))

        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Starting Jarvis...",
            font=("Segoe UI", 15)
        )
        self.status_text.pack(pady=(0, 20))

        # =========================
        # CHAT
        # =========================

        self.chat = ctk.CTkTextbox(
            self.content,
            font=("Segoe UI", 15),
            corner_radius=12
        )
        self.chat.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )
        self.chat.configure(state="disabled")

        # =========================
        # FOOTER
        # =========================

        footer = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )
        footer.pack(fill="x", padx=30, pady=15)

        self.mic_label = ctk.CTkLabel(
            footer,
            text="🎤 Microphone",
            font=("Segoe UI", 13)
        )
        self.mic_label.pack(side="left")

        self.version_label = ctk.CTkLabel(
            footer,
            text="JARVIS AI • Local",
            font=("Segoe UI", 11)
        )
        self.version_label.pack(side="right")

        # =========================
        # START
        # =========================

        self.start_jarvis()

        self.after(1000, self.update_ui)

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_app
        )

    # =========================
    # START JARVIS
    # =========================

    def start_jarvis(self):
        try:
            self.jarvis_process = subprocess.Popen(
                [PYTHON, BACKGROUND],
                cwd=BASE_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self.add_message(
                "SYSTEM",
                "Jarvis background assistant started."
            )

        except Exception as e:
            self.add_message(
                "SYSTEM",
                f"Could not start Jarvis: {e}"
            )

    # =========================
    # UPDATE UI
    # =========================

    def update_ui(self):
        try:
            response = requests.get(
                f"{SERVER}/status",
                timeout=1
            )
            response.raise_for_status()

            data = response.json()
            self.server_online = True

            self.connection.configure(text="● CONNECTED")
            self.sidebar_status.configure(text="● SYSTEM ONLINE")

            status = data.get("status", "READY")
            message = data.get("message", 'Say "Hey Jarvis"')

            self.status_title.configure(
                text=f"◉ {status}"
            )

            self.status_text.configure(text=message)
            self.mic_label.configure(text="🎤 Microphone active")

            # Accept the backend's message history when available.
            messages = data.get("messages", [])

            if isinstance(messages, list):
                self.ingest_messages(messages)

        except Exception:
            self.server_online = False

            self.connection.configure(text="● OFFLINE")
            self.sidebar_status.configure(text="● OFFLINE")
            self.status_title.configure(text="◉ OFFLINE")
            self.status_text.configure(
                text="Jarvis server is not running."
            )
            self.mic_label.configure(
                text="🎤 Waiting for Jarvis..."
            )

        # Keep the chat visible whenever we are on the Chat page.
        if self.current_page == "chat":
            self.refresh_chat()

        if self.current_page == "memory":
            self.load_memory_data()
        elif self.current_page == "reminders":
            self.load_reminder_data()

        self.after(1000, self.update_ui)

    # =========================
    # INGEST CHAT MESSAGES
    # =========================

    def ingest_messages(self, messages):
        """
        Supports both message formats:
        1. {"id": ..., "speaker": ..., "text": ...}
        2. {"speaker": ..., "text": ...}

        If the backend provides IDs, they are used for exact de-duplication.
        Otherwise the message content is used as a stable fallback key.
        """

        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                continue

            speaker = str(
                message.get("speaker", "SYSTEM")
            ).strip()

            text = str(
                message.get("text", "")
            ).strip()

            if not text:
                continue

            message_id = message.get("id")

            if message_id is not None:
                key = f"id:{message_id}"
            else:
                key = f"msg:{speaker}|{text}"

            if key in self.seen_message_ids:
                continue

            self.seen_message_ids.add(key)

            self.chat_history.append({
                "speaker": speaker,
                "text": text
            })

    # =========================
    # CLEAR CONTENT
    # =========================

    def clear_page(self):
        self.status_frame.pack_forget()
        self.chat.pack_forget()

        if hasattr(self, "memory_panel"):
            self.memory_panel.destroy()
            del self.memory_panel

        if hasattr(self, "reminder_panel"):
            self.reminder_panel.destroy()
            del self.reminder_panel

        if hasattr(self, "system_panel"):
            self.system_panel.destroy()
            del self.system_panel

    # =========================
    # CHAT
    # =========================

    def show_chat(self):
        self.current_page = "chat"

        self.clear_page()

        self.page_title.configure(text="Chat")

        self.status_frame.pack(
            fill="x",
            padx=30,
            pady=15
        )

        self.chat.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        self.refresh_chat()

    def refresh_chat(self):
        if not hasattr(self, "chat"):
            return

        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")

        if not self.chat_history:
            self.chat.insert(
                "end",
                'JARVIS\nReady. Say "Hey Jarvis" to begin.\n\n'
            )
        else:
            for item in self.chat_history:
                speaker = item.get("speaker", "SYSTEM")
                text = item.get("text", "")

                self.chat.insert(
                    "end",
                    f"{speaker}\n{text}\n\n"
                )

        self.chat.see("end")
        self.chat.configure(state="disabled")

    # =========================
    # MEMORY
    # =========================

    def show_memory(self):
        self.current_page = "memory"

        self.clear_page()

        self.page_title.configure(text="Memory")

        self.memory_panel = ctk.CTkTextbox(
            self.content,
            font=("Segoe UI", 15),
            corner_radius=12
        )
        self.memory_panel.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=20
        )

        self.load_memory_data()

    def load_memory_data(self):
        if not hasattr(self, "memory_panel"):
            return

        try:
            response = requests.get(
                f"{SERVER}/memories",
                timeout=2
            )
            response.raise_for_status()

            data = response.json()
            memories = data.get("memories", [])

            self.memory_panel.configure(state="normal")
            self.memory_panel.delete("1.0", "end")

            self.memory_panel.insert(
                "end",
                "🧠  JARVIS MEMORY\n\n"
            )

            if not memories:
                self.memory_panel.insert(
                    "end",
                    "No memories saved yet.\n\n"
                    'Say: "Remember that my favorite color is blue."'
                )
            else:
                for index, item in enumerate(
                    memories,
                    start=1
                ):
                    memory = item.get("memory", "")
                    created = item.get("created_at", "")

                    self.memory_panel.insert(
                        "end",
                        f"{index}. {memory}\n"
                    )

                    if created:
                        self.memory_panel.insert(
                            "end",
                            f"   Saved: {created}\n\n"
                        )
                    else:
                        self.memory_panel.insert(
                            "end",
                            "\n"
                        )

            self.memory_panel.configure(state="disabled")

        except Exception as e:
            self.memory_panel.configure(state="normal")
            self.memory_panel.delete("1.0", "end")
            self.memory_panel.insert(
                "end",
                "Could not load memories.\n\n"
                f"{e}"
            )
            self.memory_panel.configure(state="disabled")

    # =========================
    # REMINDERS
    # =========================

    def show_reminders(self):
        self.current_page = "reminders"

        self.clear_page()

        self.page_title.configure(text="Reminders")

        self.reminder_panel = ctk.CTkTextbox(
            self.content,
            font=("Segoe UI", 15),
            corner_radius=12
        )
        self.reminder_panel.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=20
        )

        self.load_reminder_data()

    def load_reminder_data(self):
        if not hasattr(self, "reminder_panel"):
            return

        try:
            response = requests.get(
                f"{SERVER}/reminders",
                timeout=2
            )
            response.raise_for_status()

            data = response.json()
            reminders = data.get("reminders", [])

            self.reminder_panel.configure(state="normal")
            self.reminder_panel.delete("1.0", "end")

            self.reminder_panel.insert(
                "end",
                "🔔  JARVIS REMINDERS\n\n"
            )

            if not reminders:
                self.reminder_panel.insert(
                    "end",
                    "No active reminders.\n\n"
                    'Say: "Remind me to drink water in 10 minutes."'
                )
            else:
                for index, item in enumerate(
                    reminders,
                    start=1
                ):
                    reminder = item.get("reminder", "")
                    remind_at = item.get("remind_at", "")

                    self.reminder_panel.insert(
                        "end",
                        f"{index}. {reminder}\n"
                        f"   Due: {remind_at}\n\n"
                    )

            self.reminder_panel.configure(state="disabled")

        except Exception as e:
            self.reminder_panel.configure(state="normal")
            self.reminder_panel.delete("1.0", "end")
            self.reminder_panel.insert(
                "end",
                "Could not load reminders.\n\n"
                f"{e}"
            )
            self.reminder_panel.configure(state="disabled")

    # =========================
    # SYSTEM
    # =========================

    def show_system(self):
        self.current_page = "system"

        self.clear_page()

        self.page_title.configure(text="System")

        self.system_panel = ctk.CTkTextbox(
            self.content,
            font=("Segoe UI", 15),
            corner_radius=12
        )
        self.system_panel.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=20
        )

        self.system_panel.insert(
            "end",
            "⚙  JARVIS SYSTEM\n\n"
            "AI Model: llama3.2:3b\n"
            "Speech Recognition: Whisper tiny\n"
            "Wake Word: Hey Jarvis\n"
            "Voice Engine: pyttsx3\n"
            "Memory: SQLite\n"
            "Web Search: DDGS\n"
            "Frontend: CustomTkinter\n"
            "Backend: Flask\n\n"
            "System status is monitored automatically."
        )

        self.system_panel.configure(state="disabled")

    # =========================
    # ADD MESSAGE
    # =========================

    def add_message(self, speaker, message):
        speaker = str(speaker).strip()
        message = str(message).strip()

        if not message:
            return

        key = f"local:{speaker}|{message}"

        if key in self.seen_message_ids:
            return

        self.seen_message_ids.add(key)

        self.chat_history.append({
            "speaker": speaker,
            "text": message
        })

        if self.current_page == "chat":
            self.refresh_chat()

    # =========================
    # CLOSE
    # =========================

    def close_app(self):
        # Jarvis continues running.
        self.destroy()


app = JarvisUI()
app.mainloop()
