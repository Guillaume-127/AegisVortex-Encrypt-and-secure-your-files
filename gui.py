import os
import threading
import queue
import customtkinter as ctk
from tkinter import filedialog, messagebox
import secu_files
import windnd

class AegisVortexGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔒 AEGIS-VORTEX V3.8 - MATRI-X STABILITY")
        self.geometry("750x650")
        ctk.set_appearance_mode("dark")
        
        # Thème Matrix Premium
        self.matrix_green = "#00FF41"
        self.matrix_dark = "#0D0208"
        self.font_mono = "Consolas"
        self.configure(fg_color=self.matrix_dark)

        # --- Communication Thread-Safe ---
        self.update_queue = queue.Queue()
        self.after(100, self.process_queue)

        # --- Variables ---
        self.target_path_enc = ctk.StringVar(value="")
        self.target_path_dec = ctk.StringVar(value="")
        self.password_enc = ctk.StringVar(value="")
        self.password_conf = ctk.StringVar(value="")
        self.password_dec = ctk.StringVar(value="")
        self.keep_original_enc = ctk.BooleanVar(value=True)
        self.keep_original_dec = ctk.BooleanVar(value=True)
        self.is_running = False

        # --- Layout Principal ---
        self.grid_columnconfigure(0, weight=1)
        
        # Header
        self.header_label = ctk.CTkLabel(self, text="AEGIS-VORTEX V3", 
                                        font=ctk.CTkFont(family=self.font_mono, size=32, weight="bold"),
                                        text_color=self.matrix_green)
        self.header_label.grid(row=0, column=0, padx=20, pady=(20, 5))

        self.subheader_label = ctk.CTkLabel(self, text="DEFENSE GRID: ACTIVE", 
                                           font=ctk.CTkFont(family=self.font_mono, size=14),
                                           text_color=self.matrix_green)
        self.subheader_label.grid(row=1, column=0, padx=20, pady=(0, 10))

        # --- Tabview ---
        self.tabview = ctk.CTkTabview(self, fg_color="#000000", border_color=self.matrix_green, 
                                      border_width=1, segmented_button_fg_color="#002200",
                                      segmented_button_selected_color="#004400",
                                      segmented_button_selected_hover_color="#006600",
                                      segmented_button_unselected_color="#000000",
                                      segmented_button_unselected_hover_color="#003300",
                                      text_color=self.matrix_green)
        self.tabview.grid(row=2, column=0, padx=20, pady=0, sticky="nsew")
        self.tabview.add(" >> ENCRYPT ")
        self.tabview.add(" >> DECRYPT ")
        
        # Style des boutons d'onglets
        self.tabview._segmented_button.configure(font=ctk.CTkFont(family=self.font_mono, weight="bold"))

        # --- ONGLET ENCRYPT ---
        self.enc_tab = self.tabview.tab(" >> ENCRYPT ")
        self.enc_tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.enc_tab, text="SOURCE_PATH >", font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")
        self.path_entry_enc = ctk.CTkEntry(self.enc_tab, textvariable=self.target_path_enc, font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", text_color=self.matrix_green, border_color=self.matrix_green, placeholder_text="Drag & Drop files or Scan...", placeholder_text_color="#006600", width=450)
        self.path_entry_enc.grid(row=1, column=0, padx=20, pady=5, sticky="we")
        ctk.CTkButton(self.enc_tab, text="SCAN", font=ctk.CTkFont(family=self.font_mono, weight="bold"), fg_color="#000000", border_width=1, border_color=self.matrix_green, hover_color="#003300", text_color=self.matrix_green, command=lambda: self.browse("enc"), width=80).grid(row=1, column=1, padx=(0, 20), pady=5)

        ctk.CTkLabel(self.enc_tab, text="ACCESS_KEY >", font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green).grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.pass_entry_enc = ctk.CTkEntry(self.enc_tab, textvariable=self.password_enc, font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", text_color=self.matrix_green, border_color=self.matrix_green, placeholder_text="Key...", show="*", width=550)
        self.pass_entry_enc.grid(row=3, column=0, columnspan=2, padx=20, pady=5, sticky="we")

        ctk.CTkLabel(self.enc_tab, text="CONFIRM_KEY >", font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green).grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")
        self.pass_conf_enc = ctk.CTkEntry(self.enc_tab, textvariable=self.password_conf, font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", text_color=self.matrix_green, border_color=self.matrix_green, placeholder_text="Confirm...", show="*", width=550)
        self.pass_conf_enc.grid(row=5, column=0, columnspan=2, padx=20, pady=5, sticky="we")

        enc_opt_frame = ctk.CTkFrame(self.enc_tab, fg_color="transparent")
        enc_opt_frame.grid(row=6, column=0, columnspan=2, padx=20, pady=15, sticky="w")
        ctk.CTkLabel(enc_opt_frame, text="COMPRESSION:", font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green).grid(row=0, column=0)
        self.comp_menu = ctk.CTkOptionMenu(enc_opt_frame, values=["Rapide", "Équilibré", "Maximum"], font=ctk.CTkFont(family=self.font_mono), 
                                          fg_color="#000000", button_color="#003300", button_hover_color="#006600", 
                                          dropdown_fg_color="#000000", dropdown_hover_color="#003300", dropdown_text_color=self.matrix_green,
                                          text_color=self.matrix_green, width=120)
        self.comp_menu.set("Rapide")
        self.comp_menu.grid(row=0, column=1, padx=10)
        
        self.keep_check_enc = ctk.CTkCheckBox(enc_opt_frame, text="KEEP_ORIGINAL", variable=self.keep_original_enc, font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green, fg_color="#000000", border_color=self.matrix_green, hover_color="#003300", checkmark_color=self.matrix_green)
        self.keep_check_enc.grid(row=0, column=2, padx=10)

        enc_btn_frame = ctk.CTkFrame(self.enc_tab, fg_color="transparent")
        enc_btn_frame.grid(row=7, column=0, columnspan=2, padx=20, pady=10, sticky="we")
        enc_btn_frame.grid_columnconfigure(0, weight=3)
        enc_btn_frame.grid_columnconfigure(1, weight=1)

        self.encrypt_btn = ctk.CTkButton(enc_btn_frame, text="[ EXECUTE_ENCRYPTION ]", font=ctk.CTkFont(family=self.font_mono, weight="bold"), fg_color="#000000", border_width=1, border_color=self.matrix_green, hover_color="#004400", text_color=self.matrix_green, height=45, command=lambda: self.start_action("enc"))
        self.encrypt_btn.grid(row=0, column=0, padx=(0, 10), sticky="we")
        
        ctk.CTkButton(enc_btn_frame, text="[ CLEAR ]", font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", border_width=1, border_color=self.matrix_green, hover_color="#003300", text_color=self.matrix_green, height=45, command=lambda: self.clear_fields("enc")).grid(row=0, column=1, sticky="we")

        # --- ONGLET DECRYPT ---
        self.dec_tab = self.tabview.tab(" >> DECRYPT ")
        self.dec_tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.dec_tab, text="TARGET_PATH (.127) >", font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green).grid(row=0, column=0, padx=20, pady=(15, 0), sticky="w")
        self.path_entry_dec = ctk.CTkEntry(self.dec_tab, textvariable=self.target_path_dec, font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", text_color=self.matrix_green, border_color=self.matrix_green, placeholder_text="Inject .127 file or Drag...", placeholder_text_color="#006600", width=450)
        self.path_entry_dec.grid(row=1, column=0, padx=20, pady=5, sticky="we")
        ctk.CTkButton(self.dec_tab, text="SCAN", font=ctk.CTkFont(family=self.font_mono, weight="bold"), fg_color="#000000", border_width=1, border_color=self.matrix_green, hover_color="#003300", text_color=self.matrix_green, command=lambda: self.browse("dec"), width=80).grid(row=1, column=1, padx=(0, 20), pady=5)

        ctk.CTkLabel(self.dec_tab, text="ACCESS_KEY >", font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green).grid(row=2, column=0, padx=20, pady=(10, 0), sticky="w")
        self.pass_entry_dec = ctk.CTkEntry(self.dec_tab, textvariable=self.password_dec, font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", text_color=self.matrix_green, border_color=self.matrix_green, placeholder_text="Unlock key...", show="*", width=550)
        self.pass_entry_dec.grid(row=3, column=0, columnspan=2, padx=20, pady=5, sticky="we")

        dec_opt_frame = ctk.CTkFrame(self.dec_tab, fg_color="transparent")
        dec_opt_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=15, sticky="w")
        self.keep_check_dec = ctk.CTkCheckBox(dec_opt_frame, text="KEEP_ORIGINAL (.127)", variable=self.keep_original_dec, font=ctk.CTkFont(family=self.font_mono), text_color=self.matrix_green, fg_color="#000000", border_color=self.matrix_green, hover_color="#003300", checkmark_color=self.matrix_green)
        self.keep_check_dec.grid(row=0, column=0)

        dec_btn_frame = ctk.CTkFrame(self.dec_tab, fg_color="transparent")
        dec_btn_frame.grid(row=5, column=0, columnspan=2, padx=20, pady=10, sticky="we")
        dec_btn_frame.grid_columnconfigure(0, weight=3)
        dec_btn_frame.grid_columnconfigure(1, weight=1)

        self.decrypt_btn = ctk.CTkButton(dec_btn_frame, text="[ EXECUTE_DECRYPTION ]", font=ctk.CTkFont(family=self.font_mono, weight="bold"), fg_color="#000000", border_width=1, border_color=self.matrix_green, hover_color="#004400", text_color=self.matrix_green, height=45, command=lambda: self.start_action("dec"))
        self.decrypt_btn.grid(row=0, column=0, padx=(0, 10), sticky="we")
        
        ctk.CTkButton(dec_btn_frame, text="[ CLEAR ]", font=ctk.CTkFont(family=self.font_mono), fg_color="#000000", border_width=1, border_color=self.matrix_green, hover_color="#003300", text_color=self.matrix_green, height=45, command=lambda: self.clear_fields("dec")).grid(row=0, column=1, sticky="we")

        # --- Footer ---
        self.progress_bar = ctk.CTkProgressBar(self, fg_color="#002200", progress_color=self.matrix_green)
        self.progress_bar.grid(row=3, column=0, padx=20, pady=(20, 10), sticky="we")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="SYSTEM READY.", font=ctk.CTkFont(family=self.font_mono, size=12), text_color=self.matrix_green)
        self.status_label.grid(row=4, column=0, padx=20, pady=(0, 20))

        # Drag & Drop
        windnd.hook_dropfiles(self, self.on_drop)
        self.header_label.focus() # Fix for placeholder display

    def clear_fields(self, mode):
        if mode == "enc":
            self.target_path_enc.set("")
            self.password_enc.set("")
            self.password_conf.set("")
        else:
            self.target_path_dec.set("")
            self.password_dec.set("")

    def process_queue(self):
        try:
            while True:
                msg = self.update_queue.get_nowait()
                m_type = msg.get("type")
                if m_type == "progress":
                    current, total = msg["current"], msg["total"]
                    val = current / total if total > 0 else 0
                    self.progress_bar.set(val)
                    self.status_label.configure(text=f">> DATA_FLOW: {current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB [{val*100:.1f}%]")
                elif m_type == "status":
                    self.status_label.configure(text=msg["text"])
                elif m_type == "messagebox":
                    if msg["m_type"] == "info": messagebox.showinfo(msg["title"], msg["text"])
                    elif msg["m_type"] == "error": messagebox.showerror(msg["title"], msg["text"])
                elif m_type == "reset":
                    self.is_running = False
                    self.progress_bar.set(0)
                    self.status_label.configure(text="SYSTEM READY.")
        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

    def on_drop(self, filenames):
        if filenames:
            path = filenames[0].decode('gbk') if isinstance(filenames[0], bytes) else filenames[0]
            if self.tabview.get() == " >> ENCRYPT ": self.target_path_enc.set(path)
            else: self.target_path_dec.set(path)
            self.status_label.configure(text=f">> SOURCE_INJECTED: {os.path.basename(path)}")

    def browse(self, mode):
        if mode == "enc":
            choice = messagebox.askquestion("SOURCE_TYPE", "Select FOLDER? (No for single FILE)")
            path = filedialog.askdirectory() if choice == 'yes' else filedialog.askopenfilename()
            if path: self.target_path_enc.set(path.replace("/", "\\"))
        else:
            path = filedialog.askopenfilename(filetypes=[("Secure Files", "*.127;*.enc")])
            if path: self.target_path_dec.set(path.replace("/", "\\"))

    def update_progress(self, current, total):
        self.update_queue.put({"type": "progress", "current": current, "total": total})

    def start_action(self, mode):
        if self.is_running: return
        if mode == "enc":
            path, pwd, pwd_conf = self.target_path_enc.get().strip('\"\''), self.password_enc.get(), self.password_conf.get()
            if not path or not pwd: return messagebox.showwarning("AUTH_REQUIRED", "Please provide credentials and source path.")
            if pwd != pwd_conf: return messagebox.showerror("SYNC_ERROR", "Keys do not match.")
        else:
            path, pwd = self.target_path_dec.get().strip('\"\''), self.password_dec.get()
            if not path or not pwd: return messagebox.showwarning("AUTH_REQUIRED", "Please provide credentials and target path.")

        self.is_running = True
        self.status_label.configure(text=">> INITIALIZING_CIPHER_ENGINE...")
        levels = {"Rapide": 1, "Équilibré": 3, "Maximum": 19}
        lvl = levels.get(self.comp_menu.get(), 3)

        def run():
            try:
                if mode == "enc":
                    keep = self.keep_original_enc.get()
                    res, msg = secu_files.encrypt_target(path, pwd, lvl, delete_original=not keep, progress_callback=self.update_progress)
                else:
                    keep = self.keep_original_dec.get()
                    res, msg = secu_files.decrypt_file(path, pwd, progress_callback=self.update_progress, delete_original=not keep)
                
                if res: self.update_queue.put({"type": "messagebox", "m_type": "info", "title": "SUCCESS", "text": f"PROCESS_COMPLETED: {msg}"})
                else: self.update_queue.put({"type": "messagebox", "m_type": "error", "title": "SECURITY_BREACH", "text": f"PROCESS_FAILED: {msg}"})
            except Exception as e: 
                self.update_queue.put({"type": "messagebox", "m_type": "error", "title": "CRITICAL_OVERFLOW", "text": str(e)})
            finally:
                self.update_queue.put({"type": "reset"})

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    app = AegisVortexGUI()
    app.mainloop()
