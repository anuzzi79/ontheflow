import flet as ft
import threading
import queue
import time
import datetime
import numpy as np
import soundcard as sc
import speech_recognition as sr
from faster_whisper import WhisperModel
import warnings
import sys
import os
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAZIONE E COSTANTI ---
SAMPLE_RATE = 16000
DEVICE_TYPE = "cpu"
COMPUTE_TYPE = "int8"
# Ignora warning
warnings.filterwarnings("ignore", category=UserWarning)
try:
    from soundcard.mediafoundation import SoundcardRuntimeWarning
    warnings.filterwarnings("ignore", category=SoundcardRuntimeWarning)
except ImportError:
    pass

class TranscriberApp:
    def __init__(self):
        self.is_recording = False
        self.stop_event = threading.Event()
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()  # Per risultati ordinati
        self.executor = None  # Creato dinamicamente
        self.chunk_counter = 0  # Contatore per ordinamento
        self.model = None
        self.current_model_name = ""
        self.log_file = ""
        
        # Stato UI
        self.page = None
        self.txt_output = None # Sarà una ListView
        
    def get_log_dir(self):
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        log_dir = os.path.join(docs, "LiveTranscriber_Logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return log_dir

    def get_timestamp(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def log_to_file(self, text):
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(text + "\n")
            except:
                pass

    def record_audio_thread(self, mic, buffer_seconds):
        """Cattura audio e lo etichetta con chunk_id e timestamp di cattura"""
        print(f"DEBUG: Start Recording Thread (Buffer: {buffer_seconds}s)")
        try:
            with mic.recorder(samplerate=SAMPLE_RATE) as recorder:
                while not self.stop_event.is_set():
                    try:
                        # Cattura timestamp PRIMA del recording (più accurato)
                        capture_time = datetime.datetime.now()
                        data = recorder.record(numframes=SAMPLE_RATE * buffer_seconds)
                        
                        # Etichetta chunk con ID progressivo
                        chunk_id = self.chunk_counter
                        self.chunk_counter += 1
                        
                        # Metti in queue: (chunk_id, capture_time, audio_data)
                        self.audio_queue.put((chunk_id, capture_time, data))
                        
                    except Exception as e:
                        print(f"Error recording: {e}")
                        time.sleep(0.1)
        except Exception as e:
            print(f"Fatal recorder error: {e}")

    def dispatcher_thread(self, engine_mode, lang_code, whisper_lang, buffer_seconds):
        """Distribuisce chunk ai worker paralleli (NON BLOCCA!)"""
        print("DEBUG: Start Dispatcher Thread (Parallel Processing)")
        prev_audio_chunk = np.array([], dtype='float32')
        overlap_samples = int(SAMPLE_RATE * (2.0 if engine_mode == "google" else 0))

        while not self.stop_event.is_set() or not self.audio_queue.empty():
            try:
                chunk_id, capture_time, data = self.audio_queue.get(timeout=1)
            except queue.Empty:
                continue

            mono_data = np.mean(data, axis=1)

            if engine_mode == "google":
                if prev_audio_chunk.size > 0:
                    combined_data = np.concatenate((prev_audio_chunk, mono_data))
                else:
                    combined_data = mono_data
                
                prev_audio_chunk = mono_data[-overlap_samples:]
                data_to_process = combined_data
                
                boost_factor = 3.0
                data_to_process = data_to_process * boost_factor
                data_to_process = np.clip(data_to_process, -1.0, 1.0)
            else:
                data_to_process = mono_data

            if np.max(np.abs(data_to_process)) < 0.0001:
                 prev_audio_chunk = np.array([], dtype='float32')
                 continue

            # Usa timestamp di cattura (non di elaborazione!)
            timestamp = capture_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # SOTTOMETTI AL POOL (non blocca!)
            if engine_mode == "google":
                future = self.executor.submit(self.process_chunk_google, data_to_process.copy(), lang_code, timestamp)
            else:
                future = self.executor.submit(self.process_chunk_whisper, data_to_process.copy(), whisper_lang, timestamp)
            
            # Aggiungi alla result queue con chunk_id per ordinamento
            self.result_queue.put((chunk_id, future))
        
        print("DEBUG: Dispatcher finished")
    
    def result_collector_thread(self):
        """Raccoglie risultati dai worker e li mostra NELL'ORDINE CORRETTO"""
        print("DEBUG: Start Result Collector Thread")
        expected_chunk_id = 0
        pending_results = {}  # Buffer per risultati fuori ordine
        
        while not self.stop_event.is_set() or not self.result_queue.empty() or len(pending_results) > 0:
            try:
                chunk_id, future = self.result_queue.get(timeout=0.5)
                
                # Attendi completamento worker (può essere già finito!)
                try:
                    results = future.result(timeout=30)
                except Exception as e:
                    results = [f"[ERROR CHUNK {chunk_id}]: {e}"]
                
                # Salva risultato
                pending_results[chunk_id] = results
                
                # Mostra tutti i chunk consecutivi disponibili
                while expected_chunk_id in pending_results:
                    for line in pending_results[expected_chunk_id]:
                        if line:  # Salta linee vuote
                            self.update_ui(line)
                    
                    del pending_results[expected_chunk_id]
                    expected_chunk_id += 1
                    
            except queue.Empty:
                continue
        
        print("DEBUG: Result Collector finished")

    def process_chunk_google(self, audio_data, lang_code, timestamp):
        """Worker per Google Speech (thread-safe, ritorna risultati)"""
        recognizer = sr.Recognizer()
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        audio_source = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)

        try:
            text = recognizer.recognize_google(audio_source, language=lang_code)
            return [f"[{timestamp}] {text}"]
        except sr.UnknownValueError:
            return []  # Nessun testo riconosciuto
        except Exception as e:
            return [f"[ERROR GOOGLE]: {e}"]

    def process_chunk_whisper(self, audio_data, lang_code, timestamp):
        """Worker per Whisper (thread-safe, ritorna risultati)"""
        try:
            if self.model:
                segments, _ = self.model.transcribe(audio_data, beam_size=5, language=lang_code, vad_filter=True)
                parts = [s.text.strip() for s in segments if s.text.strip()]
                text = " ".join(parts)
                if text:
                    return [f"[{timestamp}] {text}"]
                return []
            return []
        except Exception as e:
            return [f"[ERROR WHISPER]: {e}"]

    def update_ui(self, text):
        self.log_to_file(text)
        if self.page and self.txt_output:
            try:
                # Definisci la coroutine async per l'update UI
                async def _do_update():
                    # Aggiungi nuova riga al TextField
                    if self.txt_output.value:
                        self.txt_output.value += "\n" + text
                    else:
                        self.txt_output.value = text
                    
                    # Keep logs manageable (limita a ultime 500 righe)
                    lines = self.txt_output.value.split("\n")
                    if len(lines) > 500:
                        self.txt_output.value = "\n".join(lines[-500:])
                    
                    self.page.update()
                
                # Esegui la coroutine nel thread principale UI
                self.page.run_task(_do_update)
            except Exception as e:
                print(f"UI Update Error: {e}")

    def start_transcription(self, engine, lang, device_name):
        if self.is_recording: return
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.get_log_dir(), f"transcript_{ts}.txt")
        
        if lang == "Português":
            l_google = "pt-BR"
            l_whisper = "pt"
            w_model = "small"
            w_buffer = 12
        else:
            l_google = "en-US"
            l_whisper = "en"
            w_model = "small.en"
            w_buffer = 4

        if "Whisper" in engine:
            if self.current_model_name != w_model:
                self.update_ui(f"Loading Whisper Model ({w_model})... Please wait.")
                try:
                    self.model = WhisperModel(w_model, device=DEVICE_TYPE, compute_type=COMPUTE_TYPE)
                    self.current_model_name = w_model
                    self.update_ui("Model Loaded.")
                except Exception as e:
                    self.update_ui(f"Error loading model: {e}")
                    return
            current_buffer = w_buffer
            mode = "whisper"
            # Whisper: 3 worker paralleli per CPU multi-core
            num_workers = 3
        else:
            current_buffer = 10 
            mode = "google"
            # Google: 4 worker per gestire rate limiting API
            num_workers = 4

        target_mic = None
        try:
            mics = sc.all_microphones(include_loopback=True)
            for m in mics:
                if m.name == device_name:
                    target_mic = m; break
            if not target_mic:
                for m in mics:
                    if device_name in m.name:
                        target_mic = m; break
            if not target_mic:
                default = sc.default_speaker()
                for m in mics:
                    if m.isloopback and m.id == default.id:
                        target_mic = m; break
        except:
            pass

        if not target_mic:
            self.update_ui("ERROR: Audio device not found! Try selecting another one.")
            return

        self.update_ui(f"--- STARTED ({mode.upper()} - {lang} - {target_mic.name}) ---")
        self.update_ui(f">>> Parallel Processing: {num_workers} workers")
        
        # Reset queues e contatori
        while not self.audio_queue.empty():
            self.audio_queue.get()
        while not self.result_queue.empty():
            self.result_queue.get()
        self.chunk_counter = 0

        # Crea pool di worker paralleli
        self.executor = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="TranscribeWorker")

        self.stop_event.clear()
        self.is_recording = True
        
        # Thread 1: Recording (cattura audio)
        t_rec = threading.Thread(target=self.record_audio_thread, args=(target_mic, current_buffer))
        t_rec.daemon = True
        t_rec.start()
        
        # Thread 2: Dispatcher (distribuisce ai worker)
        t_disp = threading.Thread(target=self.dispatcher_thread, args=(mode, l_google, l_whisper, current_buffer))
        t_disp.daemon = True
        t_disp.start()
        
        # Thread 3: Result Collector (raccoglie risultati ordinati)
        t_collect = threading.Thread(target=self.result_collector_thread)
        t_collect.daemon = True
        t_collect.start()

    def stop_transcription(self):
        if not self.is_recording: return
        self.stop_event.set()
        self.is_recording = False
        
        # Chiudi pool di worker
        if self.executor:
            self.executor.shutdown(wait=True, cancel_futures=False)
            self.executor = None
        
        self.update_ui("--- STOPPED ---")

