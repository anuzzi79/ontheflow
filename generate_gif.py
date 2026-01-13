from PIL import Image, ImageDraw
import math

# Configurazione GIF
WIDTH, HEIGHT = 400, 300
BG_COLOR = (20, 20, 25) # Dark background come l'app
LINE_COLOR = (200, 200, 255) # Bianco/Azzurrino
ROBOT_COLOR = (50, 150, 255) # Blu robotico
PAPER_COLOR = (240, 240, 240)
FRAMES_COUNT = 20

frames = []

def draw_robot(draw, frame_idx):
    # Centro
    cx, cy = WIDTH // 2, HEIGHT // 2
    
    # 1. Foglio/Tablet sul tavolo
    draw.rectangle([cx - 60, cy + 40, cx + 60, cy + 90], fill=(40, 40, 50), outline=LINE_COLOR, width=2)
    draw.rectangle([cx - 50, cy + 50, cx + 50, cy + 80], fill=PAPER_COLOR) # Schermo/Carta bianca

    # 2. Corpo Robot
    draw.arc([cx - 40, cy - 20, cx + 40, cy + 100], start=180, end=0, fill=ROBOT_COLOR, width=0) # Corpo tondo sotto
    draw.rectangle([cx - 30, cy, cx + 30, cy + 60], fill=(30, 30, 40), outline=LINE_COLOR) # Torso

    # 3. Testa Robot (Ovale)
    head_y_offset = math.sin(frame_idx * 0.5) * 2 # Testa che "boba" un po'
    draw.rounded_rectangle([cx - 35, cy - 60 + head_y_offset, cx + 35, cy - 10 + head_y_offset], radius=10, fill=BG_COLOR, outline=LINE_COLOR, width=3)
    
    # Occhi (Lampeggiano al frame 10)
    eye_color = (0, 255, 255) if frame_idx not in [9, 10] else (20, 20, 25)
    draw.ellipse([cx - 20, cy - 45 + head_y_offset, cx - 10, cy - 30 + head_y_offset], fill=eye_color)
    draw.ellipse([cx + 10, cy - 45 + head_y_offset, cx + 20, cy - 30 + head_y_offset], fill=eye_color)

    # Cuffie
    draw.arc([cx - 45, cy - 65 + head_y_offset, cx + 45, cy - 20 + head_y_offset], start=180, end=0, fill=ROBOT_COLOR, width=5)
    draw.rectangle([cx - 48, cy - 45 + head_y_offset, cx - 35, cy - 20 + head_y_offset], fill=ROBOT_COLOR)
    draw.rectangle([cx + 35, cy - 45 + head_y_offset, cx + 48, cy - 20 + head_y_offset], fill=ROBOT_COLOR)

    # 4. Braccio che scrive
    # Movimento oscillatorio veloce per simulare scrittura
    arm_x = math.cos(frame_idx * 1.5) * 15
    
    shoulder_x, shoulder_y = cx + 30, cy + 20
    hand_x, hand_y = cx + arm_x, cy + 65
    
    # Braccio (linea semplice)
    draw.line([shoulder_x, shoulder_y, hand_x, hand_y], fill=LINE_COLOR, width=4)
    # Penna
    draw.line([hand_x, hand_y, hand_x - 5, hand_y + 10], fill=(255, 100, 100), width=2)

    # 5. Scrittura (Linee che appaiono)
    # Simuliamo righe di testo sul foglio
    text_progress = (frame_idx % FRAMES_COUNT) * 2
    if text_progress > 5:
        draw.line([cx - 40, cy + 60, cx - 40 + text_progress, cy + 60], fill=(0,0,0), width=1)
    if text_progress > 20:
        draw.line([cx - 40, cy + 70, cx - 60 + text_progress, cy + 70], fill=(0,0,0), width=1)

# Generazione Frames
for i in range(FRAMES_COUNT):
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(im)
    draw_robot(draw, i)
    frames.append(im)

# Salvataggio GIF
frames[0].save(
    "robot_writing.gif",
    save_all=True,
    append_images=frames[1:],
    duration=100, # ms per frame
    loop=0
)

print("GIF generata: robot_writing.gif")
