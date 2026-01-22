"""
Script per creare il file .env con la configurazione di AssemblyAI
Esegui: python create_env_file.py
"""

import os

# Contenuto del file .env
env_content = """# ════════════════════════════════════════════════════════════
# AssemblyAI Real-Time Configuration
# ════════════════════════════════════════════════════════════
#
# ⚠️  IMPORTANTE: Sostituisci YOUR_API_KEY_HERE con la tua chiave reale!
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
# - Il file .env è già in .gitignore
# - Hai $50 di crediti GRATUITI (~6.500 minuti)
# ════════════════════════════════════════════════════════════
"""

# Percorso del file .env
env_file = os.path.join(os.path.dirname(__file__), ".env")

print("=" * 60)
print("CREAZIONE FILE .ENV")
print("=" * 60)
print()

# Controlla se esiste già
if os.path.exists(env_file):
    risposta = input("Il file .env esiste gia. Sovrascriverlo? (s/n): ")
    if risposta.lower() not in ['s', 'si', 'y', 'yes']:
        print("\nOperazione annullata.")
        print(f"File esistente: {env_file}")
        print()
        input("Premi INVIO per uscire...")
        exit(0)

# Crea il file
try:
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)
    
    print("OK! File .env creato con successo!")
    print(f"Percorso: {env_file}")
    print()
    print("=" * 60)
    print("PROSSIMI PASSI:")
    print("=" * 60)
    print()
    print("1. Apri il file .env con un editor di testo (Blocco Note)")
    print("2. Trova la riga: ASSEMBLYAI_API_KEY=YOUR_API_KEY_HERE")
    print("3. Sostituisci YOUR_API_KEY_HERE con la tua chiave reale")
    print("4. Salva il file")
    print()
    print("Esempio:")
    print("  ASSEMBLYAI_API_KEY=abc123def456...")
    print()
    print("5. Installa python-dotenv:")
    print("   pip install python-dotenv")
    print()
    print("6. Testa la configurazione:")
    print("   python test_assemblyai.py")
    print()
    print("7. Avvia l'applicazione:")
    print("   python gui_transcriber.py")
    print()
    print("=" * 60)
    print("Fatto! Segui i passi sopra per completare la configurazione.")
    print("=" * 60)
    
except Exception as e:
    print(f"ERRORE durante la creazione del file: {e}")
    print()
    print("SOLUZIONE ALTERNATIVA:")
    print("1. Crea manualmente un file chiamato: .env")
    print(f"2. Nella cartella: {os.path.dirname(env_file)}")
    print("3. Copia dentro il contenuto seguente:")
    print()
    print("-" * 60)
    print(env_content)
    print("-" * 60)

print()
input("Premi INVIO per uscire...")
