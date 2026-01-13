from PIL import Image, ImageDraw
import os

def create_robot_gif():
    # Configurazione
    width, height = 200, 200
    frames = []
    bg_color = (20, 20, 30) # Dark blue background (Flet style)
    robot_color = (200, 200, 200)
    eye_color = (0, 255, 255) # Cyan eyes
    paper_color = (255, 255, 255)
    
    # Coordinate base Robot
    head_rect = [70, 50, 130, 100]
    body_rect = [80, 100, 120, 150]
    eye_l = [80, 65, 90, 75]
    eye_r = [110, 65, 120, 75]
    
    # Carta
    paper_rect = [60, 150, 140, 180]

    # Genera 10 frame di animazione
    for i in range(10):
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Disegna Carta
        draw.rectangle(paper_rect, fill=paper_color)
        
        # Disegna Testo sulla carta (simulato con linee)
        line_progress = i * 6
        if line_progress > 0:
            draw.line([70, 160, 70 + line_progress, 160], fill=(0,0,0), width=2)
        if i > 5:
            draw.line([70, 170, 70 + (i-5)*6, 170], fill=(0,0,0), width=2)

        # Disegna Robot (Corpo, Testa, Occhi)
        draw.rectangle(body_rect, fill=robot_color, outline=(100,100,100))
        draw.rectangle(head_rect, fill=robot_color, outline=(100,100,100))
        draw.ellipse(eye_l, fill=eye_color)
        draw.ellipse(eye_r, fill=eye_color)
        
        # Cuffie (Ispirato all'immagine)
        draw.arc([60, 40, 140, 90], start=180, end=0, fill=(50, 50, 255), width=5)
        draw.rectangle([60, 55, 70, 85], fill=(50, 50, 255)) # Ear L
        draw.rectangle([130, 55, 140, 85], fill=(50, 50, 255)) # Ear R

        # Braccio che si muove (Animazione)
        # Il braccio va avanti e indietro
        arm_x = 100 + (i % 5) * 5
        if i >= 5: arm_x = 125 - (i % 5) * 5
        
        # Spalla -> Mano
        draw.line([120, 110, arm_x, 160], fill=robot_color, width=5)
        # Penna
        draw.line([arm_x, 160, arm_x - 5, 175], fill=(255, 0, 0), width=2)

        frames.append(img)

    # Salva GIF
    frames[0].save('robot_writing.gif', save_all=True, append_images=frames[1:], duration=100, loop=0)
    print("GIF creata: robot_writing.gif")

if __name__ == "__main__":
    create_robot_gif()
