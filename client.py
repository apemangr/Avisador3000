import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab
import socket
import threading
import time
import os

class ProgressBarMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Avisador 3000!")
        self.root.geometry("350x250")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'icon.ico')
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.bbox = None
        self.is_monitoring = False
        self.monitor_thread = None

        self.select_button = tk.Button(self.root, text="1. Selecciona la región de la  barra", command=self.start_selection)
        self.select_button.pack(pady=10)

        self.ip_label = tk.Label(self.root, text="2. Ingresa la IP del pobre sujeto:")
        self.ip_label.pack()

        self.ip_entry = tk.Entry(self.root, width=25)
        self.ip_entry.pack(pady=5)
        self.ip_entry.insert(0, "192.168.1.100")

        self.monitor_button = tk.Button(self.root, text="3. Comenzar a monitoriar", state=tk.DISABLED, command=self.toggle_monitoring)
        self.monitor_button.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Estado: Esperando por seleccionar una región.", wraplength=340)
        self.status_label.pack(pady=5)

    def start_selection(self):
        self.root.withdraw()
        selection_window = tk.Toplevel()
        selection_window.attributes("-fullscreen", True)
        selection_window.attributes("-alpha", 0.3)
        selection_window.configure(bg="black")
        canvas = tk.Canvas(selection_window, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)
        start_x, start_y, rect = None, None, None

        def on_press(event): nonlocal start_x, start_y, rect; start_x, start_y = event.x, event.y; rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline='red', width=2)
        def on_drag(event): canvas.coords(rect, start_x, start_y, event.x, event.y)
        def on_release(event):
            x1, y1 = min(start_x, event.x), min(start_y, event.y)
            x2, y2 = max(start_x, event.x), max(start_y, event.y)
            selection_window.destroy()
            self.root.deiconify()
            if x2 - x1 > 10 and y2 - y1 > 5:
                self.bbox = (x1, y1, x2, y2)
                self.status_label.config(text="Región seleccionada. Ahora ingresa la IP.")
                self.monitor_button.config(state=tk.NORMAL)
        
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)

    def toggle_monitoring(self):
        if self.is_monitoring:
            self.is_monitoring = False
            self.monitor_button.config(text="3. Comenzar monitoreo.")
            self.status_label.config(text="Se detuvo el monitoreo.")
        else:
            target_ip = self.ip_entry.get()
            if not target_ip: messagebox.showerror("Error", "Ingresa un IP válida!!!"); return
            self.is_monitoring = True
            self.monitor_button.config(text="Detener el monitoreo.")
            self.monitor_thread = threading.Thread(target=self.monitor_loop, args=(target_ip,), daemon=True)
            self.monitor_thread.start()

    def colors_are_similar(self, c1, c2, tol=25): return all(abs(c1[i] - c2[i]) <= tol for i in range(3))

    def monitor_loop(self, target_ip):
        try:
            img = ImageGrab.grab(bbox=self.bbox)
            start_px_x, end_px_x = int(img.width * 0.05), int(img.width * 0.95)
            px_y = int(img.height / 2)

            start_color = img.getpixel((start_px_x, px_y))
            end_color = img.getpixel((end_px_x, px_y))

            
            if not self.colors_are_similar(start_color, end_color):
                # Case A: Barra en progreso
                fill_color, bg_color = start_color, end_color
                self.status_label.config(text="Estado detectado: En progreso. Esperando a que termine...")
                self.wait_for_completion(fill_color, end_px_x, px_y, target_ip)
            else:
                # Case B: Barra vacia o llena.
                bg_color = start_color
                self.status_label.config(text="Estado detectado: Vacío. Esperando a comenzar...")
                fill_color = self.wait_for_start(bg_color, start_px_x, px_y)
                if fill_color and self.is_monitoring:
                    self.status_label.config(text="Inicio el proceso. Esperando a que termine...")
                    self.wait_for_completion(fill_color, end_px_x, px_y, target_ip)

        except Exception as e: self.status_label.config(text=f"Error: {e}")
        finally:
            self.is_monitoring = False
            self.monitor_button.config(text="3. Comenzar monitoreo.")

    def wait_for_start(self, bg_color, x, y):
        while self.is_monitoring:
            current_color = ImageGrab.grab(bbox=self.bbox).getpixel((x, y))
            if not self.colors_are_similar(current_color, bg_color):
                return current_color
            time.sleep(0.2)
        return None

    def wait_for_completion(self, fill_color, x, y, target_ip):
        while self.is_monitoring:
            current_color = ImageGrab.grab(bbox=self.bbox).getpixel((x, y))
            if self.colors_are_similar(current_color, fill_color):
                self.status_label.config(text="Progreso completado! Enviando señal...")
                self.send_network_signal(target_ip)
                break
            time.sleep(0.5)

    def send_network_signal(self, target_ip):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((target_ip, 9999))
                s.sendall(b'ACTION')
            self.status_label.config(text="Señal enviada correctamente!")
        except Exception as e: self.status_label.config(text=f"Error al enviar la señal: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ProgressBarMonitorApp(root)
    root.mainloop()
