# Live Transcriber Pro 🎙️

Applicazione standalone Python con **GUI moderna** per trascrivere in **VERO tempo reale** l'audio di sistema (quello che esce dalle casse/cuffie).

## ⚡ Novità: AssemblyAI Real-Time!

Ora supporta **AssemblyAI Real-Time Streaming** con latenza di **300-500ms** (come ChatGPT)!

### Confronto Motori:

| Motore | Latenza | Qualità | Costo | Internet |
|--------|---------|---------|-------|----------|
| **AssemblyAI Real-Time** ⚡ | **300-500ms** | ⭐⭐⭐⭐⭐ | $0.0077/min | ✅ |
| Whisper Locale | 6-15 secondi | ⭐⭐⭐ | Gratis | ❌ |
| Google Speech | 8-12 secondi | ⭐⭐⭐⭐ | Gratis | ✅ |

---

## 📦 Installazione

### Requisiti

- Python 3.8+
- Windows 10/11 (supporto audio loopback nativo)

### Dipendenze Base

```bash
pip install flet soundcard numpy faster-whisper speech-recognition
```

### Per AssemblyAI Real-Time (CONSIGLIATO)

```bash
pip install assemblyai pyaudio
```

### Opzionale: python-dotenv (per gestione sicura API key)

```bash
pip install python-dotenv
```

---

## 🚀 Avvio Rapido

### Opzione 1: GUI (Consigliata)

```bash
python gui_transcriber.py
```

### Opzione 2: CLI (deprecata)

```bash
python live_transcriber.py
```

---

## 🔑 Setup AssemblyAI Real-Time

Per usare la trascrizione **VERA real-time** (come ChatGPT):

### 1. Ottieni la chiave API GRATUITA

1. Vai su: https://www.assemblyai.com/dashboard/signup
2. Registrati (email + password)
3. Copia la chiave API dalla dashboard
4. Ottieni **$50 crediti gratuiti** (~6.500 minuti!)

### 2. Configura la chiave

**Metodo A - Direttamente nel codice:**

Apri `gui_transcriber.py` e cerca (riga ~44):

```python
self.ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "YOUR_API_KEY_HERE")
```

Sostituisci `YOUR_API_KEY_HERE` con la tua chiave reale.

**Metodo B - File .env (più sicuro):**

1. Crea file `.env` nella cartella `ontheflow`
2. Scrivi: `ASSEMBLYAI_API_KEY=tua-chiave-qui`
3. Installa: `pip install python-dotenv`

### 3. Test configurazione

```bash
python test_assemblyai.py
```

Se tutto OK, vedrai: ✅ **TUTTO OK!**

---

## 🎯 Come Usare

1. Avvia `python gui_transcriber.py`
2. Seleziona **Audio Source** (dispositivo loopback per catturare audio del PC)
3. Seleziona **Language** (English o Português)
4. Seleziona **Engine**:
   - **AssemblyAI Real-Time** ⚡ - Latenza 300-500ms (CONSIGLIATO)
   - Google - Latenza ~10s (gratis, richiede internet)
   - Whisper - Latenza 6-15s (gratis, offline)
5. Clicca **START RECORDING**
6. Parla o riproduci audio → trascrizione appare **ISTANTANEAMENTE**!

---

## 💰 Costi AssemblyAI

- **Crediti gratuiti**: $50 (~6.500 minuti = 108 ore)
- **Pay-as-you-go**: $0.0077/minuto (~$0.46/ora)
- **Esempi**:
  - 2 ore/giorno: ~$28/mese (dopo crediti gratuiti)
  - 8 ore/giorno: ~$110/mese

**Alternative economiche**:
- AssemblyAI streaming: $0.00047/min (4x più economico!)
- OpenAI Whisper API: $0.006/min

---

## 📁 File Principali

- `gui_transcriber.py` - **Applicazione GUI principale** (USA QUESTO!)
- `test_assemblyai.py` - Test configurazione API key
- `ASSEMBLYAI_SETUP.md` - Istruzioni dettagliate setup
- `live_transcriber.py` - Versione CLI (deprecata)

---

## 🐛 Troubleshooting

### "Invalid API Key"
- Verifica chiave su: https://www.assemblyai.com/dashboard
- Controlla nessuno spazio prima/dopo la chiave
- Riavvia l'app dopo aver modificato la chiave

### "Audio device not found"
- Seleziona dispositivo **Loopback** (cattura audio PC)
- Clicca 🔄 Refresh per aggiornare lista

### "Module not found"
```bash
pip install assemblyai pyaudio flet soundcard numpy faster-whisper
```

### Latenza ancora alta con AssemblyAI
- Verifica connessione internet stabile
- Controlla che hai selezionato "AssemblyAI Real-Time" nel dropdown
- AssemblyAI invia risultati ogni ~1-2 secondi (frase completa)

---

## 🎉 Features

✅ **3 motori di trascrizione** (AssemblyAI, Google, Whisper)  
✅ **GUI moderna** con tema dark  
✅ **Latenza ultra-bassa** (300-500ms con AssemblyAI)  
✅ **Supporto multilingua** (English, Português)  
✅ **Cattura audio loopback** (PC audio)  
✅ **Export automatico** logs in Documents/LiveTranscriber_Logs  
✅ **Copy/Paste** integrato  
✅ **Orologio sincronizzato**  

---

## 📚 Documentazione Completa

Vedi `ASSEMBLYAI_SETUP.md` per istruzioni dettagliate.

---

## 🤝 Supporto

Per problemi o domande:
1. Verifica `ASSEMBLYAI_SETUP.md`
2. Esegui `python test_assemblyai.py`
3. Controlla console per errori dettagliati

---

**Powered by Google Speech, Whisper AI & AssemblyAI** 🚀
