import customtkinter as ctk
import requests
import subprocess
import os
import sys
import ctypes
from ctypes import wintypes
from PIL import Image


# ========================================================
# SINGLE FRONTEND INSTANCE
# ========================================================

ERROR_ALREADY_EXISTS = 183

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

CreateMutexW = kernel32.CreateMutexW
CreateMutexW.argtypes = [
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.LPCWSTR
]
CreateMutexW.restype = wintypes.HANDLE

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [
    wintypes.HANDLE
]
CloseHandle.restype = wintypes.BOOL


FRONTEND_MUTEX = CreateMutexW(
    None,
    False,
    "Local\\JARVIS_Frontend"
)

if not FRONTEND_MUTEX:
    raise ctypes.WinError(ctypes.get_last_error())

mutex_error = ctypes.get_last_error()

if mutex_error == ERROR_ALREADY_EXISTS:
    print("JARVIS frontend is already running.")
    CloseHandle(FRONTEND_MUTEX)
    sys.exit(0)

print("JARVIS frontend instance lock acquired.")


# ========================================================
# PATHS
# ========================================================

try:
    from paths import PATHS

except ImportError:

    BASE_DIR = os.path.dirname(
        os.path.abspath(__file__)
    )

    PATHS = {
        "BASE_DIR": BASE_DIR,
        "FRONTEND": os.path.join(
            BASE_DIR,
            "frontend.py"
        ),
        "BACKGROUND": os.path.join(
            BASE_DIR,
            "background.py"
        ),
        "SERVER": os.path.join(
            BASE_DIR,
            "server.py"
        ),
        "VENV": os.path.join(
            BASE_DIR,
            "venv"
        ),
        "PYTHON": os.path.join(
            BASE_DIR,
            "venv",
            "Scripts",
            "python.exe"
        ),
        "SERVER_URL": "http://127.0.0.1:5000",
    }


BASE_DIR = PATHS["BASE_DIR"]
PYTHON = PATHS["PYTHON"]
BACKGROUND = PATHS["BACKGROUND"]
SERVER_SCRIPT = PATHS["SERVER"]
SERVER = PATHS["SERVER_URL"]


# ========================================================
# FILES
# ========================================================

LOGO_FILE = os.path.join(
    BASE_DIR,
    "jarvis_icon.png"
)

ICON_FILE = os.path.join(
    BASE_DIR,
    "jarvis.ico"
)


# ========================================================
# CUSTOMTKINTER
# ========================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ========================================================
# JARVIS UI
# ========================================================

