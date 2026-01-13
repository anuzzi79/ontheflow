from moviepy.editor import VideoFileClip

try:
    print("Caricamento video...")
    clip = VideoFileClip("RobotAnotation.mp4")

    print("Salvataggio frame statico...")
    clip.save_frame("robot_static.png", t=0)

    print("Conversione GIF...")
    # Resize a 200px di altezza per buona qualità ma file leggero
    clip_resized = clip.resize(height=200)
    clip_resized.write_gif("robot_anim.gif", fps=15)
    print("Fatto!")
except Exception as e:
    print(f"Errore: {e}")
