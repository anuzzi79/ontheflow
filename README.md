# Live Transcriber

Applicazione standalone Python per trascrivere in tempo reale l'audio di sistema (quello che esce dalle casse/cuffie) dall'Inglese al testo.

## Requisiti

- Python 3.8+
- Su Windows, non sono necessari driver aggiuntivi per l'audio.

## Installazione

Se non l'hai già fatto, installa le dipendenze:

```bash
pip install soundcard soundfile numpy faster-whisper
```

## Utilizzo

1. Apri un terminale nella cartella del progetto.
2. Esegui lo script:

```bash
python live_transcriber.py
```

3. Riproduci un video YouTube, un film o partecipa a una chiamata in lingua **Inglese**.
4. Il testo trascritto apparirà nel terminale.

## Configurazione

Nel file `live_transcriber.py` puoi modificare queste variabili all'inizio del file:

- `MODEL_SIZE`: "tiny.en" (veloce), "base.en" (bilanciato), "small.en" (preciso ma lento).
- `DEVICE_TYPE`: "cpu" o "cuda" (se hai una GPU NVIDIA).
