import tkinter as tk
from tkinter import messagebox
from PIL import ImageGrab
import socket
import threading
import time
import os
import ctypes
from ctypes import wintypes
import psutil

class ProgressBarMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Avisador 3001!")
        self.root.geometry("350x300")

        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, 'icon.ico')
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)

        self.bbox = None
        self.target_hwnd = None
        self.target_pid = None
        self.is_monitoring = False
        self.monitor_thread = None

        # Configurar funciones de Windows API
        self.setup_windows_api()

        self.select_button = tk.Button(self.root, text="1. Selecciona la ventana a monitorear", command=self.select_window)
        self.select_button.pack(pady=10)

        self.window_info_label = tk.Label(self.root, text="Ninguna ventana seleccionada", wraplength=340)
        self.window_info_label.pack(pady=5)

        self.ip_label = tk.Label(self.root, text="2. Ingresa la IP del servidor:")
        self.ip_label.pack()

        self.ip_entry = tk.Entry(self.root, width=25)
        self.ip_entry.pack(pady=5)
        self.ip_entry.insert(0, "192.168.1.100")

        self.monitor_button = tk.Button(self.root, text="3. Comenzar monitoreo", state=tk.DISABLED, command=self.toggle_monitoring)
        self.monitor_button.pack(pady=10)

        self.status_label = tk.Label(self.root, text="Estado: Esperando seleccionar una ventana.", wraplength=340)
        self.status_label.pack(pady=5)

    def setup_windows_api(self):
        """Configurar las funciones de la API de Windows"""
        # Definir las funciones de Windows API
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        
        # Función para enumerar ventanas
        self.EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        
        # Función para obtener el PID de una ventana
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        
        # Función para verificar si una ventana es visible
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = ctypes.c_bool
        
        # Función para obtener el texto de la ventana
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int

    def select_window(self):
        """Permitir al usuario seleccionar una ventana haciendo clic en ella"""
        self.status_label.config(text="Haz clic en la ventana que quieres monitorear...")
        self.root.withdraw()
        
        # Crear una ventana temporal invisible para capturar el clic
        temp_window = tk.Toplevel()
        temp_window.attributes("-fullscreen", True)
        temp_window.attributes("-alpha", 0.01)  # Casi transparente
        temp_window.configure(bg="black")
        temp_window.configure(cursor="crosshair")
        
        def on_click(event):
            # Obtener las coordenadas del clic en la pantalla
            x, y = temp_window.winfo_pointerx(), temp_window.winfo_pointery()
            temp_window.destroy()
            self.root.deiconify()
            
            # Obtener la ventana en esas coordenadas
            point = wintypes.POINT(x, y)
            hwnd = self.user32.WindowFromPoint(point)
            
            if hwnd:
                self.set_target_window(hwnd)
            else:
                self.status_label.config(text="No se pudo obtener la ventana. Intenta de nuevo.")
        
        temp_window.bind("<Button-1>", on_click)
        temp_window.focus_set()

    def set_target_window(self, hwnd):
        """Establecer la ventana objetivo y obtener su información"""
        try:
            # Obtener el PID de la ventana
            pid = wintypes.DWORD()
            self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            
            # Obtener el título de la ventana
            buffer_size = 512
            buffer = ctypes.create_unicode_buffer(buffer_size)
            self.user32.GetWindowTextW(hwnd, buffer, buffer_size)
            window_title = buffer.value
            
            # Obtener información del proceso
            try:
                process = psutil.Process(pid.value)
                process_name = process.name()
            except:
                process_name = "Desconocido"
            
            self.target_hwnd = hwnd
            self.target_pid = pid.value
            
            info_text = f"Ventana: {window_title}\nProceso: {process_name} (PID: {pid.value})"
            self.window_info_label.config(text=info_text)
            self.status_label.config(text="Ventana seleccionada. Ahora ingresa la IP.")
            self.monitor_button.config(state=tk.NORMAL)
            
        except Exception as e:
            self.status_label.config(text=f"Error al obtener información de la ventana: {e}")

    def window_exists(self, hwnd):
        """Verificar si una ventana todavía existe"""
        try:
            return self.user32.IsWindow(hwnd) and self.user32.IsWindowVisible(hwnd)
        except:
            return False

    def process_exists(self, pid):
        """Verificar si un proceso todavía existe"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except:
            return False

    def toggle_monitoring(self):
        if self.is_monitoring:
            self.is_monitoring = False
            self.monitor_button.config(text="3. Comenzar monitoreo")
            self.status_label.config(text="Se detuvo el monitoreo.")
        else:
            target_ip = self.ip_entry.get()
            if not target_ip: 
                messagebox.showerror("Error", "Ingresa una IP válida!")
                return
            if not self.target_hwnd:
                messagebox.showerror("Error", "Primero selecciona una ventana!")
                return
                
            self.is_monitoring = True
            self.monitor_button.config(text="Detener monitoreo")
            self.monitor_thread = threading.Thread(target=self.monitor_window, args=(target_ip,), daemon=True)
            self.monitor_thread.start()

    def monitor_window(self, target_ip):
        """Monitorear la ventana seleccionada hasta que desaparezca"""
        try:
            self.status_label.config(text="Monitoreando ventana... Esperando a que se cierre.")
            
            # Verificar que la ventana existe al inicio
            if not self.window_exists(self.target_hwnd):
                self.status_label.config(text="Error: La ventana ya no existe.")
                return
            
            # Monitorear la ventana
            while self.is_monitoring:
                # Verificar si la ventana todavía existe
                if not self.window_exists(self.target_hwnd) and not self.process_exists(self.target_pid):
                    self.status_label.config(text="¡La ventana se cerró! Enviando señal...")
                    self.send_network_signal(target_ip)
                    break
                elif not self.window_exists(self.target_hwnd):
                    # La ventana no es visible pero el proceso sigue
                    self.status_label.config(text="Ventana minimizada/oculta. Monitoreando proceso...")
                
                time.sleep(1)  # Verificar cada segundo
                
        except Exception as e:
            self.status_label.config(text=f"Error durante el monitoreo: {e}")
        finally:
            self.is_monitoring = False
            self.monitor_button.config(text="3. Comenzar monitoreo")

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
