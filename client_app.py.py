# client_app.py (ta wersja nie wymaga zmian w SERVER_URL na razie)
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import json
import os
import requests
from PIL import Image, ImageDraw, ImageFont, ImageTk

# --- KONFIGURACJA SERWERA ---
# WAŻNE: Zostaw to tak na razie. Zmienimy to po wdrożeniu na Render.com!
SERVER_URL = "http://127.0.0.1:5000" 


# Konfiguracja bossów (taka sama jak w serwerze, aby uniknąć błędów)
BOSS_CONFIG = {
    "Szeptotruj #1": 40, "Szeptotruj #2": 40,
    "Skorpion #1": 40, "Skorpion #2": 40,
    "Serpentor #1": 41, "Serpentor #2": 41
}
CHANNELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"]
STATE_FILE = "boss_state.json" # Ten plik nie będzie używany do synchronizacji, ale może zostać do backupu

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

class BossTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Wężowe Pole - Tracker Bossów (Wersja Sieciowa)")
        self.geometry("820x520") 
        self.resizable(False, False)
        self.configure(bg=colors['bg'])
        
        self.reset_button_images = {}
        
        self.state = {} 
        self.labels = {}
        
        self.create_ui()
        self.update_statuses()

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

    def load_state(self):
        try:
            response = requests.get(f"{SERVER_URL}/get_state")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            messagebox.showerror("Błąd połączenia", f"Nie można połączyć się z serwerem: {SERVER_URL}. Upewnij się, że serwer jest uruchomiony i adres jest poprawny.")
            return {}
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Błąd komunikacji", f"Wystąpił błąd podczas pobierania stanu: {e}")
            return {}

    def save_state(self):
        pass # Stan jest na serwerze

    def toggle_kill(self, key):
        current_timestamp = datetime.now().isoformat() if key not in self.state else None
        
        try:
            response = requests.post(f"{SERVER_URL}/update_boss_status", json={"key": key, "timestamp": current_timestamp})
            response.raise_for_status()
            self.state = self.load_state() 
            self.update_statuses()
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Błąd aktualizacji", f"Nie udało się zaktualizować statusu bossa na serwerze: {e}")

    def reset_channel(self, channel):
        if messagebox.askyesno("Potwierdzenie", f"Na pewno zresetować wszystkie dane dla kanału {channel}?"):
            try:
                response = requests.post(f"{SERVER_URL}/reset_channel/{channel}")
                response.raise_for_status()
                self.state = self.load_state()
                self.update_statuses()
            except requests.exceptions.RequestException as e:
                messagebox.showerror("Błąd resetowania", f"Nie udało się zresetować kanału na serwerze: {e}")

    def update_statuses(self):
        self.state = self.load_state() 

        now = datetime.now()
        for ch in CHANNELS:
            for boss, minutes in BOSS_CONFIG.items():
                key = f"{ch}_{boss}"
                last_kill = self.state.get(key)
                label = self.labels[key]
                
                if last_kill:
                    killed_at = datetime.fromisoformat(last_kill)
                    respawn_time = killed_at + timedelta(minutes=minutes)

                    remaining = (respawn_time - now).total_seconds()

                    if remaining <= 0:
                        label.config(text="🟢 Aktywny", bg=colors['active'])
                    elif remaining > 300:
                        mins = int(remaining // 60)
                        label.config(text=f"🔴 {mins} min", bg=colors['respawn_later'])
                    else:
                        mins = int(remaining // 60)
                        secs = int(remaining % 60)
                        label.config(text=f"🔴 {mins}:{secs:02}", bg=colors['respawn_soon'])
                else:
                    label.config(text="❓ Nieznany", bg=colors['unknown'])
        self.after(1000, self.update_statuses)

if __name__ == "__main__":
    app = BossTrackerApp()
    app.mainloop()