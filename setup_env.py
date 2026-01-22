"""
Script per creare/aggiornare il file .env con la configurazione di AssemblyAI
Esegui: python setup_env.py
"""

import os

# Contenuto del file .env
env_content = """# ════════════════════════════════════════════════════════════
# AssemblyAI Real-Time Configuration
# ════════════════════════════════════════════════════════════
#
# IMPORTANTE: Sostituisci YOUR_API_KEY_HERE con la tua chiave reale!
#
# La tua chiave API la trovi su: https://www.assemblyai.com/dashboard
#
# ════════════════════════════════════════════════════════════

ASSEMBLYAI_API_KEY=YOUR_API_KEY_HERE

# ════════════════════════════════════════════════════════════
# Istruzioni:
# 1. Copia la tua chiave API da AssemblyAI Dashboard
# 2. Apri questo file .env con un editor di testo
# 3. Sostituisci YOUR_API_KEY_HERE con la tua chiave reale
# 4. Salva il file
# 5. Installa: pip install python-dotenv
# 6. Esegui: python gui_transcriber.py
#
# Note:
# - Mantieni questo file PRIVATO (non caricarlo su GitHub!)
# - Il file .env e' gia' in .gitignore
# - Hai $50 di crediti GRATUITI (~6.500 minuti)
# ════════════════════════════════════════════════════════════
"""

# Percorso del file .env
env_file = os.path.join(os.path.dirname(__file__), ".env")

print("=" * 60)
print("SETUP FILE .ENV")
print("=" * 60)
print()

# Crea/sovrascrive il file (NON chiede conferma)
try:
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("OK! File .env creato/aggiornato con successo!")
    print(f"Percorso: {env_file}")
    print()
    print("=" * 60)
    print("PROSSIMI PASSI:")
    print("=" * 60)
    print()
    print("1. Apri il file .env con Blocco Note:")
    print(f"   notepad \"{env_file}\"")
    print()
    print("2. Trova la riga:")
    print("   ASSEMBLYAI_API_KEY=YOUR_API_KEY_HERE")
    print()
    print("3. Sostituisci YOUR_API_KEY_HERE con la tua chiave reale")
    print("   (quella che hai copiato da assemblyai.com/dashboard)")
    print()
    print("4. Salva il file (Ctrl+S)")
    print()
    print("5. Installa python-dotenv (se non gia' fatto):")
    print("   pip install python-dotenv")
    print()
    print("6. Testa la configurazione:")
    print("   python test_assemblyai.py")
    print()
    print("7. Se il test OK, avvia l'applicazione:")
    print("   python gui_transcriber.py")
    print()
    print("=" * 60)
    print("FATTO!")
    print("=" * 60)
    
except Exception as e:
    print(f"ERRORE durante la creazione del file: {e}")
    print()
    print("SOLUZIONE ALTERNATIVA:")
    print("1. Apri Blocco Note")
    print("2. Copia il contenuto seguente:")
    print()
    print("-" * 60)
    print(env_content)
    print("-" * 60)
    print()
    print("3. Salva come: .env")
    print(f"4. Nella cartella: {os.path.dirname(env_file) or os.getcwd()}")

print()
