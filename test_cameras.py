"""
test_cameras.py
Test rapido per verificare che entrambe le GoPro funzionino
"""

from image_recognition.camera_manager import CameraManager

def main():
    manager = CameraManager()
    
    # Discovery
    num_cameras = manager.discover()
    print(f"\n=== Trovate {num_cameras} camere ===\n")
    
    if num_cameras == 0:
        print("ERRORE: Nessuna camera trovata!")
        return
    
    # Mostra info camere
    for i, cam in enumerate(manager.cameras):
        print(f"Camera {i+1}:")
        print(f"  Device: {cam.device_path}")
        print(f"  Nome: {cam.name}")
        print(f"  Formato: {cam.pixel_format}")
        print(f"  Risoluzione: {cam.width}x{cam.height}")
        print()
    
    # Cattura da tutte
    print("=== Cattura in corso... ===\n")
    images = manager.capture_all(label="test")
    
    print(f"\n=== Risultato ===")
    print(f"Immagini catturate: {len(images)}/{num_cameras}")
    for img in images:
        print(f"  ✓ {img}")

if __name__ == "__main__":
    main()