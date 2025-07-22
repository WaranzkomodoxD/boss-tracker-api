import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageTk

# --- KONFIGURACJA SERWERA ---
# !!! WAŻNE: ZMIEŃ TO NA TWÓJ WŁAŚCIWY URL Z RENDER.COM !!!
# NA CZAS TESTÓW LOKALNYCH USTAWIJ "http://127.0.0.1:5000"
SERVER_URL = "https://boss-tracker-api.onrender.com"

# Co ile milisekund odpytywać SERWER o nowe dane (np. 3 sekundy)
UPDATE_SERVER_INTERVAL_MS = 3000

# Co ile milisekund odświeżać LOKALNE GUI (np. 1 sekundę)
# GUI odświeża się płynnie, nawet jeśli serwer odpytywany jest rzadziej
UPDATE_UI_INTERVAL_MS = 1000

# Konfiguracja bossów (taka sama jak w serwerze, aby uniknąć błędów)
BOSS_CONFIG = {
    "Szeptotruj #1": 40, "Szeptotruj #2": 40,
    "Skorpion #1": 40, "Skorpion #2": 40,
    "Serpentor #1": 41, "Serpentor #2": 41
}
CHANNELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"]
BOSS_STATE_FILE = "boss_state.json" # Plik do lokalnego cachowania stanu bossów

# --- Paleta kolorów dla Dark Mode ---
colors = {
    "bg": "#2e2e2e",
    "fg": "#d0d0d0",
    "frame_bg": "#3c3c3c",
    "button": "#5a5a5a",
    "button_fg": "#ffffff",
    "separator": "#2e2e2e",
    "unknown": "#505050",
    "active": "#2f5d2f",
    "respawn_soon": "#8b3a3a",
    "respawn_later": "#6b2b2b",
    "reset_button_bg": "#4a4a4a",
    "reset_button_fg": "#f0f0f0"
}

# --- FUNKCJE POMOCNICZE (do ładowania/zapisywania lokalnego stanu) ---
def load_local_boss_state():
    """Ładuje ostatni znany stan bossów z lokalnego pliku JSON."""
    try:
        if os.path.exists(BOSS_STATE_FILE):
            with open(BOSS_STATE_FILE, 'r') as f:
                return json.load(f)
        else:
            return {}
    except (json.JSONDecodeError, Exception) as e:
        print(f"Błąd ładowania lokalnego stanu ({BOSS_STATE_FILE}): {e}")
        return {}