class JarvisUI(ctk.CTk):

    def __init__(self):

        super().__init__()

        # ------------------------------------------------
        # WINDOW
        # ------------------------------------------------

        self.title("JARVIS")

        self.geometry(
            "1100x700"
        )

        self.minsize(
            950,
            600
        )

        # ------------------------------------------------
        # WINDOW ICON
        # ------------------------------------------------

        if os.path.exists(ICON_FILE):

            try:
                self.iconbitmap(
                    ICON_FILE
                )

            except Exception:
                pass

        # ------------------------------------------------
        # PROCESS REFERENCES
        # ------------------------------------------------

        self.jarvis_process = None
        self.server_process = None

        # ------------------------------------------------
        # UI STATE
        # ------------------------------------------------

        self.chat_history = []

        self.seen_message_ids = set()

        self.current_page = "chat"

        self.server_online = False

        self.closing = False

        # ------------------------------------------------
        # LOGO
        # ------------------------------------------------

        self.logo_image = None

        if os.path.exists(LOGO_FILE):

            try:

                logo_pil = Image.open(
                    LOGO_FILE
                ).convert("RGBA")

                self.logo_image = ctk.CTkImage(
                    light_image=logo_pil,
                    dark_image=logo_pil,
                    size=(58, 58)
                )

            except Exception as e:

                print(
                    "Logo loading error:",
                    e
                )

        # ------------------------------------------------
        # BUILD UI
        # ------------------------------------------------

        self.build_ui()

        # ------------------------------------------------
        # START SERVICES
        # ------------------------------------------------

        self.start_server()

        # Give Flask a moment to initialize before
        # starting the background assistant.
        self.after(
            500,
            self.start_jarvis
        )

        # ------------------------------------------------
        # UPDATE LOOP
        # ------------------------------------------------

        self.after(
            1000,
            self.update_ui
        )

        # ------------------------------------------------
        # WINDOW CLOSE
        # ------------------------------------------------

        self.protocol(
            "WM_DELETE_WINDOW",
            self.close_app
        )


    # ====================================================
    # UI
    # ====================================================

    def build_ui(self):

        # ------------------------------------------------
        # SIDEBAR
        # ------------------------------------------------

        self.sidebar = ctk.CTkFrame(
            self,
            width=220,
            corner_radius=0
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(
            False
        )

        # ------------------------------------------------
        # CONTENT
        # ------------------------------------------------

        self.content = ctk.CTkFrame(
            self,
            corner_radius=0
        )

        self.content.pack(
            side="right",
            fill="both",
            expand=True
        )

        # ------------------------------------------------
        # LOGO + TITLE
        # ------------------------------------------------

        logo_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )

        logo_frame.pack(
            fill="x",
            padx=15,
            pady=(22, 30)
        )

        if self.logo_image:

            logo_image_label = ctk.CTkLabel(
                logo_frame,
                image=self.logo_image,
                text=""
            )

            logo_image_label.pack(
                side="left",
                padx=(4, 10)
            )

        else:

            logo_image_label = ctk.CTkLabel(
                logo_frame,
                text="◉",
                font=("Segoe UI", 30, "bold")
            )

            logo_image_label.pack(
                side="left",
                padx=(4, 10)
            )

        logo_text = ctk.CTkLabel(
            logo_frame,
            text="JARVIS",
            font=("Segoe UI", 25, "bold")
        )

        logo_text.pack(
            side="left"
        )

        # ------------------------------------------------
        # NAVIGATION
        # ------------------------------------------------

        self.chat_button = ctk.CTkButton(
            self.sidebar,
            text="💬   Chat",
            height=45,
            anchor="w",
            command=self.show_chat
        )

        self.chat_button.pack(
            fill="x",
            padx=15,
            pady=5
        )

        self.memory_button = ctk.CTkButton(
            self.sidebar,
            text="🧠   Memory",
            height=45,
            anchor="w",
            command=self.show_memory
        )

        self.memory_button.pack(
            fill="x",
            padx=15,
            pady=5
        )

        self.reminder_button = ctk.CTkButton(
            self.sidebar,
            text="🔔   Reminders",
            height=45,
            anchor="w",
            command=self.show_reminders
        )

        self.reminder_button.pack(
            fill="x",
            padx=15,
            pady=5
        )

        self.system_button = ctk.CTkButton(
            self.sidebar,
            text="⚙   System",
            height=45,
            anchor="w",
            command=self.show_system
        )

        self.system_button.pack(
            fill="x",
            padx=15,
            pady=5
        )

        self.credits_button = ctk.CTkButton(
            self.sidebar,
            text="©   Credits",
            height=45,
            anchor="w",
            command=self.show_credits
        )

        self.credits_button.pack(
            fill="x",
            padx=15,
            pady=5
        )

        # ------------------------------------------------
        # SIDEBAR STATUS
        # ------------------------------------------------

        self.sidebar_status = ctk.CTkLabel(
            self.sidebar,
            text="● CONNECTING",
            font=("Segoe UI", 12)
        )

        self.sidebar_status.pack(
            side="bottom",
            pady=25
        )

        # ------------------------------------------------
        # HEADER
        # ------------------------------------------------

        header = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        header.pack(
            fill="x",
            padx=30,
            pady=(25, 5)
        )

        self.page_title = ctk.CTkLabel(
            header,
            text="Chat",
            font=("Segoe UI", 28, "bold")
        )

        self.page_title.pack(
            side="left"
        )

        self.connection = ctk.CTkLabel(
            header,
            text="● CONNECTING",
            font=("Segoe UI", 13)
        )

        self.connection.pack(
            side="right"
        )

        # ------------------------------------------------
        # STATUS
        # ------------------------------------------------

        self.status_frame = ctk.CTkFrame(
            self.content
        )

        self.status_frame.pack(
            fill="x",
            padx=30,
            pady=15
        )

        self.status_title = ctk.CTkLabel(
            self.status_frame,
            text="◉ STARTING",
            font=("Segoe UI", 30, "bold")
        )

        self.status_title.pack(
            pady=(20, 5)
        )

        self.status_text = ctk.CTkLabel(
            self.status_frame,
            text="Starting Jarvis...",
            font=("Segoe UI", 15)
        )

        self.status_text.pack(
            pady=(0, 20)
        )

        # ------------------------------------------------
        # CHAT
        # ------------------------------------------------

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

        self.chat.configure(
            state="disabled"
        )

        # ------------------------------------------------
        # FOOTER
        # ------------------------------------------------

        footer = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        footer.pack(
            fill="x",
            padx=30,
            pady=15
        )

        self.mic_label = ctk.CTkLabel(
            footer,
            text="🎤 Microphone",
            font=("Segoe UI", 13)
        )

        self.mic_label.pack(
            side="left"
        )

        self.version_label = ctk.CTkLabel(
            footer,
            text="JARVIS AI • Local",
            font=("Segoe UI", 11)
        )

        self.version_label.pack(
            side="right"
        )


    # ====================================================
    # START FLASK SERVER
    # ====================================================

    def start_server(self):

        if not os.path.exists(SERVER_SCRIPT):

            self.add_message(
                "SYSTEM",
                f"server.py not found:\n{SERVER_SCRIPT}"
            )

            return

        if not os.path.exists(PYTHON):

            self.add_message(
                "SYSTEM",
                f"Python environment not found:\n{PYTHON}"
            )

            return

        # ------------------------------------------------
        # CHECK IF SERVER ALREADY EXISTS
        # ------------------------------------------------

        try:

            response = requests.get(
                f"{SERVER}/status",
                timeout=0.5
            )

            if response.ok:

                print(
                    "JARVIS server already running."
                )

                return

        except Exception:
            pass

        # ------------------------------------------------
        # START SERVER
        # ------------------------------------------------

        try:

            self.server_process = subprocess.Popen(
                [
                    PYTHON,
                    SERVER_SCRIPT
                ],
                cwd=BASE_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            print(
                "JARVIS Flask server started."
            )

        except Exception as e:

            self.add_message(
                "SYSTEM",
                f"Could not start server:\n{e}"
            )


    # ====================================================
    # START BACKGROUND JARVIS
    # ====================================================

    def start_jarvis(self):

        if self.closing:
            return

        if not os.path.exists(BACKGROUND):

            self.add_message(
                "SYSTEM",
                f"background.py not found:\n{BACKGROUND}"
            )

            return

        if not os.path.exists(PYTHON):

            self.add_message(
                "SYSTEM",
                f"Python environment not found:\n{PYTHON}"
            )

            return

        # ------------------------------------------------
        # PREVENT DUPLICATE CHILD FROM THIS UI
        # ------------------------------------------------

        if (
            self.jarvis_process is not None
            and self.jarvis_process.poll() is None
        ):

            return

        # ------------------------------------------------
        # START BACKGROUND ASSISTANT
        # ------------------------------------------------

        try:

            self.jarvis_process = subprocess.Popen(
                [
                    PYTHON,
                    BACKGROUND
                ],
                cwd=BASE_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self.add_message(
                "SYSTEM",
                "Jarvis background assistant started."
            )

            print(
                "JARVIS background assistant started."
            )

        except Exception as e:

            self.add_message(
                "SYSTEM",
                f"Could not start Jarvis:\n{e}"
            )


    # ====================================================
    # UPDATE UI
    # ====================================================

    def update_ui(self):

        if self.closing:
            return

        try:

            response = requests.get(
                f"{SERVER}/status",
                timeout=1
            )

            response.raise_for_status()

            data = response.json()

            self.server_online = True

            self.connection.configure(
                text="● CONNECTED"
            )

            self.sidebar_status.configure(
                text="● SYSTEM ONLINE"
            )

            status = data.get(
                "status",
                "READY"
            )

            message = data.get(
                "message",
                'Say "Hey Jarvis"'
            )

            self.status_title.configure(
                text=f"◉ {status}"
            )

            self.status_text.configure(
                text=message
            )

            self.mic_label.configure(
                text="🎤 Microphone active"
            )

            messages = data.get(
                "messages",
                []
            )

            if isinstance(messages, list):

                self.ingest_messages(
                    messages
                )

        except Exception:

            self.server_online = False

            self.connection.configure(
                text="● OFFLINE"
            )

            self.sidebar_status.configure(
                text="● OFFLINE"
            )

            self.status_title.configure(
                text="◉ OFFLINE"
            )

            self.status_text.configure(
                text="Jarvis server is not running."
            )

            self.mic_label.configure(
                text="🎤 Waiting for Jarvis..."
            )

        # ------------------------------------------------
        # PAGE REFRESH
        # ------------------------------------------------

        if self.current_page == "chat":

            self.refresh_chat()

        elif self.current_page == "memory":

            self.load_memory_data()

        elif self.current_page == "reminders":

            self.load_reminder_data()

        # ------------------------------------------------
        # NEXT UPDATE
        # ------------------------------------------------

        if not self.closing:

            self.after(
                1000,
                self.update_ui
            )


    # ====================================================
    # CHAT MESSAGE INGESTION
    # ====================================================

    def ingest_messages(
        self,
        messages
    ):

        for message in messages:

            if not isinstance(
                message,
                dict
            ):
                continue

            speaker = str(
                message.get(
                    "speaker",
                    "SYSTEM"
                )
            ).strip()

            text = str(
                message.get(
                    "text",
                    ""
                )
            ).strip()

            if not text:
                continue

            message_id = message.get(
                "id"
            )

            if message_id is not None:

                key = f"id:{message_id}"

            else:

                key = (
                    f"msg:"
                    f"{speaker}|"
                    f"{text}"
                )

            if key in self.seen_message_ids:
                continue

            self.seen_message_ids.add(
                key
            )

            self.chat_history.append(
                {
                    "speaker": speaker,
                    "text": text
                }
            )


    # ====================================================
    # CLEAR PAGE
    # ====================================================

    def clear_page(self):

        self.status_frame.pack_forget()

        self.chat.pack_forget()

        if hasattr(
            self,
            "memory_panel"
        ):

            self.memory_panel.destroy()

            del self.memory_panel

        if hasattr(
            self,
            "reminder_panel"
        ):

            self.reminder_panel.destroy()

            del self.reminder_panel

        if hasattr(
            self,
            "system_panel"
        ):

            self.system_panel.destroy()

            del self.system_panel

        if hasattr(
            self,
            "credits_panel"
        ):

            self.credits_panel.destroy()

            del self.credits_panel


    # ====================================================
    # CHAT
    # ====================================================

    def show_chat(self):

        self.current_page = "chat"

        self.clear_page()

        self.page_title.configure(
            text="Chat"
        )

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

        if not hasattr(
            self,
            "chat"
        ):
            return

        self.chat.configure(
            state="normal"
        )

        self.chat.delete(
            "1.0",
            "end"
        )

        if not self.chat_history:

            self.chat.insert(
                "end",
                'JARVIS\n'
                'Ready. Say "Hey Jarvis" '
                'to begin.\n\n'
            )

        else:

            for item in self.chat_history:

                speaker = item.get(
                    "speaker",
                    "SYSTEM"
                )

                text = item.get(
                    "text",
                    ""
                )

                self.chat.insert(
                    "end",
                    f"{speaker}\n"
                    f"{text}\n\n"
                )

        self.chat.see(
            "end"
        )

        self.chat.configure(
            state="disabled"
        )


    # ====================================================
    # MEMORY
    # ====================================================

    def show_memory(self):

        self.current_page = "memory"

        self.clear_page()

        self.page_title.configure(
            text="Memory"
        )

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

        if not hasattr(
            self,
            "memory_panel"
        ):
            return

        try:

            response = requests.get(
                f"{SERVER}/memories",
                timeout=2
            )

            response.raise_for_status()

            data = response.json()

            memories = data.get(
                "memories",
                []
            )

            self.memory_panel.configure(
                state="normal"
            )

            self.memory_panel.delete(
                "1.0",
                "end"
            )

            self.memory_panel.insert(
                "end",
                "🧠  JARVIS MEMORY\n\n"
            )

            if not memories:

                self.memory_panel.insert(
                    "end",
                    "No memories saved yet.\n\n"
                    'Say: "Remember that my '
                    'favorite color is blue."'
                )

            else:

                for index, item in enumerate(
                    memories,
                    start=1
                ):

                    memory = item.get(
                        "memory",
                        ""
                    )

                    created = item.get(
                        "created_at",
                        ""
                    )

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

            self.memory_panel.configure(
                state="disabled"
            )

        except Exception as e:

            self.memory_panel.configure(
                state="normal"
            )

            self.memory_panel.delete(
                "1.0",
                "end"
            )

            self.memory_panel.insert(
                "end",
                f"Could not load memories.\n\n{e}"
            )

            self.memory_panel.configure(
                state="disabled"
            )


    # ====================================================
    # REMINDERS
    # ====================================================

    def show_reminders(self):

        self.current_page = "reminders"

        self.clear_page()

        self.page_title.configure(
            text="Reminders"
        )

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

        if not hasattr(
            self,
            "reminder_panel"
        ):
            return

        try:

            response = requests.get(
                f"{SERVER}/reminders",
                timeout=2
            )

            response.raise_for_status()

            data = response.json()

            reminders = data.get(
                "reminders",
                []
            )

            self.reminder_panel.configure(
                state="normal"
            )

            self.reminder_panel.delete(
                "1.0",
                "end"
            )

            self.reminder_panel.insert(
                "end",
                "🔔  JARVIS REMINDERS\n\n"
            )

            if not reminders:

                self.reminder_panel.insert(
                    "end",
                    "No active reminders.\n\n"
                    'Say: "Remind me to drink '
                    'water in 10 minutes."'
                )

            else:

                for index, item in enumerate(
                    reminders,
                    start=1
                ):

                    reminder = item.get(
                        "reminder",
                        ""
                    )

                    remind_at = item.get(
                        "remind_at",
                        ""
                    )

                    self.reminder_panel.insert(
                        "end",
                        f"{index}. {reminder}\n"
                        f"   Due: {remind_at}\n\n"
                    )

            self.reminder_panel.configure(
                state="disabled"
            )

        except Exception as e:

            self.reminder_panel.configure(
                state="normal"
            )

            self.reminder_panel.delete(
                "1.0",
                "end"
            )

            self.reminder_panel.insert(
                "end",
                f"Could not load reminders.\n\n{e}"
            )

            self.reminder_panel.configure(
                state="disabled"
            )


    # ====================================================
    # SYSTEM
    # ====================================================

    def show_system(self):

        self.current_page = "system"

        self.clear_page()

        self.page_title.configure(
            text="System"
        )

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
            f"JARVIS Folder:\n{BASE_DIR}\n\n"
            "Paths are controlled by paths.py."
        )

        self.system_panel.configure(
            state="disabled"
        )


    # ====================================================
    # CREDITS
    # ====================================================

    def show_credits(self):

        self.current_page = "credits"

        self.clear_page()

        self.page_title.configure(
            text="Credits"
        )

        self.credits_panel = ctk.CTkFrame(
            self.content,
            corner_radius=12
        )

        self.credits_panel.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=20
        )

        # ------------------------------------------------
        # TITLE
        # ------------------------------------------------

        credits_title = ctk.CTkLabel(
            self.credits_panel,
            text="JARVIS",
            font=("Segoe UI", 32, "bold")
        )

        credits_title.pack(
            pady=(30, 5)
        )

        credits_subtitle = ctk.CTkLabel(
            self.credits_panel,
            text="Made By",
            font=("Segoe UI", 16, "bold"),
            text_color="gray"
        )

        credits_subtitle.pack(
            pady=(0, 15)
        )

        # ------------------------------------------------
        # TEAM
        # ------------------------------------------------

        team_frame = ctk.CTkFrame(
            self.credits_panel,
            fg_color="transparent"
        )

        team_frame.pack(
            pady=10,
            padx=20,
            fill="both",
            expand=True
        )

        team_frame.grid_columnconfigure(
            0,
            weight=1
        )

        team_frame.grid_columnconfigure(
            1,
            weight=1
        )

        team_members = [
            (
                "G.Sravya",
                "FrontEnd Developer"
            ),
            (
                "B.Gagan",
                "BackEnd Developer"
            ),
            (
                "Ch.Satya",
                "AI Model Handler"
            ),
            (
                "D.Nishilitha",
                "Voice Recognition & Response Handler"
            )
        ]

        for i, (name, role) in enumerate(
            team_members
        ):

            name_label = ctk.CTkLabel(
                team_frame,
                text=name,
                font=("Segoe UI", 14, "bold"),
                anchor="e"
            )

            name_label.grid(
                row=i,
                column=0,
                padx=10,
                pady=8,
                sticky="e"
            )

            role_label = ctk.CTkLabel(
                team_frame,
                text=f"-- {role}",
                font=("Segoe UI", 14),
                text_color="gray75",
                anchor="w"
            )

            role_label.grid(
                row=i,
                column=1,
                padx=10,
                pady=8,
                sticky="w"
            )

        # ------------------------------------------------
        # FOOTER
        # ------------------------------------------------

        credits_footer = ctk.CTkLabel(
            self.credits_panel,
            text="JARVIS AI • Local Assistant",
            font=("Segoe UI", 12),
            text_color="gray"
        )

        credits_footer.pack(
            pady=(10, 25)
        )


    # ====================================================
    # ADD MESSAGE
    # ====================================================

    def add_message(
        self,
        speaker,
        message
    ):

        speaker = str(
            speaker
        ).strip()

        message = str(
            message
        ).strip()

        if not message:
            return

        key = (
            f"local:"
            f"{speaker}|"
            f"{message}"
        )

        if key in self.seen_message_ids:
            return

        self.seen_message_ids.add(
            key
        )

        self.chat_history.append(
            {
                "speaker": speaker,
                "text": message
            }
        )

        if self.current_page == "chat":

            self.refresh_chat()


    # ====================================================
    # CLOSE
    # ====================================================

    def close_app(self):

        if self.closing:
            return

        self.closing = True

        print(
            "Closing JARVIS frontend..."
        )

        # ------------------------------------------------
        # IMPORTANT:
        # Background JARVIS is intentionally kept running.
        # ------------------------------------------------

        self.destroy()


# ========================================================
# START APPLICATION
# ========================================================

if __name__ == "__main__":

    app = JarvisUI()

    app.mainloop()
