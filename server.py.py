import json
import os
from flask import Flask, request, jsonify

# Konfiguracja bossów (taka sama jak w kliencie)
BOSS_CONFIG = {
    "Szeptotruj #1": 40, "Szeptotruj #2": 40,
    "Skorpion #1": 40, "Skorpion #2": 40,
    "Serpentor #1": 41, "Serpentor #2": 41
}
CHANNELS = ["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"]
STATE_FILE = "boss_state.json" # Plik, który będzie przechowywać stan na serwerze

app = Flask(__name__)

# Funkcja do ładowania stanu bossów z pliku
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# Funkcja do zapisywania stanu bossów do pliku
def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

# Endpoint do pobierania całego stanu bossów
@app.route("/get_state", methods=["GET"])
def get_state():
    current_state = load_state()
    return jsonify(current_state)

# Endpoint do aktualizowania stanu pojedynczego bossa (zabicia/aktywacji)
@app.route("/update_boss_status", methods=["POST"])
def update_boss_status():
    data = request.get_json()
    key = data.get("key")
    timestamp = data.get("timestamp") # Może być None, jeśli boss jest usuwany
    
    if not key:
        return jsonify({"message": "Brak 'key' w zapytaniu."}), 400

    current_state = load_state()
    if timestamp:
        current_state[key] = timestamp
    else:
        current_state.pop(key, None) # Usuń, jeśli timestamp jest None
    
    save_state(current_state)
    return jsonify({"message": "Status bossa zaktualizowany."}), 200

# Endpoint do resetowania kanału
@app.route("/reset_channel/<channel_name>", methods=["POST"])
def reset_channel_server(channel_name):
    current_state = load_state()
    initial_keys_count = len(current_state) # Dla sprawdzenia czy coś się zmieniło
    
    keys_to_remove = [k for k in current_state if k.startswith(f"{channel_name}_")]
    for key in keys_to_remove:
        current_state.pop(key)
            
    save_state(current_state)
    
    if len(current_state) < initial_keys_count:
        return jsonify({"message": f"Kanał {channel_name} zresetowany."}), 200
    else:
        return jsonify({"message": f"Brak zmian dla kanału {channel_name} (lub kanał nie istnieje).", "keys_to_remove": keys_to_remove}), 200


if __name__ == "__main__":
    HOST_IP = '0.0.0.0' # MUSI być '0.0.0.0' dla Render.com
    PORT = int(os.environ.get("PORT", 5000)) # Render.com ustawi zmienną środowiskową PORT
                                             # Domyślnie 5000 dla lokalnego testowania
    print(f"Serwer Flask uruchomiony na http://{HOST_IP}:{PORT}")
    print(f"Stan bossów będzie przechowywany w pliku: {os.path.abspath(STATE_FILE)}")
    print("Upewnij się, że port 5000 jest otwarty w Twoim firewallu!")
    print("Jeśli koledzy są w innej sieci, potrzebne będzie przekierowanie portów na routerze lub ngrok.")
    
    app.run(host=HOST_IP, port=PORT, debug=False)