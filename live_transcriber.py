import soundcard as sc
import soundfile as sf
import numpy as np
from faster_whisper import WhisperModel
import speech_recognition as sr
import os
import queue
import threading
import time
import sys
import warnings
import datetime
import io
from concurrent.futures import ThreadPoolExecutor

# Ignora i warning di soundcard per discontinuità
warnings.filterwarnings("ignore", category=UserWarning)
try:
    from soundcard.mediafoundation import SoundcardRuntimeWarning
    warnings.filterwarnings("ignore", category=SoundcardRuntimeWarning)
except ImportError:
    pass

# --- CONFIGURAZIONE BASE ---
SAMPLE_RATE = 16000
DEVICE_TYPE = "cpu"
COMPUTE_TYPE = "int8"

# Crea un nome file unico con data e ora
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = f"transcript_{timestamp}.txt"

# Coda audio
audio_queue = queue.Queue()

# Lock per la scrittura su file/console per evitare righe mescolate
io_lock = threading.Lock()

def log_to_file(text):
    """Scrive il testo nel file di log."""
    with io_lock:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(text + "\n")
        except Exception as e:
            print(f"Errore scrittura file: {e}")

def safe_print(text):
    """Stampa thread-safe"""
    with io_lock:
        print(text)
        sys.stdout.flush()

def record_audio(mic, stop_event, record_seconds):
    """Thread dedicato alla registrazione audio continua."""
    print(f">>> Thread registrazione avviato (Buffer: {record_seconds}s)")
    try:
        with mic.recorder(samplerate=SAMPLE_RATE) as recorder:
            while not stop_event.is_set():
                try:
                    data = recorder.record(numframes=SAMPLE_RATE * record_seconds)
                    audio_queue.put(data)
                except Exception as e:
                    print(f"Errore rec: {e}")
                    time.sleep(0.1)
    except Exception as e:
        print(f"Errore fatale recorder: {e}")

def task_process_google(audio_data, lang_code, timestamp_str):
    """Task eseguito in background per chiamare Google"""
    recognizer = sr.Recognizer()
    
    # Conversione audio
    if len(audio_data.shape) > 1:
        mono_data = np.mean(audio_data, axis=1)
    else:
        mono_data = audio_data

    # NORMALIZZAZIONE AGGRESSIVA (HARD LIMITER)
    # Moltiplica il volume per 3 per tirare su la voce, poi taglia i picchi (clipping)
    boost_factor = 3.0
    mono_data = mono_data * boost_factor
    mono_data = np.clip(mono_data, -1.0, 1.0)

    audio_int16 = (mono_data * 32767).astype(np.int16)
    audio_bytes = audio_int16.tobytes()
    audio_source = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)
    
    try:
        # Chiamata bloccante a Google (ora avviene in un thread separato)
        text = recognizer.recognize_google(audio_source, language=lang_code)
        
        # Stampa risultato
        output_line = f"[{timestamp_str}] {text}"
        safe_print(output_line)
        log_to_file(output_line)
        
    except sr.UnknownValueError:
        # Logga anche i chunk non riconosciuti per capire se sono buchi di sistema o di AI
        msg = f"[{timestamp_str}] [GOOGLE: Audio non riconosciuto/Silenzio]"
        safe_print(msg)
        log_to_file(msg)
    except sr.RequestError as e:
        safe_print(f"[ERRORE GOOGLE API]: {e}")
    except Exception as e:
        safe_print(f"[ERRORE GENERICO]: {e}")

