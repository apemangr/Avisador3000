import socket
import tkinter as tk
from PIL import Image, ImageTk
from playsound import playsound
import threading
import os

# --- CONFIGURACIÓN ---
HOST = '0.0.0.0'  # Escuchar en todas las interfaces de red
PORT = 9999       # Puerto para la comunicación

# Obtener la ruta absoluta del directorio donde se encuentra el script
script_dir = os.path.dirname(os.path.abspath(__file__))
IMAGE_FILE = os.path.join(script_dir, 'scare.jpg')
SOUND_FILE = os.path.join(script_dir, 'notification.mp3')
ICON_FILE = os.path.join(script_dir, 'icon.ico')

def show_image_and_play_sound():
    """Crea una ventana emergente con la imagen y reproduce el sonido."""
    try:
        # Reproducir sonido
        if os.path.exists(SOUND_FILE):
            threading.Thread(target=playsound, args=(SOUND_FILE,), daemon=True).start()
        else:
            print(f"Advertencia: No se encontró el archivo de sonido '{SOUND_FILE}'")

        # Configurar la ventana emergente
        root = tk.Tk()
        root.title("¡Sorpresa!")
        
        # Establecer el ícono de la ventana
        if os.path.exists(ICON_FILE):
            root.iconbitmap(ICON_FILE)
        else:
            print(f"Advertencia: No se encontró el archivo de ícono '{ICON_FILE}'")

        root.attributes('-fullscreen', True)
        root.attributes('-topmost', True)

        if os.path.exists(IMAGE_FILE):
            # Cargar y mostrar la imagen
            img = Image.open(IMAGE_FILE)
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()
            img = img.resize((screen_width, screen_height))
            img_tk = ImageTk.PhotoImage(img)
            label = tk.Label(root, image=img_tk)
            label.pack()
        else:
            print(f"Advertencia: No se encontró el archivo de imagen '{IMAGE_FILE}'")
            label = tk.Label(root, text=f"¡Alerta!\nNo se encontró '{IMAGE_FILE}'", font=("Arial", 30))
            label.pack(padx=50, pady=50)

        root.after(2000, root.destroy)
        root.mainloop()

    except Exception as e:
        print(f"Error al mostrar la alerta: {e}")

def start_server():
    """Inicia el servidor para escuchar conexiones entrantes."""
    print(f"Servidor iniciando en {HOST}:{PORT}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor escuchando en el puerto {PORT}...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Conexión recibida de {addr}")
                data = conn.recv(1024)
                if data == b'ACTION':
                    print("¡Señal recibida! Activando alerta...")
                    show_image_and_play_sound()

if __name__ == "__main__":
    start_server()
