"""
camera_manager.py

Gestisce la cattura di immagini dalle camere del frigo.
Non sa niente dei dettagli delle camere: tutto il lavoro di
discovery e configurazione lo fa camera_discoverer.

Uso:
    from image_recognition.camera_manager import CameraManager

    manager = CameraManager()
    manager.discover()
    images = manager.capture_all(label="fridge")
"""

from pathlib import Path
from datetime import datetime
from typing import List
from image_recognition.camera_discoverer import discover
from logger.logger import get_logger


class CameraManager:
    """
    Orchestra discovery e cattura delle camere.
    """

    def __init__(self, image_dir: str = "captured_images", max_retries: int = 3):
        """
        Args:
            image_dir: Directory dove salvare le immagini
            max_retries: Numero massimo di tentativi per camera
        """
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(exist_ok=True)
        self.max_retries = max_retries
        self.cameras = []
        self.logger = get_logger('camera_manager')

    def discover(self) -> int:
        """
        Scansiona il sistema e trova le camere disponibili.

        Returns:
            Numero di camere trovate
        """
        self.cameras = discover()
        return len(self.cameras)

    def capture_all(self, label: str = "fridge") -> List[str]:
        """
        Cattura un'immagine da ogni camera disponibile.

        Args:
            label: Etichetta per i nomi file (es. "fridge" -> "fridge_cam_video7_20260203_120000.jpg")

        Returns:
            Lista dei percorsi delle immagini catturate con successo
        """
        if not self.cameras:
            self.logger.error("Nessuna camera disponibile. Esegui discover() prima.")
            return []

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        captured = []

        for camera in self.cameras:
            image_path = self._capture_with_retry(camera, label, timestamp)
            if image_path:
                captured.append(image_path)

        self.logger.info(f"Catturate {len(captured)}/{len(self.cameras)} immagini")
        return captured

    def _capture_with_retry(self, camera, label: str, timestamp: str) -> str | None:
        """
        Tenta la cattura da una camera con retry automatico.

        Returns:
            Percorso dell'immagine salvata, None se tutti i tentativi falliti
        """
        # Nome file dal device path: /dev/video7 -> video7
        device_name = Path(camera.device_path).name
        filename = f"{label}_{device_name}_{timestamp}.jpg"
        filepath = str(self.image_dir / filename)

        for attempt in range(self.max_retries):
            self.logger.info(f"Tentativo {attempt + 1}/{self.max_retries} per {camera.device_path}")
            if camera.capture(filepath):
                return filepath
            self.logger.warning(f"Tentativo {attempt + 1} fallito per {camera.device_path}")

        self.logger.error(f"Tutti i tentativi falliti per {camera.device_path}")
        return None

    def get_camera_count(self) -> int:
        return len(self.cameras)