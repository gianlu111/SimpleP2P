import hashlib
import os

class FileManager:
    @staticmethod # non richiede istanza
    def calculate_file_hash(file_path):
        # calcolo dell hash del contenuto del file
        sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest(), None
        except Exception as e:
            return None, f"Errore nell`hashing: {e}"