def save_local_boss_state(state):
    """Zapisuje bieżący stan bossów do lokalnego pliku JSON."""
    try:
        with open(BOSS_STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except IOError as e:
        print(f"Błąd zapisu lokalnego stanu do {BOSS_STATE_FILE}: {e}")

# --- KLASA APLIKACJI TKINTER ---
class BossTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wężowe Pole - Tracker Bossów (Wersja Sieciowa)")
        self.geometry("820x520")
        self.resizable(False, False)
        self.configure(bg=colors['bg'])

        self.reset_button_images = {}

        self.state = load_local_boss_state() # Wczytaj lokalny stan na start
        self.labels = {}

        self.create_ui()

        self.connection_status_label = tk.Label(self, text="Status: Łączenie z serwerem...", font=("Segoe UI", 9), bg=colors['bg'], fg="blue")
        self.connection_status_label.grid(row=len(CHANNELS) + 2, column=0, columnspan=len(BOSS_CONFIG) * 2 + 1, pady=5, sticky="w", padx=10)

        self.fetch_data_from_server() # Rozpoczynamy cykl pobierania danych z serwera (wolniej)
        self.update_statuses_ui() # Rozpoczynamy cykl aktualizacji statusów w UI (szybciej)

    def create_vertical_text_image(self, text, font_size=10, font_name="Segoe UI Bold", text_color=colors['reset_button_fg'], bg_color=colors['reset_button_bg']):
        try:
            font = ImageFont.truetype(font_name, font_size)
        except IOError:
            font = ImageFont.load_default()

        dummy_img = Image.new('RGBA', (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        img = Image.new('RGBA', (text_width + 4, text_height + 4), color=bg_color)
        draw = ImageDraw.Draw(img)
        draw.text((2, 2), text, font=font, fill=text_color)

        rotated_img = img.transpose(Image.Transpose.ROTATE_90)

        final_img = Image.new('RGBA', (rotated_img.width, rotated_img.height), color=bg_color)
        final_img.paste(rotated_img, (0, 0))

        return ImageTk.PhotoImage(final_img)

    def create_ui(self):
        num_boss_columns_in_frame = len(BOSS_CONFIG) * 2 - 1
        if len(BOSS_CONFIG) == 0:
            num_boss_columns_in_frame = 0

        tk.Label(self, text="Tracker Bossów - Wężowe Pole (Synchronizowany)", font=("Segoe UI", 12, "bold"), bg=colors['bg'], fg=colors['fg']).grid(row=0, column=0, columnspan=num_boss_columns_in_frame + 2, pady=5)

        main_header_frame = tk.Frame(self, bg=colors['frame_bg'])
        main_header_frame.grid(row=1, column=0, columnspan=num_boss_columns_in_frame + 1, padx=(10, 2), pady=5, sticky="ew")

        tk.Label(self, text="", bg=colors['bg']).grid(row=1, column=num_boss_columns_in_frame + 1, padx=(2, 10), sticky="ew")

        current_header_column_index = 0
        main_header_frame.grid_columnconfigure(0, weight=0)

        for c_idx, boss_name in enumerate(BOSS_CONFIG.keys()):
            if c_idx > 0:
                tk.Frame(main_header_frame, width=2, bg=colors['separator']).grid(row=0, column=current_header_column_index, sticky="ns")
                current_header_column_index += 1

            header_label = tk.Label(main_header_frame, text=boss_name, font=("Segoe UI", 9, "bold"), anchor="center", bg=colors['frame_bg'], fg=colors['fg'])
            header_label.grid(row=0, column=current_header_column_index, pady=2, sticky="ew")
            main_header_frame.grid_columnconfigure(current_header_column_index, weight=1)
            current_header_column_index += 1

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(num_boss_columns_in_frame + 1, weight=0)

        for r_idx, ch in enumerate(CHANNELS):
            frame = tk.LabelFrame(self, text=ch, padx=5, pady=5, font=("Segoe UI", 9, "bold"), labelanchor="nw", bg=colors['frame_bg'], fg=colors['fg'], bd=1)
            frame.grid(row=r_idx + 2, column=0, padx=(10, 2), pady=2, sticky="ew")

            reset_text = "RESET"
            self.reset_button_images[ch] = self.create_vertical_text_image(reset_text)

            reset_btn = tk.Button(self,
                                  image=self.reset_button_images[ch],
                                  compound="center",
                                  command=lambda ch_name=ch: self.reset_channel(ch_name),
                                  bg=colors['reset_button_bg'],
                                  fg=colors['reset_button_fg'],
                                  relief=tk.FLAT, borderwidth=0)
            reset_btn.grid(row=r_idx + 2, column=num_boss_columns_in_frame + 1, padx=(2, 10), sticky="ns", pady=2)

            current_channel_column_index = 0
            for c_idx, boss_name in enumerate(BOSS_CONFIG.keys()):
                if c_idx > 0:
                    tk.Frame(frame, width=2, bg=colors['separator']).grid(row=0, column=current_channel_column_index, sticky="ns")
                    current_channel_column_index += 1

                key = f"{ch}_{boss_name}"

                boss_elements_frame = tk.Frame(frame, bg=colors['frame_bg'], bd=1, relief="solid")
                boss_elements_frame.grid(row=0, column=current_channel_column_index, padx=2, pady=2, sticky="ew")

                boss_elements_frame.grid_columnconfigure(0, weight=1)
                boss_elements_frame.grid_columnconfigure(1, weight=1)

                btn = tk.Button(boss_elements_frame, text="Zbij", command=lambda k=key: self.toggle_kill(k), bg=colors['button'], fg=colors['button_fg'], relief=tk.FLAT, borderwidth=0)
                btn.grid(row=0, column=0, sticky="ew", padx=(0,1))

                label = tk.Label(boss_elements_frame, text="...", width=10, fg='white')
                label.grid(row=0, column=1, sticky="ew", padx=(1,0))

                self.labels[key] = label
                current_channel_column_index += 1

            for i in range(len(BOSS_CONFIG)):
                frame.grid_columnconfigure(i * 2, weight=1)

    def fetch_data_from_server(self):
        """Pobiera najnowsze dane o bossach z serwera i aktualizuje self.state."""
        try:
            response = requests.get(f"{SERVER_URL}/get_state", timeout=5)
            response.raise_for_status()
            new_state = response.json()

            if new_state != self.state:
                self.state = new_state
                save_local_boss_state(self.state)
                self.connection_status_label.config(text="Status: Połączono (dane zaktualizowane)", fg="green")
            else:
                self.connection_status_label.config(text="Status: Połączono (brak nowych danych)", fg="gray")

        except requests.exceptions.Timeout:
            self.connection_status_label.config(text="Status: Limit czasu połączenia. Serwer może się budzić...", fg="orange")
        except requests.exceptions.ConnectionError:
            self.connection_status_label.config(text="Status: Błąd połączenia (serwer offline?). Próbuję ponownie...", fg="red")
        except requests.exceptions.RequestException as e:
            self.connection_status_label.config(text=f"Status: Błąd serwera ({e}). Próbuję ponownie...", fg="red")
        except json.JSONDecodeError:
            self.connection_status_label.config(text="Status: Błąd danych z serwera (JSON). Próbuję ponownie...", fg="red")
        except Exception as e:
            self.connection_status_label.config(text=f"Status: Nieoczekiwany błąd ({type(e).__name__}: {e}).", fg="red")
        finally:
            self.after(UPDATE_SERVER_INTERVAL_MS, self.fetch_data_from_server)

    def _load_state_from_server_immediate(self):
        try:
            response = requests.get(f"{SERVER_URL}/get_state", timeout=5)
            response.raise_for_status()
            new_state = response.json()
            if new_state != self.state:
                self.state = new_state
                save_local_boss_state(self.state)
                self.connection_status_label.config(text="Status: Dane zaktualizowane natychmiast!", fg="darkgreen")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Błąd natychmiastowego pobierania stanu z serwera: {e}")
            self.connection_status_label.config(text="Status: Błąd natychmiastowej aktualizacji z serwera!", fg="red")
            return False

    def toggle_kill(self, key):
        if self.state.get(key):
            timestamp_to_send = None
        else:
            timestamp_to_send = datetime.now().isoformat()

        payload = {
            "key": key,
            "timestamp": timestamp_to_send
        }

        try:
            response = requests.post(f"{SERVER_URL}/update_boss_status", json=payload, timeout=5)
            response.raise_for_status()

            self._load_state_from_server_immediate()
            self.update_statuses_ui()
        except requests.exceptions.Timeout:
            messagebox.showerror("Błąd", f"Nie udało się zaktualizować statusu bossa {key}: Przekroczono limit czasu serwera.")
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Błąd aktualizacji", f"Nie udało się zaktualizować statusu bossa na serwerze: {e}")
        except Exception as e:
            messagebox.showerror("Błąd", f"Nieoczekiwany błąd podczas aktualizacji statusu: {e}")

    def reset_channel(self, channel):
        if messagebox.askyesno("Potwierdzenie", f"Na pewno zresetować wszystkie dane dla kanału {channel}?"):
            try:
                response = requests.post(f"{SERVER_URL}/reset_channel/{channel}", timeout=5)
                response.raise_for_status()

                self._load_state_from_server_immediate()
                self.update_statuses_ui()

                messagebox.showinfo("Sukces", f"Kanał {channel} został zresetowany na serwerze.")
            except requests.exceptions.Timeout:
                messagebox.showerror("Błąd", f"Nie udało się zresetować kanału {channel}: Przekroczono limit czasu serwera.")
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Błąd resetowania", f"Nie udało się zresetować kanału na serwerze: {e}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nieoczekiwany błąd podczas resetowania kanału: {e}")

    def update_statuses_ui(self):
        """Aktualizuje statusy bossów w interfejsie użytkownika na podstawie self.state (lokalnego)."""
        now = datetime.now()
        for ch in CHANNELS:
            for boss_name, minutes in BOSS_CONFIG.items():
                key = f"{ch}_{boss_name}"
                last_kill_timestamp = self.state.get(key)

                label = self.labels.get(key)

                if not label:
                    print(f"Ostrzeżenie: Etykieta dla klucza '{key}' nie została znaleziona w UI.")
                    continue

                if last_kill_timestamp:
                    try:
                        killed_at = datetime.fromisoformat(last_kill_timestamp)
                        respawn_time = killed_at + timedelta(minutes=minutes)
                        remaining = (respawn_time - now).total_seconds()

                        if remaining <= 0:
                            label.config(text="🟢 Aktywny", bg=colors['active'], fg='white')
                        elif remaining > 300:
                            mins = int(remaining // 60)
                            label.config(text=f"🔴 {mins} min", bg=colors['respawn_later'], fg='white')
                        else:
                            mins = int(remaining // 60)
                            secs = int(remaining % 60)
                            label.config(text=f"🔴 {mins}:{secs:02}", bg=colors['respawn_soon'], fg='white')
                    except ValueError:
                        label.config(text="Błąd czasu", bg=colors['unknown'], fg='red')
                else:
                    label.config(text="❓ Nieznany", bg=colors['unknown'], fg='white')

        self.after(UPDATE_UI_INTERVAL_MS, self.update_statuses_ui)

if __name__ == "__main__":
    app = BossTrackerApp()
    app.mainloop()