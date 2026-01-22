# 🔄 Aggiornamento AssemblyAI alla v3 (Universal Streaming)

## ⚠️ IMPORTANTE: AssemblyAI ha deprecato il vecchio modello!

AssemblyAI ha introdotto il nuovo **Universal Streaming Model** (v3) che sostituisce il vecchio RealtimeTranscriber.

---

## 🚀 Cosa fare:

### 1. Aggiorna il pacchetto AssemblyAI

```bash
pip install --upgrade assemblyai
```

Oppure reinstalla completamente:

```bash
pip uninstall assemblyai
pip install assemblyai
```

---

### 2. Verifica la versione installata

```bash
pip show assemblyai
```

Dovresti vedere una versione **≥ 0.30.0** (o superiore).

---

### 3. Testa l'applicazione

```bash
python gui_transcriber.py
```

Se vedi ancora errori "Model deprecated", prova:

```bash
pip install --upgrade --force-reinstall assemblyai
```

---

## ✅ Novità della v3 (Universal Streaming)

### **Vantaggi:**

1. ✅ **Latenza ancora più bassa** (~200-400ms invece di 300-500ms)
2. ✅ **Supporto multilingua migliorato** (Inglese, Portoghese, Spagnolo, Francese, Tedesco, Italiano)
3. ✅ **Formattazione automatica** (punteggiatura, capitalizzazione)
4. ✅ **Maggiore accuratezza**
5. ✅ **API più stabile e moderna**

### **Modelli disponibili:**

| Modello | Lingue supportate | Quando usarlo |
|---------|-------------------|---------------|
| `universal-streaming-english` | Solo Inglese | Massima velocità per inglese |
| `universal-streaming-multi` | EN, PT, ES, FR, DE, IT | Multilingua (beta) |

---

## 📝 Cosa è cambiato nel codice:

### **PRIMA (v2 - deprecato):**

```python
transcriber = aai.RealtimeTranscriber(
    sample_rate=16000,
    on_data=callback,
    on_error=error_callback
)
transcriber.connect()
transcriber.stream(audio_bytes)
transcriber.close()
```

### **DOPO (v3 - corrente):**

```python
from assemblyai.streaming.v3 import StreamingClient, StreamingParameters

client = StreamingClient(StreamingClientOptions(api_key=KEY))
client.on(StreamingEvents.Turn, callback)
client.connect(StreamingParameters(
    sample_rate=16000,
    speech_model="universal-streaming-english"
))
client.send_audio(audio_bytes)
client.disconnect(terminate=True)
```

---

## 🔧 Modifiche applicate:

✅ Import aggiornati per v3  
✅ `StreamingClient` al posto di `RealtimeTranscriber`  
✅ Nuovi eventi: `BeginEvent`, `TurnEvent`, `TerminationEvent`  
✅ `send_audio()` al posto di `stream()`  
✅ `disconnect()` al posto di `close()`  
✅ Modello `universal-streaming-multi` per multilingua  

---

## 🐛 Troubleshooting

### Errore: "Model deprecated"

```bash
pip install --upgrade assemblyai
```

### Errore: "No module named 'assemblyai.streaming.v3'"

```bash
pip uninstall assemblyai
pip install assemblyai
```

### Errore: "StreamingClient has no attribute 'stream'"

Assicurati di usare `send_audio()` invece di `stream()`.

### Audio non viene trascritto

1. Verifica che la chiave API sia corretta nel file `.env`
2. Controlla la connessione internet
3. Verifica che il dispositivo audio sia "Loopback" per catturare audio del PC

---

## 📚 Documentazione Ufficiale

- [AssemblyAI Universal Streaming Docs](https://www.assemblyai.com/docs/speech-to-text/universal-streaming)
- [Python SDK v3 Guide](https://www.assemblyai.com/docs/guides/real-time-streaming-transcription)

---

## ✨ Tutto aggiornato!

Il codice in `gui_transcriber.py` è già stato aggiornato alla v3!

Devi solo aggiornare il pacchetto con `pip install --upgrade assemblyai` e sei pronto! 🚀
