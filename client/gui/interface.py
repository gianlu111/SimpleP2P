import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core.client import P2PClientCore


class P2PGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("P2P Platform")
        self.client = P2PClientCore()

        # Schermata iniziale di configurazione
        self.setup_frame = tk.Frame(self.root)
        self.setup_frame.pack(padx=10, pady=10)

        tk.Label(self.setup_frame, text="Tracker Host:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.tracker_host_entry = tk.Entry(self.setup_frame)
        self.tracker_host_entry.grid(row=0, column=1, padx=5, pady=5)
        self.tracker_host_entry.insert(0, self.client.settings['tracker_host'])

        tk.Label(self.setup_frame, text="Tracker Port:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.tracker_port_entry = tk.Entry(self.setup_frame)
        self.tracker_port_entry.grid(row=1, column=1, padx=5, pady=5)
        self.tracker_port_entry.insert(0, self.client.settings['tracker_port'])

        # Checkbox per abilitare la porta locale
        self.use_auto_port = tk.BooleanVar(value=True)
        self.local_port_checkbox = tk.Checkbutton(
            self.setup_frame, text="Porta automatica", variable=self.use_auto_port, command=self.toggle_local_port
        )
        self.local_port_checkbox.grid(row=2, column=0, sticky="w", padx=5, pady=5)

        # Casella di input per la porta locale
        self.local_port_entry = tk.Entry(self.setup_frame)
        self.local_port_entry.grid(row=2, column=1, padx=5, pady=5)
        self.local_port_entry.configure(state="disabled")
        if self.client.settings['local_port'] != 0:
            self.use_auto_port.set(False)
            self.local_port_entry.configure(state="normal")
            self.local_port_entry.insert(0, self.client.settings['local_port'])

        tk.Label(self.setup_frame, text="Peer Name:").grid(row=3, column=0, sticky="w", padx=5, pady=5)
        self.peer_name_entry = tk.Entry(self.setup_frame)
        self.peer_name_entry.grid(row=3, column=1, padx=5, pady=5)
        self.peer_name_entry.insert(0, self.client.settings['peer_name'])

        self.connect_button = tk.Button(self.setup_frame, text="Connetti", command=self.connect_to_tracker)
        self.connect_button.grid(row=4, column=0, columnspan=2, pady=10)



        # Frame principale con le schede
        self.main_frame = ttk.Notebook(self.root)

        self.main_frame.bind("<<NotebookTabChanged>>", self.on_tab_change)  

        self.files_tab = ttk.Frame(self.main_frame)
        self.shared_files_tab = ttk.Frame(self.main_frame)
        self.peers_tab = ttk.Frame(self.main_frame)
        self.settings_tab = ttk.Frame(self.main_frame)

        self.main_frame.add(self.files_tab, text="File Disponibili")
        self.main_frame.add(self.shared_files_tab, text="File Condivisi")
        self.main_frame.add(self.peers_tab, text="Peer Online")
        self.main_frame.add(self.settings_tab, text="Impostazioni")

        # Configurazione della tabella per File Disponibili
        self.files_list = tk.Listbox(self.files_tab)
        self.files_list.pack(fill="both", expand=True, padx=10, pady=10)
        

        self.refresh_files_button = tk.Button(self.files_tab, text="Aggiorna", command=self.list_files)
        self.refresh_files_button.pack(pady=5)
        self.download_file_button = tk.Button(self.files_tab, text="Download File", command=self.download_file)
        self.download_file_button.pack(pady=5)


        # Configurazione per File Condivisi
        self.shared_files_list = tk.Listbox(self.shared_files_tab)
        self.shared_files_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.share_file_button = tk.Button(self.shared_files_tab, text="Condividi File", command=self.share_file)
        self.share_file_button.pack(pady=5)

        self.unshare_file_button = tk.Button(self.shared_files_tab, text="Rimuovi Condivisione", command=self.unshare_file)
        self.unshare_file_button.pack(pady=5)

        # Configurazione per Peer Online
        self.peers_list = tk.Listbox(self.peers_tab)
        self.peers_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.refresh_peers_button = tk.Button(self.peers_tab, text="Aggiorna", command=self.list_peers)
        self.refresh_peers_button.pack(pady=5)

        # Tracker Status
        self.tracker_status_label = tk.Label(self.peers_tab, text="Stato Tracker: Non verificato", fg="gray")
        self.tracker_status_label.pack(pady=5)

        # Pianifica il primo aggiornamento dello stato
        self.check_tracker_status()




    def connect_to_tracker(self):
        tracker_host = self.tracker_host_entry.get()
        tracker_port = self.tracker_port_entry.get()
        local_port = self.local_port_entry.get()
        peer_name = self.peer_name_entry.get()

        try:
            tracker_port = int(tracker_port)
            local_port = int(local_port) if local_port else 0
        except ValueError:
            messagebox.showerror("Errore", "Porta deve essere un numero valido.")
            return
        self.client.settings['tracker_host'] = tracker_host
        self.client.settings['tracker_port'] = tracker_port
        self.client.settings['local_port'] = local_port
        self.client.settings['peer_name'] = peer_name

        self.build_settings_tab() # deve mostrare i settings dopo la modifica dal setup


        success, response = self.client.connect_to_tracker()
        if success:
            messagebox.showinfo("Successo", "Connessione al tracker avvenuta con successo.")
            self.setup_frame.pack_forget()
            self.main_frame.pack(fill="both", expand=True)
            self.list_files()
        else:
            messagebox.showerror("Errore", response)

    def list_files(self):
        if self.client and self.client.client_socket:
            success, response = self.client.list_files()
            if success:
                self.files_list.delete(0, tk.END)
                for file in response:
                    self.files_list.insert(tk.END, f"Nome: {file['name']} Size: {int(file['size'])/1024:.2f}KB SHA256: {file['hash']}")
            else:
                messagebox.showerror("Errore", response)
    def download_file(self):
        selected = self.files_list.curselection()
        if selected and self.client:
            file_hash = self.files_list.get(selected[0]).split()[-1]
            success, response = self.client.download_file(file_hash)
            if success:
                messagebox.showinfo("Successo", response)
            else:
                messagebox.showerror("Errore", response)
            self.list_files()
    def share_file(self):
        file_path = filedialog.askopenfilename()
        if file_path and self.client:
            success, response = self.client.share_file(file_path)
            if success:
                messagebox.showinfo("Successo", response)
                
            else:
                messagebox.showerror("Errore", response)
            self.list_shared_files()

    def unshare_file(self):
        selected = self.shared_files_list.curselection()
        if selected and self.client:
            file_hash = self.shared_files_list.get(selected[0]).split()[-1]
            success, response = self.client.unshare_file(file_hash)
            if success:
                messagebox.showinfo("Successo", response)
            else:
                messagebox.showerror("Errore", response)
            self.list_shared_files()
            
    def list_shared_files(self):
        if self.client:
            success, response = self.client.list_shared_files()
            if success:
                self.shared_files_list.delete(0, tk.END)
                for hash in response:
                    self.shared_files_list.insert(tk.END, f"Percorso: {response[hash]} SHA256: {hash}")
            else:
                messagebox.showerror("Errore", response)

    def list_peers(self):
        if self.client:
            success, response = self.client.list_peers()
            if success:
                self.peers_list.delete(0, tk.END)
                for peer in response:
                    self.peers_list.insert(tk.END, f"Nome: {peer['name']} IP: {peer['ip']} Porta: {peer['port']}")
            else:
                messagebox.showerror("Errore", response)

    def on_tab_change(self, event):
        selected_tab = event.widget.tab(event.widget.index("current"))["text"]
        if selected_tab == "File Disponibili":
            self.list_files()
        elif selected_tab == "File Condivisi":
            self.list_shared_files()
        elif selected_tab == "Peer Online":
            self.list_peers()
    def toggle_local_port(self):

        if self.use_auto_port.get():
            self.local_port_entry.delete(0, tk.END)
            self.local_port_entry.configure(state="disabled")
        else:
            self.local_port_entry.configure(state="normal")
            self.local_port_entry.insert(0, "8001")  # Valore di default

    def build_settings_tab(self):
        frame = self.settings_tab

        # Tracker Settings
        tracker_label = ttk.Label(frame, text="Indirizzo del Tracker:")
        tracker_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        self.tracker_host_var = tk.StringVar(value=self.client.settings['tracker_host'])
        tracker_entry = ttk.Entry(frame, textvariable=self.tracker_host_var)
        tracker_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        tracker_port_label = ttk.Label(frame, text="Porta del Tracker:")
        tracker_port_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        self.tracker_port_var = tk.IntVar(value=self.client.settings['tracker_port'])
        tracker_port_entry = ttk.Entry(frame, textvariable=self.tracker_port_var)
        tracker_port_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Peer Settings
        local_port_label = ttk.Label(frame, text="Porta Locale:")
        local_port_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

        self.local_port_var = tk.IntVar(value=self.client.settings['local_port'])
        local_port_entry = ttk.Entry(frame, textvariable=self.local_port_var)
        local_port_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        peer_name_label = ttk.Label(frame, text="Nome del Peer:")
        peer_name_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

        self.peer_name_var = tk.StringVar(value=self.client.settings['peer_name'])
        peer_name_entry = ttk.Entry(frame, textvariable=self.peer_name_var)
        peer_name_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        # Paths
        cache_folder_label = ttk.Label(frame, text="Cartella Cache:")
        cache_folder_label.grid(row=4, column=0, padx=10, pady=5, sticky="w")

        self.cache_folder_var = tk.StringVar(value=self.client.network.cache_folder)
        cache_folder_entry = ttk.Entry(frame, textvariable=self.cache_folder_var)
        cache_folder_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        cache_folder_button = ttk.Button(frame, text="Sfoglia", command=self.select_cache_folder)
        cache_folder_button.grid(row=4, column=2, padx=10, pady=5)

        download_folder_label = ttk.Label(frame, text="Cartella Download:")
        download_folder_label.grid(row=5, column=0, padx=10, pady=5, sticky="w")

        self.download_folder_var = tk.StringVar(value=self.client.network.download_folder)
        download_folder_entry = ttk.Entry(frame, textvariable=self.download_folder_var)
        download_folder_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

        download_folder_button = ttk.Button(frame, text="Sfoglia", command=self.select_download_folder)
        download_folder_button.grid(row=5, column=2, padx=10, pady=5)

        # Advanced Settings
        chunk_size_label = ttk.Label(frame, text="Dimensione Chunk (KB):")
        chunk_size_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")

        self.chunk_size_var = tk.IntVar(value=self.client.network.download_chunksize // 1024)
        chunk_size_entry = ttk.Entry(frame, textvariable=self.chunk_size_var)
        chunk_size_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # Buttons
        save_button = ttk.Button(frame, text="Salva", command=self.save_settings)
        save_button.grid(row=7, column=0, padx=10, pady=10, sticky="ew")

        reset_button = ttk.Button(frame, text="Ripristina Predefiniti", command=self.reset_settings)
        reset_button.grid(row=7, column=1, padx=10, pady=10, sticky="ew")

        frame.grid_columnconfigure(1, weight=1)

    def select_cache_folder(self):
        folder = filedialog.askdirectory(title="Seleziona Cartella Cache")
        if folder:
            self.cache_folder_var.set(folder)

    def select_download_folder(self):
        folder = filedialog.askdirectory(title="Seleziona Cartella Download")
        if folder:
            self.download_folder_var.set(folder)

    def save_settings(self):
        # Update ClientCore configuration
        self.client.settings['tracker_host'] = self.tracker_host_var.get()
        self.client.settings['tracker_port'] = self.tracker_port_var.get()
        self.client.settings['local_port'] = self.local_port_var.get()
        self.client.settings['peer_name'] = self.peer_name_var.get()
        self.client.network.cache_folder = self.cache_folder_var.get()
        self.client.network.download_folder = self.download_folder_var.get()
        self.client.network.download_chunksize = self.chunk_size_var.get() * 1024

        # Save shared files and notify user
        self.client.save_settings()
        messagebox.showinfo("Impostazioni", "Impostazioni salvate con successo!")

    def reset_settings(self):
        # Reset to default values
        self.tracker_host_var.set("127.0.0.1")
        self.tracker_port_var.set(8000)
        self.local_port_var.set(0)
        self.peer_name_var.set("Peer")
        self.cache_folder_var.set(os.path.join("..", "cache"))
        self.download_folder_var.set(os.path.join("..", "downloads"))
        self.chunk_size_var.set(64)
        messagebox.showinfo("Impostazioni", "Impostazioni ripristinate ai valori predefiniti.")

    def check_tracker_status(self):
        success = self.client.check_tracker_status()
        if success:
            self.tracker_status_label.config(text="Stato Tracker: Connesso", fg="green")
        else:
            self.tracker_status_label.config(text="Stato Tracker: Non connesso", fg="red")

        # Richiama questa funzione ogni 10 secondi
        self.root.after(10000, self.check_tracker_status)
if __name__ == "__main__":
    root = tk.Tk()
    gui = P2PGUI(root)
    root.mainloop()
