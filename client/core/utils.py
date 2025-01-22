import hashlib
import os
import json
class P2PUtils:
    @staticmethod # non richiede istanza
    def load_json(file_path):
        try:
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    return json.load(f)
            return {}
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"Errore durante il caricamento del file JSON: {e}")
            return {}
    @staticmethod
    def save_json(file_path, data):
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Errore durante il salvataggio del file JSON: {e}")
        
        