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
        self.executor = ThreadPoolExecutor(max_workers=4)
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
        print(f"DEBUG: Start Recording Thread (Buffer: {buffer_seconds}s)")
        try:
            with mic.recorder(samplerate=SAMPLE_RATE) as recorder:
                while not self.stop_event.is_set():
                    try:
                        data = recorder.record(numframes=SAMPLE_RATE * buffer_seconds)
                        self.audio_queue.put(data)
                    except Exception as e:
                        print(f"Error recording: {e}")
                        time.sleep(0.1)
        except Exception as e:
            print(f"Fatal recorder error: {e}")

    def process_queue_thread(self, engine_mode, lang_code, whisper_lang, buffer_seconds):
        print("DEBUG: Start Processing Thread")
        prev_audio_chunk = np.array([], dtype='float32')
        overlap_samples = int(SAMPLE_RATE * (2.0 if engine_mode == "google" else 0))

        while not self.stop_event.is_set():
            try:
                data = self.audio_queue.get(timeout=buffer_seconds + 3)
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

            timestamp = self.get_timestamp()
            
            if engine_mode == "google":
                self.executor.submit(self.task_google, data_to_process, lang_code, timestamp)
            else:
                self.task_whisper(data_to_process, whisper_lang, timestamp)

    def task_google(self, audio_data, lang_code, timestamp):
        recognizer = sr.Recognizer()
        audio_int16 = (audio_data * 32767).astype(np.int16)
        audio_bytes = audio_int16.tobytes()
        audio_source = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)

        try:
            text = recognizer.recognize_google(audio_source, language=lang_code)
            self.update_ui(f"[{timestamp}] {text}")
        except sr.UnknownValueError:
            pass
        except Exception as e:
            self.update_ui(f"[ERROR GOOGLE]: {e}")

    def task_whisper(self, audio_data, lang_code, timestamp):
        try:
            if self.model:
                segments, _ = self.model.transcribe(audio_data, beam_size=5, language=lang_code, vad_filter=True)
                parts = [s.text.strip() for s in segments if s.text.strip()]
                text = " ".join(parts)
                if text:
                    self.update_ui(f"[{timestamp}] {text}")
        except Exception as e:
            self.update_ui(f"[ERROR WHISPER]: {e}")

    def update_ui(self, text):
        self.log_to_file(text)
        if self.page and self.txt_output:
            try:
                # Definisci la coroutine async per l'update UI
                async def _do_update():
                    color = ft.Colors.GREEN_400
                    if "[ERROR" in text: color = ft.Colors.RED_400
                    if ">>>" in text: color = ft.Colors.YELLOW_200
                    
                    self.txt_output.controls.append(ft.Text(text, color=color, selectable=True, size=15, font_family="Consolas"))
                    
                    # Keep logs manageable
                    if len(self.txt_output.controls) > 500:
                        self.txt_output.controls.pop(0)
                    
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

        if engine == "Whisper (Local)":
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
        else:
            current_buffer = 10 
            mode = "google"

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
        
        while not self.audio_queue.empty():
            self.audio_queue.get()

        self.stop_event.clear()
        self.is_recording = True
        
        t_rec = threading.Thread(target=self.record_audio_thread, args=(target_mic, current_buffer))
        t_rec.daemon = True
        t_rec.start()
        
        t_proc = threading.Thread(target=self.process_queue_thread, args=(mode, l_google, l_whisper, current_buffer))
        t_proc.daemon = True
        t_proc.start()

    def stop_transcription(self):
        if not self.is_recording: return
        self.stop_event.set()
        self.is_recording = False
        self.update_ui("--- STOPPED ---")

def main(page: ft.Page):
    page.title = "Live Transcriber Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 800
    page.window_height = 850
    page.padding = 20
    
    app = TranscriberApp()
    app.page = page

    # --- UI COMPONENTS ---
    
    img_robot = ft.Image(
        src="robot_static.png",
        width=180,
        height=180,
        fit="cover",
        scale=1.4,
    )
    
    robot_container = ft.Container(
        content=img_robot,
        width=170,
        height=170,
        border_radius=ft.border_radius.all(85),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border=ft.border.all(3, ft.Colors.BLUE_GREY_800),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=15, color=ft.Colors.BLACK),
    )

    # Orologio sincronizzato con Windows
    clock_text = ft.Text(
        value=datetime.datetime.now().strftime("%H:%M:%S"),
        size=20,
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

    header = ft.Text("Live Transcriber Pro", size=30, weight="bold", color=ft.Colors.BLUE_200)

    dd_device = ft.Dropdown(label="Audio Source (Loopback)", width=450)
    
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
            ft.dropdown.Option("Google (Online)"),
            ft.dropdown.Option("Whisper (Local)"),
        ],
        value="Whisper (Local)",
        expand=True
    )

    # Output Area: ListView
    txt_output = ft.ListView(
        expand=True,
        spacing=5,
        padding=10,
        auto_scroll=True,
    )
    app.txt_output = txt_output
    
    # Contenitore per dare lo stile console
    log_container = ft.Container(
        content=txt_output,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_700),
        bgcolor=ft.Colors.BLACK12,
        border_radius=5,
        expand=True,
        padding=5
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
            
            txt_output.controls.append(ft.Text(f">>> Initializing {dd_engine.value}... Please wait...", color=ft.Colors.YELLOW_200))
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
            
            txt_output.controls.append(ft.Text("\n>>> STOP REQUESTED... Finishing last chunk & closing threads...\n", color=ft.Colors.ORANGE_300))
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
        txt_output.controls.clear()
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

    btn_clear = ft.TextButton("Clear Log", on_click=btn_clear_click, icon=ft.Icons.CLEAR_ALL)
    btn_open_logs = ft.TextButton("Open Logs Folder", on_click=btn_open_logs_click, icon=ft.Icons.FOLDER_OPEN)

    page.add(
        ft.Row([
            ft.Column([header, ft.Text("Powered by Google & Whisper AI", size=12, color=ft.Colors.GREY_400)]),
            ft.Container(expand=True),
            ft.Column([
                robot_container,
                ft.Container(height=10),
                clock_text
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            btn_refresh
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        
        ft.Row([dd_device]),
        ft.Row([dd_lang, dd_engine]),
        ft.Divider(),
        log_container, # Uso il container, non la listview nuda
        ft.Row([btn_open_logs, ft.Container(expand=True), btn_clear]),
        ft.Divider(),
        ft.Row([btn_start, btn_stop], spacing=20),
        ft.Container(
            content=ft.Text("Logs saved automatically to text files.", size=12, color=ft.Colors.GREY_500, text_align=ft.TextAlign.CENTER),
            padding=10,
            alignment=ft.Alignment(0, 0)
        )
    )

if __name__ == "__main__":
    ft.app(target=main)