def main():
    print("--- LIVE TRANSCRIBER v3.0 (Async Multi-Threaded) ---")
    
    # 1. SELEZIONE LINGUA
    print("\n1. Seleziona la lingua:")
    print("  [i] Inglese (English)")
    print("  [p] Portoghese (Português)")
    choice_lang = input("Scelta (i/p): ").strip().lower()

    if choice_lang == 'p':
        lang_whisper = "pt"
        lang_google = "pt-BR"
        whisper_model = "small"
        whisper_buffer = 12
        print(">>> Lingua selezionata: PORTOGHESE")
    else:
        lang_whisper = "en"
        lang_google = "en-US"
        whisper_model = "small.en"
        whisper_buffer = 4
        print(">>> Lingua selezionata: INGLESE")

    # 2. SELEZIONE MOTORE
    print("\n2. Seleziona il motore di trascrizione:")
    print("  [w] Whisper Locale (Offline)")
    print("  [g] Google Speech (Online)")
    choice_engine = input("Scelta (w/g): ").strip().lower()

    engine_mode = "whisper" if choice_engine == 'w' else "google"
    
    if engine_mode == "google":
        current_buffer = 10  # Buffer più lungo per ridurre frequenza chiamate API
        overlap_samples = int(SAMPLE_RATE * 2.0) # 2.0s overlap (più conservativo)
        print(f">>> Motore: GOOGLE ONLINE (Async mode, Buffer: {current_buffer}s + 2.0s Overlap)")
        
        # ThreadPool per gestire le richieste multiple a Google in parallelo
        # max_workers=4 significa che può gestire fino a 4 richieste simultanee
        # se internet lagga, senza bloccare la registrazione
        executor = ThreadPoolExecutor(max_workers=4)
        
    else:
        current_buffer = whisper_buffer
        overlap_samples = 0
        executor = None
        print(f">>> Motore: WHISPER LOCALE ({whisper_model}, Buffer: {current_buffer}s)")

    # Inizializza Log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- SESSIONE {timestamp} ---\n")
        f.write(f"--- Lingua: {lang_google if engine_mode == 'google' else lang_whisper} ---\n")
        f.write(f"--- Motore: {engine_mode.upper()} ---\n")

    # Caricamento Modello (Solo se Whisper)
    model = None
    if engine_mode == "whisper":
        print(f"Caricamento modello {whisper_model} su {DEVICE_TYPE}...")
        try:
            model = WhisperModel(whisper_model, device=DEVICE_TYPE, compute_type=COMPUTE_TYPE)
        except Exception as e:
            print(f"Errore modello: {e}")
            return

    # Init Audio
    try:
        default_speaker = sc.default_speaker()
        target_mic = None
        mics = sc.all_microphones(include_loopback=True)
        
        for m in mics:
            if m.isloopback and m.id == default_speaker.id:
                target_mic = m; break
        if not target_mic:
            for m in mics:
                if m.isloopback and m.name == default_speaker.name:
                    target_mic = m; break
        if not target_mic:
             for m in mics:
                 if "Loopback" in m.name or "Stereo Mix" in m.name:
                     target_mic = m; break
        
        if not target_mic:
            print("ERRORE: Loopback device non trovato.")
            return
            
        print(f"--- In ascolto su: {target_mic.name} ---")
    except Exception as e:
        print(f"Errore audio init: {e}")
        return

    print("\n--- INIZIO TRASCRIZIONE (PREMI CTRL+C PER USCIRE) ---\n")
    
    stop_event = threading.Event()
    recorder_thread = threading.Thread(target=record_audio, args=(target_mic, stop_event, current_buffer))
    recorder_thread.daemon = True
    recorder_thread.start()

    prev_audio_chunk = np.array([], dtype='float32')

    try:
        while True:
            try:
                # Timeout un po' più lungo per sicurezza
                data = audio_queue.get(timeout=current_buffer + 5)
            except queue.Empty:
                continue

            # --- PRE-PROCESSING ---
            mono_data = np.mean(data, axis=1)

            # Overlap management
            if engine_mode == "google":
                if prev_audio_chunk.size > 0:
                    combined_data = np.concatenate((prev_audio_chunk, mono_data))
                else:
                    combined_data = mono_data
                
                prev_audio_chunk = mono_data[-overlap_samples:] 
                data_to_process = combined_data
            else:
                data_to_process = mono_data

            # Check silenzio
            if np.max(np.abs(data_to_process)) < 0.001:
                prev_audio_chunk = np.array([], dtype='float32')
                continue

            # --- DISPATCHING ---
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if engine_mode == "google":
                # Lancia il task al thread pool e torna SUBITO a leggere la coda
                executor.submit(task_process_google, data_to_process, lang_google, current_time)
            
            else:
                # Whisper (rimane sincrono perché usa la CPU intensamente, inutile parallelizzare troppo)
                try:
                    segments, _ = model.transcribe(data_to_process, beam_size=5, language=lang_whisper, vad_filter=True)
                    parts = [s.text.strip() for s in segments if s.text.strip()]
                    text_result = " ".join(parts)
                    
                    if text_result:
                        output_line = f"[{current_time}] {text_result}"
                        safe_print(output_line)
                        log_to_file(output_line)
                        
                except Exception as e:
                    print(f"Errore Whisper: {e}")

    except KeyboardInterrupt:
        print("\n--- STOP ---")
        stop_event.set()
        if executor:
            print("Attendo completamento richieste pendenti...")
            executor.shutdown(wait=False)
        print(f"Salvato in: {LOG_FILE}")

if __name__ == "__main__":
    main()
