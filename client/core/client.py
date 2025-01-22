import socket
import json
from core.file_manager import FileManager
from core.network import P2PNetwork
import os
from core.utils import P2PUtils
class P2PClientCore: 
    def __init__(self, tracker_host="localhost", tracker_port=5000, local_port=0, peer_name="peer"):
        self.client_socket = None
        self.settings_path = "settings.json"
        self.settings = {
            "tracker_host": tracker_host,
            "tracker_port": tracker_port,
            "local_port": local_port,
            "peer_name": peer_name
        }

        self.network = P2PNetwork()
        self.load_settings()


    def connect_to_tracker(self):
        try:
            actual_port = self.network.start_file_server(self.settings['local_port']) # avvia il server per la condivisione dei file

            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.settings['tracker_host'], self.settings['tracker_port']))
            self.client_socket.send(f"HELLO {actual_port} {self.settings['peer_name']}\n".encode())
            response = self.client_socket.recv(1024).decode()

            return response == "OK", "Connesso al tracker"
        except Exception as e:
            return False, f"impossibile connettersi al tracker: {e}"
        
    def disconnect_from_tracker(self):
        try:
            #self.client_socket.send("BYE\n".encode())
            self.client_socket.close()
            return True, "Disconnesso dal tracker"
        except Exception as e:
            return False, f"Errore nella disconnessione dal tracker: {e}"
    def check_tracker_status(self):
        try:
            if self.client_socket:
                self.client_socket.send("PING\n".encode())
                response = self.client_socket.recv(1024).decode()
                return response == "PONG"
            return False
        except (socket.error, OSError):
            return False

    def save_settings(self):
        try:
            self.settings['cache_folder'] = self.network.cache_folder
            self.settings['download_folder'] = self.network.download_folder
            self.settings['download_chunksize'] = self.network.download_chunksize

            P2PUtils.save_json(self.settings_path, self.settings)
            print("Impostazioni salvate con successo.")
        except Exception as e:
            print(f"Errore durante il salvataggio delle impostazioni: {e}")

    def load_settings(self):
        try:
            if os.path.exists(self.settings_path):
                self.settings = P2PUtils.load_json(self.settings_path)
                self.network.cache_folder = self.settings.get('cache_folder', self.network.cache_folder)
                self.network.download_folder = self.settings.get('download_folder', self.network.download_folder)
                self.network.download_chunksize = self.settings.get('download_chunksize', self.network.download_chunksize)
                print("Impostazioni caricate con successo.")
            else:
                print("Nessun file di impostazioni trovato. Usando valori di default.")
        except Exception as e:
            print(f"Errore durante il caricamento delle impostazioni: {e}")
            print("Generazione di un file di impostazioni con valori di default...")
            self.save_settings()

    def list_peers(self): 
        try:
            self.client_socket.send("LIST\n".encode())
            response = json.loads(self.client_socket.recv(4096).decode())
            return True, response
        except Exception as e:
            return False, f"Error listing peers: {e}"
    def list_shared_files(self):
        return True, self.network.shared_files
    
    def share_file(self, file_path): # condivisione di un file con il tracker
        file_hash, error = FileManager.calculate_file_hash(file_path)
        if not file_hash:
            return False, error

        file_name = file_path.split("/")[-1]
        file_size = str(os.path.getsize(file_path))

        try:
            command = f"SHARE {file_hash} {file_name} {file_size}\n"
            self.client_socket.send(command.encode())
            response = self.client_socket.recv(1024).decode()
            if response == "FILES SHARED":
                self.network.share_file(file_hash, file_path)
                return True, f"{file_name} convidiviso!"
            else:
                return False, "Impossibile condividere il file."
        except Exception as e:
            return False, f"Errore nella condivisione: {e}"
        
    def unshare_file(self, file_hash): #unshare di un file
        try:
            command = f"UNSHARE {file_hash}\n"
            self.client_socket.send(command.encode())
            response = self.client_socket.recv(1024).decode() 
            self.network.share_file(file_hash, shared=False)
            if response == "FILE NOT FOUND":
                return False, "File non presente nel registro del server"
            return response == "FILE UNSHARED", response
        except Exception as e:
            return False, f"Errore nel unshare: {e}"

    def list_files(self):
        try:
            self.client_socket.send("LIST_FILES\n".encode())
            response = self.client_socket.recv(4096).decode()
            print(response)
            if response == "NO FILES AVAILABLE":
                return False, "No files available"
            return True, json.loads(response)
        except Exception as e:
            return False, f"Error listing files: {e}"
    def get_fileinfo(self, file_hash):
        try:
            self.client_socket.send(f"SEARCH {file_hash}\n".encode())
            online_peers = json.loads(self.client_socket.recv(1024).decode())
            self.client_socket.send(f"FILE_INFO {file_hash}\n".encode())
            file_size, file_name = self.client_socket.recv(1024).decode().split()
            print(f"File {file_hash} trovato su {online_peers} con dimensione {file_size}")
            return True, online_peers, int(file_size), file_name
        except Exception as e:
            return False, f"Errore nell'ottenimento delle informazioni: {e}"

    def download_file(self, file_hash):
        _, online_peers, file_size, file_name = self.get_fileinfo(file_hash)
        if not online_peers:
            return False, f"Nessun peer online con il file {file_hash}"
        if self.network.download_file(file_hash, file_size, online_peers):
            return self.assemble_file(file_hash, file_name)
        else:
            return False, f"Errore nel download del file"
    def assemble_file(self, file_hash, file_name):
        try:
            download_folder = self.network.download_folder

            if not os.path.exists(download_folder):
                os.makedirs(download_folder)
            cache_path = os.path.join(self.network.cache_folder, file_hash)
            download_path = os.path.join(download_folder, file_name)
            
            #chunk_files = sorted(os.listdir(cache_path), key=int)
            chunk_files = sorted(os.listdir(cache_path), key=lambda x: int(x.split('.')[0])) # ordina dopo aver tolto l'estensione

            with open(download_path, 'wb') as output_file:
                for chunk_file in chunk_files:
                    chunk_file_path = os.path.join(cache_path, chunk_file)
                    with open(chunk_file_path, 'rb') as cf:
                        output_file.write(cf.read())

            print(f"File {file_hash} assemblato con successo in {download_path}")
            return True, f"File {file_hash} assemblato con successo"
        except Exception as e:
            return False, f"Errore imprevisto : {e}"



