# 🚀 AssemblyAI Real-Time Setup - Istruzioni

## ✅ Hai completato:
- ✅ Installato `assemblyai` e `pyaudio`
- ✅ Ottenuto la chiave API da https://www.assemblyai.com/dashboard

---

## 🔑 STEP FINALE: Inserire la chiave API

Hai **2 opzioni** per inserire la tua chiave API:

### **OPZIONE 1: Direttamente nel codice** (più semplice)

1. Apri il file `gui_transcriber.py`
2. Cerca la riga **44-47** (nella classe `TranscriberApp.__init__`):

```python
self.ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "YOUR_API_KEY_HERE")
```

3. Sostituisci `YOUR_API_KEY_HERE` con la tua chiave API reale:

```python
self.ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "abc123def456...")  # <-- LA TUA CHIAVE
```

4. Salva il file

---

### **OPZIONE 2: File .env** (più sicuro, consigliato)

1. Crea un file chiamato `.env` nella cartella `ontheflow\`
2. Apri il file `.env` e scrivi:

```
ASSEMBLYAI_API_KEY=abc123def456...
```

(sostituisci `abc123def456...` con la tua chiave reale)

3. Installa `python-dotenv`:

```bash
pip install python-dotenv
```

4. Il codice caricherà automaticamente la chiave da `.env`!

---

## 🎯 Come usare AssemblyAI Real-Time

1. Avvia il programma: `python gui_transcriber.py`
2. Nel dropdown **"Engine"**, seleziona:
   - **"AssemblyAI Real-Time ⚡ (FASTEST - like ChatGPT)"**
3. Seleziona il dispositivo audio
4. Seleziona la lingua (English o Português)
5. Clicca **START RECORDING**
6. **Parla normalmente** → la trascrizione appare **ISTANTANEAMENTE** (300-500ms)!

---

## ⚡ DIFFERENZE rispetto a Whisper/Google

| Caratteristica | AssemblyAI | Whisper Locale | Google |
|----------------|------------|----------------|--------|
| **Latenza** | **300-500ms** ⚡ | 6-15 secondi 😱 | 8-12 secondi |
| **Qualità ChatGPT** | ✅ SÌ | ❌ NO | ❌ NO |
| **Costo** | $0.0077/min | Gratis | Gratis |
| **Internet** | Richiesto | NO | Richiesto |
| **Buffer** | 100ms | 4-10 secondi | 10 secondi |

---

## 💰 Costi (con $50 crediti gratuiti)

- **2 ore/giorno**: ~$28/mese (dopo crediti gratis)
- **8 ore/giorno**: ~$110/mese
- **Crediti gratis**: ~26.000 minuti (~433 ore!)

---

## 🐛 Troubleshooting

### Errore: "Invalid API Key"
- Verifica di aver copiato la chiave completa
- Controlla che non ci siano spazi prima/dopo la chiave
- Ricontrolla su: https://www.assemblyai.com/dashboard

### Errore: "Module 'assemblyai' not found"
```bash
pip install assemblyai
```

### Audio non catturato
- Verifica che il dispositivo audio sia "Loopback" (per catturare audio del PC)
- Riavvia l'applicazione

### Trascrizione non appare
- Controlla la console per messaggi di errore
- Verifica connessione internet
- Aspetta ~5 secondi dopo START prima di parlare

---

## 🎉 FATTO!

Ora hai una trascrizione **VERA real-time** come ChatGPT! 

Buon divertimento! 🚀
