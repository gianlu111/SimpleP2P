import socket
import threading
import os
import json
import time
from core.downloader import MultiPeerDownloader
from core.utils import P2PUtils

class P2PNetwork:
    def __init__(self):
        #self.post_chunk_size = 1024  # 
        self.download_chunksize = 64 * 1024 # Chunk size default dei download 64KB
        self.shared_files = {}  # {hash: file_path}
        self.cache_folder = os.path.join("..", "cache")
        self.download_folder = os.path.join("..", "downloads")
        self.shared_files_path = "shared_files.json"
        self.load_shared_files()
        

    def load_shared_files(self):
        self.shared_files = P2PUtils.load_json(self.shared_files_path)


    def save_shared_files(self):
        P2PUtils.save_json(self.shared_files_path, self.shared_files)

    def share_file(self, file_hash, file_path=None, shared=True):
        if shared:
            self.shared_files[file_hash] = file_path
            print(f"File {file_path} condiviso con hash {file_hash}")
        else:
            if file_hash in self.shared_files:
                del self.shared_files[file_hash]
                print(f"File con hash {file_hash} rimosso dalla condivisione")
        self.save_shared_files()

    def download_file(self, hash, file_size, peers):
        downloader = MultiPeerDownloader(self.cache_folder, self.download_chunksize)
        return downloader.download_file(hash, file_size, peers)
        """ chunksize = self.download_chunksize
        num_chunks = (file_size + chunksize - 1) // chunksize #?????
        chunks_to_download = list(range(num_chunks))
        print(f"Donwoload di {num_chunks} chunks")
        cache_path = os.path.join(self.cache_folder, hash)
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)
        while chunks_to_download:
            chunk_index = chunks_to_download.pop(0)
            for peer in peers:
                try:
                    peer_ip, peer_port = peer
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((peer_ip, peer_port))
                        s.sendall(f"CHUNKSIZE {chunksize}\n".encode())
                        response = s.recv(1024).decode()
                        print(response)
                        if response == "OK\n":
                            print(f"Richiesta del chunk {chunk_index} a {peer_ip}:{peer_port}")
                            s.sendall(f"GET {hash} {chunk_index}\n".encode())
                        chunk = s.recv(chunksize) # buffer fisso a chunksize
                        if chunk:
                            chunk_file_path = os.path.join(cache_path, f"{chunk_index}.chunk")
                            with open(chunk_file_path, "wb") as chunk_file:
                                chunk_file.write(chunk)
                            print(f"Chunk {chunk_index} scaricato da {peer_ip}:{peer_port}")
                            break
                except Exception as e:
                    print(f"Errorenel download del chunk {chunk_index} da {peer_ip}:{peer_port} {e}")
                    chunks_to_download.append(chunk_index)
                    continue
        if not chunks_to_download:
            print("Download dei chunk completto con successo")
            return True
        else:
            print("Errore nel download di alcuni chunks")
            return False
         """

    def post_file_chunk(self, client_socket, file_path, index, chunk_size):
        try:
            
            offset = index * chunk_size
            with open(file_path, 'rb') as file:
                file.seek(offset)
                chunk = file.read(chunk_size)
                if chunk:
                    client_socket.sendall(chunk)
                    print(f"Chunk {index} è stato inviato")
                else:
                    print(f"Il chunk {index} non esiste")
        except FileNotFoundError:
            print(f"Errore: il file {file_path} non esiste")
        except Exception as e:
            print(f"Errore nell invio del chunk: {e}")

    
    def start_file_server(self, local_port):
        def handle_peer_request(client_socket, address):
            chunk_size = None
            try:
                while True:
                    data = client_socket.recv(1024).decode()
                    if not data:  # Condizione di uscita
                        break

                    print(f"Richiesta da {address}: {data}")
                    command = data.split()[0]
                    args = data.split()[1:]
                    if command == "CHUNKSIZE":
                        chunk_size = int(args[0])
                        client_socket.send("OK\n".encode())
                    elif command == "GET":
                        if chunk_size:
                            file_hash = args[0]
                            index = int(args[1])
                            if file_hash in self.shared_files:
                                file_path = self.shared_files[file_hash]
                                self.post_file_chunk(client_socket, file_path, index, chunk_size)
                            else:
                                raise Exception(f"File con hash {file_hash} non trovato")
                        else:
                            print("ERR: Chunk size non settato")
            except Exception as e:
                print(f"Errore durante la gestione della richiesta del peer: {e}")
            finally:
                print(f"Connessione chiusa con {address}")
                client_socket.close()

        actual_port = None

        def server_thread():
            nonlocal actual_port # per capire quale porta l'os ha assegnato (se 0)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind(("0.0.0.0", local_port))
                actual_port = server_socket.getsockname()[1]
                server_socket.listen()
                print(f"Server file avviato sulla porta {actual_port}")
                while True:
                    client_socket, address = server_socket.accept()
                    threading.Thread(target=handle_peer_request, args=(client_socket, address)).start()

        server_thread_instance = threading.Thread(target=server_thread, daemon=True)
        server_thread_instance.start()
        server_thread_instance.join(1)

        return actual_port
