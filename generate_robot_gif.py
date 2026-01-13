from PIL import Image, ImageDraw
import math

def create_robot_gif():
    width, height = 300, 300
    bg_color = (15, 15, 20) # Dark background
    robot_color = (200, 200, 220)
    cyan_glow = (0, 255, 255)
    
    frames = []
    
    # Parametri animazione
    num_frames = 10
    
    for i in range(num_frames):
        # Crea canvas
        im = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(im)
        
        # --- DISEGNO ROBOT (Stilizzato) ---
        
        # Corpo
        draw.rectangle([100, 150, 200, 250], fill=(50, 50, 60))
        
        # Testa
        draw.rounded_rectangle([110, 80, 190, 150], radius=15, fill=robot_color)
        
        # Occhi (Visore)
        draw.rectangle([125, 100, 175, 120], fill=(0, 0, 0))
        # Occhi luminosi (Ciano)
        draw.ellipse([135, 105, 145, 115], fill=cyan_glow)
        draw.ellipse([155, 105, 165, 115], fill=cyan_glow)
        
        # Cuffie (Ispirate all'immagine)
        draw.ellipse([95, 90, 115, 140], fill=(30, 30, 40), outline=cyan_glow, width=2) # SX
        draw.ellipse([185, 90, 205, 140], fill=(30, 30, 40), outline=cyan_glow, width=2) # DX
        draw.arc([105, 75, 195, 120], start=180, end=0, fill=(30, 30, 40), width=5) # Archetto
        
        # Tavolo
        draw.rectangle([50, 250, 250, 260], fill=(80, 80, 90))
        
        # Foglio/Tablet
        draw.polygon([(100, 250), (200, 250), (220, 220), (120, 220)], fill=(240, 240, 250))
        
        # Testo sul foglio (righe finte)
        draw.line([130, 230, 190, 230], fill=(0, 0, 0), width=1)
        draw.line([125, 235, 185, 235], fill=(0, 0, 0), width=1)
        draw.line([135, 240, 175, 240], fill=(0, 0, 0), width=1)

        # --- ANIMAZIONE BRACCIO ---
        # Il braccio si muove a destra e sinistra come se scrivesse
        offset_x = math.sin((i / num_frames) * 2 * math.pi) * 15
        
        hand_x = 160 + offset_x
        hand_y = 230
        
        # Braccio (Linea dalla spalla alla mano)
        shoulder_x, shoulder_y = 180, 180
        elbow_x, elbow_y = 210, 200
        
        # Disegna braccio articolato
        draw.line([shoulder_x, shoulder_y, elbow_x, elbow_y], fill=robot_color, width=8)
        draw.line([elbow_x, elbow_y, hand_x, hand_y], fill=robot_color, width=6)
        
        # Mano/Penna
        draw.ellipse([hand_x-5, hand_y-5, hand_x+5, hand_y+5], fill=cyan_glow)
        # Penna
        draw.line([hand_x, hand_y, hand_x-5, hand_y+10], fill=(20, 20, 20), width=2)
        
        # Scintille di scrittura (opzionale)
        if i % 2 == 0:
            draw.point([hand_x-5, hand_y+12], fill=cyan_glow)

        frames.append(im)

    # Salva GIF
    frames[0].save(
        'robot_typing.gif',
        save_all=True,
        append_images=frames[1:],
        optimize=False,
        duration=100, # ms per frame
        loop=0
    )
    print("GIF 'robot_typing.gif' generata con successo!")

if __name__ == "__main__":
    create_robot_gif()
