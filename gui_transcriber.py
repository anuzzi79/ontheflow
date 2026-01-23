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
import json # #region debug log import
# #endregion
import asyncio  # Necessario per scroll ritardato
from concurrent.futures import ThreadPoolExecutor
import assemblyai as aai
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingParameters,
    StreamingEvents,
    BeginEvent,
    TurnEvent,
    TerminationEvent,
    StreamingError
)

# Prova a caricare variabili d'ambiente da .env (opzionale)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv non installato, usa chiave hardcoded

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
        
        # AssemblyAI Real-Time Streaming
        self.assemblyai_transcriber = None
        # Carica chiave API da environment o usa placeholder
        self.ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "YOUR_API_KEY_HERE")
        # ⚠️ IMPORTANTE: Inserisci la tua chiave API qui sopra (sostituisci YOUR_API_KEY_HERE)
        # Oppure crea un file .env con: ASSEMBLYAI_API_KEY=tua-chiave-qui
        
        # Per gestire trascrizioni parziali (real-time)
        self.current_partial_text = ""
        self.last_turn_order = -1
        self.turn_text_map = {}  # Mappa turn_order -> Testo stringa
        self.translated_text_map = {} # Mappa turn_order -> Testo tradotto
        self.turn_id_offset = 0  # Offset per garantire ordine tra sessioni
        
        self.full_log_text = ft.Text(
            value="", 
            font_family="Consolas", 
            size=14, 
            color=ft.Colors.GREEN_400,
            selectable=True
        )
        
        self.full_translation_text = ft.Text(
            value="", 
            font_family="Consolas", 
            size=14, 
            color=ft.Colors.CYAN_400, # Colore diverso per traduzione
            selectable=True
        )
    
        # Stato UI
        self.page = None
        self.log_scroll_column = None # Colonna per auto-scroll (Trascrizione)
        self.translation_scroll_column = None # Colonna per auto-scroll (Traduzione)
        self.scroll_anchor = None # Ancora per lo scroll manuale
        self.translation_scroll_anchor = None # Ancora per lo scroll manuale (Traduzione)

        
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

    def translate_text(self, text, target_lang="it"):
        """Traduce il testo usando deep_translator (Google Translate)"""
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
            return translated
        except Exception as e:
            print(f"Translation Error: {e}")
            return f"[Translation Error]"

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

            # Usa timestamp di cattura (non di elaborazione!)
            timestamp = capture_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Check se audio è silenzioso
            if np.max(np.abs(data_to_process)) < 0.0001:
                prev_audio_chunk = np.array([], dtype='float32')
                # IMPORTANTE: Crea future "vuoto" per mantenere ordine sequenziale!
                from concurrent.futures import Future
                empty_future = Future()
                empty_future.set_result([])  # Risultato vuoto (nessun testo)
                self.result_queue.put((chunk_id, empty_future))
                print(f"DEBUG: Chunk {chunk_id} SKIPPED (silence) but placeholder added")
                continue
            
            # SOTTOMETTI AL POOL (non blocca!)
            if engine_mode == "google":
                future = self.executor.submit(self.process_chunk_google, data_to_process.copy(), lang_code, timestamp)
            else:
                future = self.executor.submit(self.process_chunk_whisper, data_to_process.copy(), whisper_lang, timestamp)
            
            # Aggiungi alla result queue con chunk_id per ordinamento
            self.result_queue.put((chunk_id, future))
            current_queue_size = self.result_queue.qsize()
            print(f"DEBUG: Chunk {chunk_id} submitted to pool (queue size: {current_queue_size})")
            
            # Warning se queue troppo alta (collo di bottiglia!)
            if current_queue_size > 3:
                print(f"⚠️ WARNING: Queue size {current_queue_size} > 3 - Processing bottleneck detected!")
                if current_queue_size > 6:
                    print(f"🔴 CRITICAL: Queue size {current_queue_size} > 6 - Workers overloaded!")
                
                # Back-pressure: rallenta recording se queue troppo piena
                if current_queue_size > 8:
                    print(f"🛑 BACK-PRESSURE: Pausing recording for 2s to let workers catch up...")
                    time.sleep(2)  # Pausa per dare tempo ai worker di recuperare
        
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
                    results = future.result(timeout=45)  # Timeout 45s - aumentato per gestire carichi alti
                except TimeoutError:
                    print(f"WARNING: Chunk {chunk_id} timeout dopo 45s - SKIPPED")
                    results = [f"[⚠️ CHUNK {chunk_id} TIMEOUT - Skipped]"]
                except Exception as e:
                    print(f"ERROR: Chunk {chunk_id} failed with: {type(e).__name__}: {e}")
                    results = [f"[❌ CHUNK {chunk_id} ERROR: {type(e).__name__}]"]
                
                # Salva risultato
                pending_results[chunk_id] = results
                
                # Avvisa se troppi chunk in attesa (possibile blocco)
                if len(pending_results) > 5:
                    print(f"WARNING: {len(pending_results)} chunks waiting (expecting #{expected_chunk_id})")
                
                # Mostra tutti i chunk consecutivi disponibili
                while expected_chunk_id in pending_results:
                    for line in pending_results[expected_chunk_id]:
                        if line:  # Salta linee vuote
                            self.update_ui(line)
                    
                    del pending_results[expected_chunk_id]
                    expected_chunk_id += 1
                    print(f"DEBUG: Chunk {expected_chunk_id - 1} displayed (pending: {len(pending_results)})")
                    
            except queue.Empty:
                continue
        
        print("DEBUG: Result Collector finished")

    def process_chunk_google(self, audio_data, lang_code, timestamp):
        """Worker per Google Speech (thread-safe, ritorna risultati)"""
        try:
            recognizer = sr.Recognizer()
            audio_int16 = (audio_data * 32767).astype(np.int16)
            audio_bytes = audio_int16.tobytes()
            audio_source = sr.AudioData(audio_bytes, SAMPLE_RATE, 2)

            try:
                text = recognizer.recognize_google(audio_source, language=lang_code)
                return [f"[{timestamp}] {text}"]
            except sr.UnknownValueError:
                return []  # Nessun testo riconosciuto
            except sr.RequestError as e:
                print(f"Google API Error: {e}")
                return [f"[⚠️ Google API Error - check internet connection]"]
        except Exception as e:
            print(f"Google Worker Crash: {type(e).__name__}: {e}")
            return [f"[❌ Google Processing Failed]"]

    def process_chunk_whisper(self, audio_data, lang_code, timestamp):
        """Worker per Whisper (thread-safe, ritorna risultati)"""
        try:
            if not self.model:
                print("WARNING: Whisper model not loaded!")
                return [f"[⚠️ Model Not Loaded]"]
            
            segments, _ = self.model.transcribe(audio_data, beam_size=5, language=lang_code, vad_filter=True)
            parts = [s.text.strip() for s in segments if s.text.strip()]
            text = " ".join(parts)
            if text:
                return [f"[{timestamp}] {text}"]
            return []
        except Exception as e:
            print(f"Whisper Worker Error: {type(e).__name__}: {e}")
            return [f"[❌ Whisper Processing Failed]"]

    # ============== ASSEMBLYAI REAL-TIME STREAMING (v3 Universal) ==============
    
    def audio_generator(self, mic):
        """Generatore di chunk audio per AssemblyAI v3"""
        try:
            with mic.recorder(samplerate=SAMPLE_RATE) as recorder:
                while not self.stop_event.is_set():
                    # Buffer MICRO: solo 0.05 secondi (50ms) per latenza minima
                    data = recorder.record(numframes=int(SAMPLE_RATE * 0.05))
                    
                    # Converti in mono e PCM16
                    mono_data = np.mean(data, axis=1)
                    audio_int16 = (mono_data * 32767).astype(np.int16)
                    audio_bytes = audio_int16.tobytes()
                    
                    yield audio_bytes
        except Exception as e:
            print(f"Audio Generator Error: {e}")
    
    def record_audio_assemblyai_thread(self, mic, lang_code):
        """Streaming REAL-TIME con AssemblyAI v3 (latenza 300-500ms!)"""
        print(f"DEBUG: Start AssemblyAI Universal Streaming (Language: {lang_code})")
        
        try:
            # Crea client con nuova API v3
            client = StreamingClient(
                StreamingClientOptions(
                    api_key=self.ASSEMBLYAI_API_KEY,
                    api_host="streaming.assemblyai.com"
                )
            )
            
            # Registra callback
            client.on(StreamingEvents.Begin, self.on_assemblyai_begin)
            client.on(StreamingEvents.Turn, self.on_assemblyai_turn)
            client.on(StreamingEvents.Termination, self.on_assemblyai_terminated)
            client.on(StreamingEvents.Error, self.on_assemblyai_error)
            
            self.assemblyai_transcriber = client
            
            # Configura parametri (usa modello corretto!)
            # "universal-streaming-english" = solo inglese
            # "universal-streaming-multi" = multilingua (EN, PT, ES, FR, DE, IT)
            speech_model = "universal-streaming-multi" if lang_code == "pt" else "universal-streaming-english"
            
            params = StreamingParameters(
                sample_rate=SAMPLE_RATE,
                format_turns=True,  # Formattazione automatica (punteggiatura)
                speech_model=speech_model,
                end_utterance_silence_threshold=300,  # Ridotto a 300ms (default 700ms)
                # Altri parametri per massima reattività:
                # - Rileva fine frase più velocemente
                # - Mostra parole più rapidamente
            )
            
            # Connetti
            client.connect(params)
            
            # Crea generatore audio e avvia streaming
            # Il metodo .stream() gestisce automaticamente l'invio dei chunk
            audio_stream = self.audio_generator(mic)
            client.stream(audio_stream)
                        
        except Exception as e:
            print(f"AssemblyAI Fatal Error: {e}")
            self.update_ui(f"❌ AssemblyAI Error: {e}")
        finally:
            if self.assemblyai_transcriber:
                try:
                    self.assemblyai_transcriber.disconnect(terminate=True)
                except:
                    pass

    def on_assemblyai_begin(self, client, event: BeginEvent):
        """Callback: connessione aperta"""
        print(f"AssemblyAI: Connected! Session: {event.id}")
        self.update_ui("🟢 AssemblyAI Universal Streaming Connected - Start speaking!")

    def on_assemblyai_terminated(self, client, event: TerminationEvent):
        """Callback: connessione chiusa"""
        print(f"AssemblyAI: Disconnected (processed {event.audio_duration_seconds:.1f}s)")
        self.update_ui("🔴 AssemblyAI Disconnected")

    
    def on_assemblyai_turn(self, client, event: TurnEvent):
        """Callback: risultati REAL-TIME (parziali e finali)"""
        timestamp = self.get_timestamp()
        
        # Usa l'offset di sessione per garantire ordine cronologico globale
        # AssemblyAI riparte da 0 a ogni connessione, noi aggiungiamo l'offset
        current_turn_id = event.turn_order + self.turn_id_offset
        
        if event.end_of_turn:
            # FINE FRASE
            if event.transcript:
                self.update_or_add_line(
                    f"[{timestamp}] {event.transcript}", 
                    is_final=True, 
                    turn_order=current_turn_id
                )

                    
        else:
            # TESTO PARZIALE
            if hasattr(event, 'words') and event.words:
                all_words_text = " ".join([w.text for w in event.words])
                if all_words_text:
                    self.update_or_add_line(
                        f"[{timestamp}] 🔵 {all_words_text}...", 
                        is_final=False, 
                        turn_order=current_turn_id
                    )

    def update_or_add_line(self, text, is_final, turn_order):
        """Aggiorna il testo UNICO ricostruendolo dalla mappa (garantisce ordine e unicità)"""
        if self.page and self.full_log_text:
            try:
                async def _do_update():
                    # #region agent log
                    try:
                        with open(r"c:\Users\Antonio Nuzzi\ontheflow\.cursor\debug.log", "a") as f: 
                            f.write(json.dumps({"sessionId": "debug-session", "timestamp": int(time.time()*1000), "location": "gui_transcriber.py:update_or_add_line", "message": "Start UI Update", "data": {"turn_order": turn_order, "text_len": len(text), "is_final": is_final}}) + "\n")
                    except: pass
                    # #endregion
                    
                    # 1. Aggiorna la mappa dei testi
                    self.turn_text_map[turn_order] = text
                    
                    # Se è finale, traduci
                    if is_final and turn_order not in self.translated_text_map:
                         # Esegui traduzione in thread separato per non bloccare UI
                        def translate_worker():
                            # Pulisci il testo da timestamp e log prima di tradurre
                            clean_text = text
                            if "]" in text:
                                try:
                                    clean_text = text.split("]", 1)[1].strip()
                                except:
                                    pass
                            
                            # Ignora messaggi di sistema
                            if clean_text.startswith(">>>") or clean_text.startswith("---") or clean_text.startswith("ERROR") or clean_text.startswith("⚠️"):
                                translation = text # Copia i messaggi di sistema così come sono
                            else:
                                translation = self.translate_text(clean_text)
                                # Aggiungi timestamp se presente nell'originale
                                if "]" in text:
                                    timestamp_part = text.split("]", 1)[0] + "]"
                                    translation = f"{timestamp_part} {translation}"
                            
                            self.translated_text_map[turn_order] = translation
                            self.trigger_ui_refresh() # Ridisegna UI dopo traduzione
                            
                        threading.Thread(target=translate_worker, daemon=True).start()

                    self.trigger_ui_refresh() # Ridisegna UI immediato (trascrizione)

                self.page.run_task(_do_update)
            except Exception as e:
                print(f"UI Update Error: {e}")

    def trigger_ui_refresh(self):
        """Ricostruisce e aggiorna entrambe le colonne di testo"""
        try:
             # 2. Ricostruisci TUTTO il testo
            sorted_keys = sorted(self.turn_text_map.keys())
            
            # Ottimizzazione
            if len(sorted_keys) > 500:
                keys_to_remove = sorted_keys[:-500]
                for k in keys_to_remove:
                    if k in self.turn_text_map: del self.turn_text_map[k]
                    if k in self.translated_text_map: del self.translated_text_map[k]
                sorted_keys = sorted_keys[-500:]
            
            # Costruisci stringa unica TRASCRIZIONE
            full_content = "\n".join([self.turn_text_map[k] for k in sorted_keys])
            self.full_log_text.value = full_content
            self.full_log_text.update()

            # Costruisci stringa unica TRADUZIONE
            # Usa stringa vuota se la traduzione non è ancora pronta
            full_translation = "\n".join([self.translated_text_map.get(k, "") for k in sorted_keys])
            self.full_translation_text.value = full_translation
            self.full_translation_text.update()

            # 4. Scroll automatico: Strategia "Mano Invisibile" (Stacca e Riattacca)
            self._scroll_column(self.log_scroll_column, self.scroll_anchor)
            self._scroll_column(self.translation_scroll_column, self.translation_scroll_anchor)

        except Exception as e:
            print(f"Trigger UI Refresh Error: {e}")

    def _scroll_column(self, column, anchor):
        """Helper per gestire lo scroll automatico di una colonna"""
        if column and anchor:
            try:
                # Rimuovi e riaggiungi l'ancora per forzare il layout a vederla "nuova" in fondo
                if anchor in column.controls:
                    column.controls.remove(anchor)
                column.controls.append(anchor)
                column.update() # Ridisegna la colonna
                
                # Scroll immediato verso l'ancora
                column.scroll_to(key=anchor.key, duration=10)
                
                # Scroll ritardato di sicurezza
                async def force_scroll_delayed():
                    await asyncio.sleep(0.1) 
                    if column:
                        column.scroll_to(key=anchor.key, duration=10)
                
                self.page.run_task(force_scroll_delayed)
            except Exception as e:
                print(f"Scroll Helper Error: {e}")

    def update_ui(self, text):
        """Fallback per messaggi di sistema: usa ID sequenziale per apparire SOPRA le trascrizioni"""
        self.log_to_file(text)
        
        # Calcola ID sequenziale corretto (max + 1) per garantire ordine cronologico
        # Questo fa sì che i messaggi di sistema appaiano SOPRA le trascrizioni future
        next_id = 0
        if self.turn_text_map:
            next_id = max(self.turn_text_map.keys()) + 1
        else:
            # Se siamo all'inizio, usa un valore base
            next_id = 1
            
        # Assicurati che l'offset per le trascrizioni future sia maggiore di questo ID
        # Le trascrizioni useranno (turn_order + turn_id_offset), quindi:
        if self.turn_id_offset <= next_id:
            self.turn_id_offset = next_id + 10
            
        self.update_or_add_line(text, True, next_id)

    def on_assemblyai_error(self, client, error: StreamingError):
        """Callback: errori"""
        error_msg = str(error)
        print(f"AssemblyAI Error: {error_msg}")
        # Non mostrare errori "Model deprecated" ripetuti (già gestiti)
        if "deprecated" not in error_msg.lower():
            self.update_ui(f"⚠️ AssemblyAI Error: {error_msg}")

    def _get_microphone(self, device_name):
        """Helper per ottenere microfono"""
        try:
            mics = sc.all_microphones(include_loopback=True)
            for m in mics:
                if m.name == device_name:
                    return m
            for m in mics:
                if device_name in m.name:
                    return m
            default = sc.default_speaker()
            for m in mics:
                if m.isloopback and m.id == default.id:
                    return m
        except Exception as e:
            print(f"Error getting microphone: {e}")
        return None

    # ============================================================

    def start_transcription(self, engine, lang, device_name):
        if self.is_recording: return
        
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.get_log_dir(), f"transcript_{ts}.txt")
        
        if lang == "Português":
            l_google = "pt-BR"
            l_whisper = "pt"
            l_assemblyai = "pt"  # AssemblyAI language code
            w_model = "tiny"  # Soluzione Ibrida: tiny model per velocità
            w_buffer = 10  # Compromesso: 10s per bilanciare velocità e accuracy
        else:
            l_google = "en-US"
            l_whisper = "en"
            l_assemblyai = "en"  # AssemblyAI language code
            w_model = "small.en"
            w_buffer = 4

        # ========== ASSEMBLYAI REAL-TIME ==========
        if "AssemblyAI" in engine:
            target_mic = self._get_microphone(device_name)
            if not target_mic:
                self.update_ui("ERROR: Audio device not found! Try selecting another one.")
                return
            
            self.update_ui(f"--- STARTED (ASSEMBLYAI REAL-TIME - {lang} - {target_mic.name}) ---")
            self.update_ui("⚡ Ultra-Low Latency: ~300-500ms (like ChatGPT!)")
            self.update_ui("💡 Speak naturally, transcription appears instantly...")
            
            self.stop_event.clear()
            self.is_recording = True
            
            # Thread UNICO per AssemblyAI (gestisce tutto!)
            t_assemblyai = threading.Thread(
                target=self.record_audio_assemblyai_thread, 
                args=(target_mic, l_assemblyai)
            )
            t_assemblyai.daemon = True
            t_assemblyai.start()
            return
        
        # ========== WHISPER / GOOGLE (codice originale) ==========
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
            # Whisper: 8 worker paralleli per CPU multi-core (auto-scaling per evitare colli di bottiglia)
            num_workers = 8
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
        
        # Chiudi AssemblyAI se attivo (v3 usa disconnect)
        if self.assemblyai_transcriber:
            try:
                self.assemblyai_transcriber.disconnect(terminate=True)
                print("DEBUG: AssemblyAI transcriber disconnected")
            except Exception as e:
                print(f"Error disconnecting AssemblyAI: {e}")
            finally:
                self.assemblyai_transcriber = None
        
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
        border_radius=ft.BorderRadius.all(65),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
        border=ft.Border.all(2, ft.Colors.BLUE_GREY_800),
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
            ft.dropdown.Option("AssemblyAI Real-Time ⚡ (FASTEST - like ChatGPT)"),
            ft.dropdown.Option("Google (indicated for English)"),
            ft.dropdown.Option("Whisper (indicated for Português Brasil)"),
        ],
        value="AssemblyAI Real-Time ⚡ (FASTEST - like ChatGPT)",
        expand=True
    )

    # Output Area: UNICO Testo per selezione perfetta!
    # Avvolto in SelectionArea per permettere selezione nativa
    log_content = ft.SelectionArea(
        content=app.full_log_text
    )
    
    translation_content = ft.SelectionArea(
        content=app.full_translation_text
    )
    
    # Colonna scrollabile
    # Aggiungo un'ancora invisibile alla fine per lo scroll
    scroll_anchor = ft.Container(height=1, key="scroll_anchor")
    translation_scroll_anchor = ft.Container(height=1, key="translation_scroll_anchor")
    
    log_scroll_column = ft.Column(
        controls=[log_content, scroll_anchor],
        scroll=ft.ScrollMode.ALWAYS,
        # auto_scroll rimosso per evitare conflitti con scroll manuale
        expand=True,
    )
    
    translation_scroll_column = ft.Column(
        controls=[translation_content, translation_scroll_anchor],
        scroll=ft.ScrollMode.ALWAYS,
        expand=True
    )
    
    app.log_scroll_column = log_scroll_column
    app.scroll_anchor = scroll_anchor
    app.translation_scroll_column = translation_scroll_column
    app.translation_scroll_anchor = translation_scroll_anchor
    
    # Container principale (Sinistra - Trascrizione)
    log_container = ft.Container(
        content=log_scroll_column,
        bgcolor=ft.Colors.BLACK12,
        border_radius=10,
        border=ft.border.all(2, ft.Colors.BLUE_GREY_700),
        padding=10,
        expand=True,
    )
    
    # Container secondario (Destra - Traduzione)
    translation_container = ft.Container(
        content=translation_scroll_column,
        bgcolor=ft.Colors.BLACK12,
        border_radius=10,
        border=ft.border.all(2, ft.Colors.AMBER_900), # Bordo diverso
        padding=10,
        expand=True,
    )

    # Titoli colonne
    col_header = ft.Row([
        ft.Container(content=ft.Text("TRANSCRIPTION (Live)", weight="bold"), expand=True, alignment=ft.Alignment(0, 0)),
        ft.Container(content=ft.Text("TRANSLATION (Italian)", weight="bold", color=ft.Colors.AMBER_400), expand=True, alignment=ft.Alignment(0, 0))
    ])
    
    # Area principale divisa in due
    split_view = ft.Row(
        controls=[
            log_container,
            translation_container
        ],
        expand=True,
        spacing=10
    )

    def btn_start_click(e):
        if not app.is_recording:
            # Calcola nuovo offset per mantenere ordine cronologico e posizionare i log sotto
            current_max_id = 0
            if app.turn_text_map:
                current_max_id = max(app.turn_text_map.keys())
            # Imposta offset molto alto rispetto all'ultimo ID usato
            # Questo garantisce che i nuovi turni (0, 1, 2...) + offset siano > ultimo ID
            app.turn_id_offset = current_max_id + 100000
            
            img_robot.src = "robot_anim.gif"
            img_robot.update()
            
            btn_start.text = "STARTING..."
            btn_start.disabled = True
            btn_stop.disabled = False
            
            dd_device.disabled = True
            dd_lang.disabled = True
            dd_engine.disabled = True
            btn_refresh.disabled = True
            
            # Aggiungi messaggio di inizializzazione via update_ui
            app.update_ui(f">>> Initializing {dd_engine.value}... Please wait...")
            
            def start_bg():
                app.start_transcription(dd_engine.value, dd_lang.value, dd_device.value)
                btn_start.text = "RECORDING IN PROGRESS"
                page.update()

            threading.Thread(target=start_bg).start()

    def btn_stop_click(e):
        if app.is_recording:
            btn_stop.text = "STOPPING..."
            btn_stop.disabled = True
            
            # Aggiungi messaggio di stop via update_ui
            app.update_ui(">>> STOP REQUESTED... Finishing last chunk & closing threads...")
            
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
        # Svuota tutto
        app.turn_text_map.clear()
        app.translated_text_map.clear()
        app.full_log_text.value = ""
        app.full_translation_text.value = ""
        page.update()

    def btn_open_logs_click(e):
        try:
            log_dir = app.get_log_dir()
            os.startfile(log_dir)
        except Exception as ex:
            print(f"Error opening folder: {ex}")

    btn_start = ft.Button(
        "START RECORDING", 
        color=ft.Colors.WHITE, 
        bgcolor=ft.Colors.GREEN_700, 
        on_click=btn_start_click,
        height=50,
        expand=True
    )
    
    btn_stop = ft.Button(
        "STOP", 
        color=ft.Colors.WHITE, 
        bgcolor=ft.Colors.RED_700, 
        on_click=btn_stop_click,
        disabled=True,
        height=50,
        expand=True
    )

    def btn_copy_all_click(e):
        if app.full_log_text.value:
            page.set_clipboard(app.full_log_text.value)
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
        col_header,
        split_view, # CAMPO PRINCIPALE - Split View
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
    ft.run(main)