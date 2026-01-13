import soundcard as sc

print("Speakers:")
for s in sc.all_speakers():
    print(f" - {s.name} (ID: {s.id})")

print("\nMicrophones (include_loopback=True):")
for m in sc.all_microphones(include_loopback=True):
    print(f" - {m.name} (ID: {m.id}, Loopback: {m.isloopback})")