def main(page: ft.Page):
    page.title = "Live Transcriber Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 1400
    page.window_height = 1100
    page.padding = 15
    
    app = TranscriberApp()
    app.page = page

    # --- UI COMPONENTS ---
    
    img_robot = ft.Image(
        src="robot_static.png",
        width=140,
        height=140,
        fit="cover",
        scale=1.3,
    )
    
    robot_container = ft.Container(
        content=img_robot,
        width=130,
        height=130,
        border_radius=ft.border_radius.all(65),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border=ft.border.all(2, ft.Colors.BLUE_GREY_800),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=10, color=ft.Colors.BLACK),
    )

    # Orologio sincronizzato con Windows
    clock_text = ft.Text(
        value=datetime.datetime.now().strftime("%H:%M:%S"),
        size=18,
        weight="bold",
        color=ft.Colors.CYAN_400,
        text_align=ft.TextAlign.CENTER
    )
    
    # Thread per aggiornare l'orologio ogni secondo
    def clock_update_thread():
        while True:
            try:
                current_time = datetime.datetime.now().strftime("%H:%M:%S")
                async def _update_clock():
                    clock_text.value = current_time
                    page.update()
                page.run_task(_update_clock)
            except:
                pass
            time.sleep(1)
    
    threading.Thread(target=clock_update_thread, daemon=True).start()

    header = ft.Text("Live Transcriber Pro", size=26, weight="bold", color=ft.Colors.BLUE_200)

    dd_device = ft.Dropdown(label="Audio Source (Loopback)", expand=True)
    
    def refresh_devices(e=None):
        try:
            mics = sc.all_microphones(include_loopback=True)
            options = []
            default_speaker_id = sc.default_speaker().id
            found_default = None
            for m in mics:
                if m.isloopback:
                    opt = ft.dropdown.Option(text=m.name)
                    options.append(opt)
                    if m.id == default_speaker_id:
                        found_default = m.name
            dd_device.options = options
            if found_default:
                dd_device.value = found_default
            elif options:
                dd_device.value = options[0].text
            dd_device.update()
        except:
            pass

    refresh_devices()

    btn_refresh = ft.IconButton(icon=ft.Icons.REFRESH, on_click=refresh_devices, tooltip="Refresh Devices")

    dd_lang = ft.Dropdown(
        label="Language",
        options=[
            ft.dropdown.Option("English"),
            ft.dropdown.Option("Português"),
        ],
        value="English",
        expand=True
    )

    dd_engine = ft.Dropdown(
        label="Engine",
        options=[
            ft.dropdown.Option("Google (indicated for English)"),
            ft.dropdown.Option("Whisper (indicated for Português Brasil)"),
        ],
        value="Whisper (indicated for Português Brasil)",
        expand=True
    )

    # Output Area: TextField multilinea per selezione nativa del testo (LARGO E ALTO!)
    txt_output = ft.TextField(
        value="",
        multiline=True,
        read_only=True,
        min_lines=25,
        max_lines=60,
        text_size=14,
        bgcolor=ft.Colors.BLACK12,
        color=ft.Colors.GREEN_400,
        border_color=ft.Colors.BLUE_GREY_700,
        focused_border_color=ft.Colors.BLUE_400,
        text_style=ft.TextStyle(font_family="Consolas"),
        expand=True,  # Espande orizzontalmente
    )
    app.txt_output = txt_output
    
    # Contenitore con dimensioni FORZATE per garantire visibilità
    log_container = ft.Container(
        content=txt_output,
        height=650,  # ALTEZZA FORZATA - 650px garantiti!
        expand=True,  # Espande orizzontalmente per usare tutto lo spazio
    )

    def btn_start_click(e):
        if not app.is_recording:
            img_robot.src = "robot_anim.gif"
            img_robot.update()
            
            btn_start.text = "STARTING..."
            btn_start.disabled = True
            btn_stop.disabled = False
            
            dd_device.disabled = True
            dd_lang.disabled = True
            dd_engine.disabled = True
            btn_refresh.disabled = True
            
            # Aggiungi messaggio di inizializzazione
            if txt_output.value:
                txt_output.value += f"\n>>> Initializing {dd_engine.value}... Please wait..."
            else:
                txt_output.value = f">>> Initializing {dd_engine.value}... Please wait..."
            page.update()
            
            def start_bg():
                app.start_transcription(dd_engine.value, dd_lang.value, dd_device.value)
                btn_start.text = "RECORDING IN PROGRESS"
                page.update()

            threading.Thread(target=start_bg).start()

    def btn_stop_click(e):
        if app.is_recording:
            btn_stop.text = "STOPPING..."
            btn_stop.disabled = True
            
            # Aggiungi messaggio di stop
            txt_output.value += "\n>>> STOP REQUESTED... Finishing last chunk & closing threads..."
            page.update()
            
            def stop_bg():
                app.stop_transcription()
                img_robot.src = "robot_static.png"
                img_robot.update()
                
                btn_start.text = "START RECORDING"
                btn_start.disabled = False
                btn_stop.text = "STOP"
                btn_stop.disabled = True
                
                dd_device.disabled = False
                dd_lang.disabled = False
                dd_engine.disabled = False
                btn_refresh.disabled = False
                page.update()
            
            threading.Thread(target=stop_bg).start()

    def btn_clear_click(e):
        txt_output.value = ""
        page.update()

    def btn_open_logs_click(e):
        try:
            log_dir = app.get_log_dir()
            os.startfile(log_dir)
        except Exception as ex:
            print(f"Error opening folder: {ex}")

    btn_start = ft.ElevatedButton(
        "START RECORDING", 
        color=ft.Colors.WHITE, 
        bgcolor=ft.Colors.GREEN_700, 
        on_click=btn_start_click,
        height=50,
        expand=True
    )
    
    btn_stop = ft.ElevatedButton(
        "STOP", 
        color=ft.Colors.WHITE, 
        bgcolor=ft.Colors.RED_700, 
        on_click=btn_stop_click,
        disabled=True,
        height=50,
        expand=True
    )

    def btn_copy_all_click(e):
        if txt_output.value:
            page.set_clipboard(txt_output.value)
            # Feedback visivo temporaneo
            btn_copy_all.text = "✓ Copied!"
            page.update()
            def reset_btn():
                time.sleep(1.5)
                btn_copy_all.text = "Copy All"
                page.update()
            threading.Thread(target=reset_btn, daemon=True).start()
    
    btn_clear = ft.TextButton("Clear Log", on_click=btn_clear_click, icon=ft.Icons.CLEAR_ALL)
    btn_copy_all = ft.TextButton("Copy All", on_click=btn_copy_all_click, icon=ft.Icons.COPY_ALL)
    btn_open_logs = ft.TextButton("Open Logs Folder", on_click=btn_open_logs_click, icon=ft.Icons.FOLDER_OPEN)

    page.add(
        ft.Row([
            ft.Column([header, ft.Text("Powered by Google & Whisper AI", size=12, color=ft.Colors.GREY_400)]),
            ft.Container(expand=True),
            ft.Column([
                robot_container,
                ft.Container(height=5),
                clock_text
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            btn_refresh
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        
        ft.Row([dd_device]),
        ft.Row([dd_lang, dd_engine]),
        log_container, # CAMPO PRINCIPALE - 600px garantiti!
        ft.Text("💡 Select text with mouse + Ctrl+C, or 'Copy All'", 
                size=10, 
                color=ft.Colors.CYAN_600, 
                italic=True,
                text_align=ft.TextAlign.CENTER),
        ft.Row([btn_open_logs, ft.Container(expand=True), btn_copy_all, btn_clear]),
        ft.Row([btn_start, btn_stop], spacing=20),
        ft.Text("Logs saved to text files automatically", size=10, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER)
    )

if __name__ == "__main__":
    ft.app(target=main)
