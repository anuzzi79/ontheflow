@echo off
chcp 65001 >nul
cls

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║                                                               ║
echo ║           🎙️  LIVE TRANSCRIBER PRO - ASSEMBLYAI ⚡            ║
echo ║                                                               ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
echo 📋 Controllo dipendenze...
echo.

REM Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trovato! Installa Python 3.8+ da python.org
    pause
    exit /b 1
)

echo ✅ Python installato
echo.

REM Test configurazione AssemblyAI
echo 🔑 Verifica configurazione AssemblyAI...
python test_assemblyai.py
echo.

if errorlevel 1 (
    echo.
    echo ⚠️  ATTENZIONE: Problemi con la configurazione AssemblyAI
    echo.
    echo 📝 COSA FARE:
    echo 1. Apri gui_transcriber.py
    echo 2. Cerca la riga con ASSEMBLYAI_API_KEY
    echo 3. Sostituisci YOUR_API_KEY_HERE con la tua chiave reale
    echo.
    echo Vedi: ISTRUZIONI_RAPIDE.txt
    echo.
    echo Premi un tasto per avviare comunque (puoi usare Whisper/Google)...
    pause >nul
)

echo.
echo 🚀 Avvio Live Transcriber Pro...
echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.

python gui_transcriber.py

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo.
echo 👋 Applicazione chiusa. Grazie per aver usato Live Transcriber Pro!
echo.
pause
