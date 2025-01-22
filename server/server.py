import socket
import threading
import json
import os
import signal
import sys

class P2PServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.server_port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, self.server_port))
        self.server_socket.listen()
        self.peer_registry = []  # [(socket, (ip, port), peer_name)]
        self.file_registry = {}  # {hash: (file_name, file_size, [peer1, peer2, ...])}
        self.load_data()
        self.is_running = True


        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown) # salvare


    def load_data(self):
        try:
            if os.path.exists("file_registry.json"):
                with open("file_registry.json", "r") as f:
                    # carica e converte direttamente i peer in tuple
                    self.file_registry = {
                        file_hash: (file_name, file_size, [tuple(peer) for peer in peer_list])
                        for file_hash, (file_name, file_size, peer_list) in json.load(f).items()
                    }
        except (json.JSONDecodeError, FileNotFoundError, OSError) as e:
            print(f"Errore durante il caricamento del registro dei file: {e}")
            self.file_registry = {}

    def save_data(self):
        try:
            with open("file_registry.json", "w") as f:
                json.dump(self.file_registry, f, indent=4)
        except Exception as e:
            print(f"Errore durante il salvataggio del registro dei file: {e}")

    def shutdown(self, signum, frame):
        print("Ricevuto segnale di terminazione. Salvataggio dei dati in corso...")
        self.is_running = False
        self.save_data()
        self.server_socket.close()
        sys.exit(0)

    def handle_client(self, client_socket, address):
        print(f"Nuova connessione da {address}")
        peer_address = None
        try:
            while True:
                data = client_socket.recv(4096).decode() #  buf_size obbligatorio e indica il max possibile
                if not data: #gestisci disconnessioni improvvise
                    break
                command = data.split()[0]
                args = data.split()[1:]


                if command == "HELLO": # Registra peer
                    if len(args) != 2:
                        client_socket.send("ERR".encode())
                        continue
                    peer_port = args[0]
                    peer_name = args[1:] 
                    peer_address = (address[0], int(peer_port)) # la porta dove il peer è in ascolto per la condivisione di file
                    self.peer_registry.append((client_socket, peer_address, peer_name[0]))
                    print(f"Peer {peer_name[0]} connesso da {peer_address}")
                    client_socket.send("OK".encode())
                    
                elif command == "LIST": # Lista peer
                    peer_list = [{"name": peer[2], "ip": peer[1][0], "port": peer[1][1]} for peer in self.peer_registry]
                    client_socket.send(json.dumps(peer_list).encode())
                elif command == "PING": 
                    client_socket.send("PONG".encode())

                elif command == "SHARE": # Condividi file
                    if len(args) % 3 != 0: #argomenti multipli di 3 x piu file
                        client_socket.send("ERR".encode())
                    else:
                        for i in range(0, len(args), 3):
                            file_hash = args[i]
                            file_name = args[i+1]
                            file_size = args[i+2]
                            if file_hash in self.file_registry:
                                if peer_address not in self.file_registry[file_hash][2]: #evita duplicati
                                    self.file_registry[file_hash][2].append(peer_address)
                            else:
                                self.file_registry[file_hash] = (file_name, file_size, [peer_address])
                        client_socket.send("FILES SHARED".encode())
                elif command == "FILE_INFO": # Info file
                    if len(args) != 1:
                        client_socket.send("ERR".encode())
                    else:
                        file_hash = args[0]
                        if file_hash in self.file_registry:
                            file_size = self.file_registry[file_hash][1]
                            file_name = self.file_registry[file_hash][0]
                            client_socket.send(f"{file_size} {file_name}".encode())
                        else:
                            client_socket.send("FILE NOT FOUND".encode())
                elif command == "UNSHARE": # Rimuovi condivisione file
                    if len(args) != 1:
                        client_socket.send("ERR".encode())
                    else:
                        file_hash = args[0]
                        if file_hash in self.file_registry:
                            if peer_address in self.file_registry[file_hash][2]:
                                self.file_registry[file_hash][2].remove(peer_address)
                                if not self.file_registry[file_hash][2]: # Se non ci sono più peer, rimuovi il file
                                    del self.file_registry[file_hash]
                                client_socket.send("FILE UNSHARED".encode())
                            else:
                                client_socket.send("ERR: Peer not sharing this file".encode())
                        else:
                            client_socket.send("FILE NOT FOUND".encode())
                elif command == "LIST_FILES":  # Lista con file_name, file_size e hash
                    if not self.file_registry:
                        client_socket.send("NO FILES AVAILABLE".encode())
                    else:
                        file_list = [
                            {"hash": file_hash, "name": file_name, "size": file_size}
                            for file_hash, (file_name, file_size, _) in self.file_registry.items()
                        ]
                        client_socket.send(json.dumps(file_list).encode())

                elif command == "SEARCH": # Cerca file con hash
                    file_hash = args[0]
                    if file_hash in self.file_registry:
                        peer_list = self.file_registry[file_hash][2]
                        # veririfica quali peer sono online
                        online_addresses = {p[1] for p in self.peer_registry}
                        online_peers = [peer for peer in peer_list if peer in online_addresses]
                        print(f"Peer online con il file {file_hash}: {online_peers}")
                        client_socket.send(json.dumps(online_peers).encode())
                    else:
                        client_socket.send("FILE NOT FOUND".encode())
        except ConnectionResetError:
            print(f"Client {peer_address} disconnesso.")
        finally:
            for peer in self.peer_registry:
                if peer[0] == client_socket and peer[1] == peer_address:
                    self.peer_registry.remove(peer)
                    break
            client_socket.close()
            print(f"Connessione con {peer_address} chiusa")

    def start(self):
        print(f"server in ascolto per connessioni sulla porta {self.server_port}...")
        while self.is_running:  # serve per la terminazione con i thread
            try:
                self.server_socket.settimeout(1.0) 
                client_socket, address = self.server_socket.accept()
                client_handler = threading.Thread(target=self.handle_client, args=(client_socket, address))
                client_handler.start()
            except socket.timeout:
                continue

if __name__ == "__main__":
    server = P2PServer()
    server.start()