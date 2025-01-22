import socket
import threading
import os
from queue import Queue

class MultiPeerDownloader:
    def __init__(self, cache_folder, download_chunksize):
        self.cache_folder = cache_folder
        self.download_chunksize = download_chunksize

    def download_file(self, file_hash, file_size, peers):
        chunksize = self.download_chunksize
        num_chunks = (file_size + chunksize - 1) // chunksize
        cache_path = os.path.join(self.cache_folder, file_hash)
        print(cache_path)
        
        if not os.path.exists(cache_path):
            os.makedirs(cache_path)

        # coda dei chunk
        chunks_queue = Queue()
        for chunk_index in range(num_chunks):
            chunks_queue.put(chunk_index)

        def download_from_peer(peer, chunks_queue):
            peer_ip, peer_port = peer
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((peer_ip, peer_port))
                    s.sendall(f"CHUNKSIZE {chunksize}\n".encode())
                    response = s.recv(1024).decode()
                    if response.strip() != "OK":
                        print(f"Il peer {peer_ip}:{peer_port} non ha accettato la dimensione del chunk.")
                        return

                    while not chunks_queue.empty():
                        try:
                            chunk_index = chunks_queue.get_nowait()  # ottiene chunk da qeueu
                            print(f"Scaricando chunk {chunk_index} da {peer_ip}:{peer_port}")
                            s.sendall(f"GET {file_hash} {chunk_index}\n".encode())
                            chunk = s.recv(chunksize)
                            if chunk:
                                chunk_file_path = os.path.join(cache_path, f"{chunk_index}.chunk")
                                with open(chunk_file_path, "wb") as chunk_file:
                                    chunk_file.write(chunk)
                                print(f"Chunk {chunk_index} scaricato da {peer_ip}:{peer_port}")
                            else:
                                raise Exception("Dati del chunk vuoti")
                        except Exception as e:
                            print(f"Problema con chunk {chunk_index} da {peer_ip}:{peer_port}: {e}")
                            chunks_queue.put(chunk_index) 
                        finally:
                            chunks_queue.task_done()
            except Exception as e:
                print(f"Impossibile connettersi al peer {peer_ip}:{peer_port}: {e}")

        # crea un thread per ogni peer disponibile, mantiene però lo stesso socket (1 socket a peer)
        threads = []
        for peer in peers:
            t = threading.Thread(target=download_from_peer, args=(peer, chunks_queue))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        # controlla se tutti i chunk sono stati scaricati
        if chunks_queue.empty():
            print("[Completato] Tutti i chunk scaricati con successo.")
            return True
        else:
            print("[Errore] Non tutti i chunk sono stati scaricati.")
            return False
