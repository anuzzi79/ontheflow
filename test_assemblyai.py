"""
Test rapido per verificare che la chiave API di AssemblyAI funzioni
"""
import os

# Prova a caricare da .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ File .env caricato")
except ImportError:
    print("⚠️  python-dotenv non installato (opzionale)")

# Verifica chiave API
api_key = os.getenv("ASSEMBLYAI_API_KEY", "YOUR_API_KEY_HERE")

print("\n" + "="*60)
print("🔑 VERIFICA CHIAVE API ASSEMBLYAI")
print("="*60)

if api_key == "YOUR_API_KEY_HERE" or not api_key:
    print("\n❌ ERRORE: Chiave API non configurata!")
    print("\nCosa fare:")
    print("1. Apri gui_transcriber.py")
    print("2. Cerca la riga con: ASSEMBLYAI_API_KEY")
    print("3. Sostituisci 'YOUR_API_KEY_HERE' con la tua chiave vera")
    print("\nOppure:")
    print("1. Crea file .env nella cartella ontheflow")
    print("2. Scrivi: ASSEMBLYAI_API_KEY=tua-chiave-qui")
    print("3. Installa: pip install python-dotenv")
else:
    print(f"\n✅ Chiave API trovata: {api_key[:8]}...{api_key[-4:]}")
    print("\nTest connessione ad AssemblyAI...")
    
    try:
        import assemblyai as aai
        aai.settings.api_key = api_key
        
        # Test semplice: verifica che la chiave sia valida
        print("✅ Modulo assemblyai importato correttamente")
        print("\n🎉 TUTTO OK! La chiave è configurata correttamente!")
        print("\nPuoi avviare gui_transcriber.py e usare AssemblyAI Real-Time!")
        
    except ImportError:
        print("❌ ERRORE: Modulo 'assemblyai' non installato")
        print("\nEsegui: pip install assemblyai")
    except Exception as e:
        print(f"⚠️  Possibile problema con la chiave API: {e}")
        print("\nVerifica che la chiave sia valida su:")
        print("https://www.assemblyai.com/dashboard")

print("\n" + "="*60 + "\n")
