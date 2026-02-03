"""
camera_discoverer.py

Responsabilità:
- Liberare i dispositivi video da PipeWire (fuser -k)
- Scansionare i dispositivi disponibili (v4l2-ctl)
- Determinare formato e risoluzione di ogni camera
- Restituire oggetti Camera pronti per la cattura

Uso:
    from image_recognition.camera_discoverer import discover
    cameras = discover()
    for cam in cameras:
        cam.capture("captured_images/foto.jpg")
"""

import subprocess
import re
from pathlib import Path
from logger.logger import get_logger

logger = get_logger('discoverer')

# Nomi dei dispositivi GoPro da cercare nell'output di v4l2-ctl
TARGET_DEVICE_NAMES = ["GENERAL - UVC", "MMP SDK"]


class Camera:
    """
    Rappresenta una singola camera USB.
    Contiene tutto quello serve per catturare un'immagine
    senza che il chiamante debba preoccuparsi dei dettagli.
    """

    def __init__(self, device_path: str, name: str, pixel_format: str,
                 width: int, height: int):
        """
        Args:
            device_path: es. "/dev/video7"
            name: nome del dispositivo (es. "GENERAL - UVC")
            pixel_format: formato video (es. "MJPG", "YUY2")
            width: larghezza in pixel
            height: altezza in pixel
        """
        self.device_path = device_path
        self.name = name
        self.pixel_format = pixel_format
        self.width = width
        self.height = height
        self.logger = get_logger('camera')

    def capture(self, output_path: str) -> bool:
        """
        Cattura un singolo frame e lo salva come immagine.

        Args:
            output_path: percorso del file di output (es. "captured_images/foto.jpg")

        Returns:
            True se la cattura è riuscita, False altrimenti
        """
        # Costruisci pipeline GStreamer in base al formato
        pipeline = self._build_pipeline(output_path)

        try:
            self.logger.info(f"Capturing from {self.device_path} ({self.name})")
            result = subprocess.run(
                pipeline,
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                self.logger.error(f"GStreamer error on {self.device_path}: {result.stderr}")
                return False

            # Verifica che il file sia stato creato e non sia vuoto
            path = Path(output_path)
            if path.exists() and path.stat().st_size > 0:
                self.logger.info(f"Saved: {output_path} ({path.stat().st_size} bytes)")
                return True
            else:
                self.logger.error(f"Output file missing or empty: {output_path}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Capture timeout on {self.device_path}")
            return False
        except Exception as e:
            self.logger.error(f"Capture error on {self.device_path}: {e}")
            return False

    def _build_pipeline(self, output_path: str) -> list:
        """
        Costruisce il comando GStreamer in base al formato della camera.

        Per MJPG: v4l2src -> jpegdec -> videoconvert -> jpegenc -> filesink
        Per altri formati (YUY2, ecc): v4l2src -> videoconvert -> jpegenc -> filesink
        """
        pipeline = ["gst-launch-1.0"]

        # Sorgente: v4l2src con un solo frame
        pipeline += [
            "v4l2src",
            f"device={self.device_path}",
            "num-buffers=1",
        ]

        # Se il formato è MJPG serve decodificare prima
        if self.pixel_format == "MJPG":
            pipeline += ["!", "image/jpeg", "!", "jpegdec"]

        # Conversione e salvataggio
        pipeline += ["!", "videoconvert", "!", "jpegenc", "!", "filesink", f"location={output_path}"]

        return pipeline

    def __repr__(self):
        return f"Camera({self.device_path}, {self.name}, {self.pixel_format}, {self.width}x{self.height})"


def discover() -> list:
    """
    Scansiona il sistema e restituisce le camere USB disponibili.

    Sequenza:
        1. Libera tutti i /dev/video* da PipeWire con fuser -k
        2. Trova i dispositivi target con v4l2-ctl --list-devices
        3. Legge formato e risoluzione con v4l2-ctl --list-formats-ext
        4. Restituisce lista di oggetti Camera

    Returns:
        List[Camera]: Lista delle camere trovate e configurate
    """
    _release_devices()
    device_paths = _find_target_devices()
    cameras = []

    for path, name in device_paths:
        fmt = _get_device_format(path)
        if fmt is None:
            logger.warning(f"Cannot read format for {path}, skipping")
            continue

        pixel_format, width, height = fmt
        cameras.append(Camera(path, name, pixel_format, width, height))
        logger.info(f"Found: {path} | {name} | {pixel_format} {width}x{height}")

    if not cameras:
        logger.error("No cameras found")
    else:
        logger.info(f"Discovery complete: {len(cameras)} camera(s)")

    return cameras


def _release_devices():
    """
    Chiude tutti i processi che tengono occupati i dispositivi video.
    Necessario perché PipeWire li occupa per default nel desktop.
    """
    logger.info("Releasing video devices from PipeWire...")
    try:
        # Trova tutti i /dev/video* esistenti
        import glob
        devices = glob.glob("/dev/video*")
        if devices:
            subprocess.run(
                ["fuser", "-k"] + devices,
                capture_output=True, text=True, timeout=5
            )
    except Exception as e:
        logger.warning(f"fuser -k error (non critico): {e}")


def _find_target_devices() -> list:
    """
    Parsa output di v4l2-ctl --list-devices e trova i dispositivi target.

    Returns:
        List[Tuple[str, str]]: Lista di (device_path, nome_dispositivo)
        es. [("/dev/video7", "GENERAL - UVC"), ("/dev/video8", "MMP SDK")]
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "--list-devices"],
            capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            logger.error(f"v4l2-ctl --list-devices error: {result.stderr}")
            return []

        devices = []
        current_name = None
        first_entry = True

        for line in result.stdout.strip().split('\n'):
            stripped = line.strip()

            if not stripped.startswith('/dev/'):
                # Riga con nome dispositivo: verifica se è un target
                matched_name = None
                for target in TARGET_DEVICE_NAMES:
                    if target in stripped:
                        matched_name = target
                        break
                current_name = matched_name
                first_entry = True
                continue

            # Riga /dev/video* : prendiamo solo il primo per dispositivo
            if current_name and first_entry and stripped.startswith('/dev/video'):
                devices.append((stripped, current_name))
                first_entry = False

        return devices

    except Exception as e:
        logger.error(f"Error finding devices: {e}")
        return []


def _get_device_format(device_path: str) -> tuple:
    """
    Legge formato e risoluzione di un dispositivo con v4l2-ctl --list-formats-ext.

    Returns:
        Tuple[str, int, int]: (pixel_format, width, height)
        es. ("MJPG", 1280, 720)
        None se non riuscito a leggere
    """
    try:
        result = subprocess.run(
            ["v4l2-ctl", "-d", device_path, "--list-formats-ext"],
            capture_output=True, text=True, timeout=5
        )

        if result.returncode != 0:
            logger.error(f"v4l2-ctl --list-formats-ext error on {device_path}: {result.stderr}")
            return None

        # Cerca il formato: riga tipo  [0]: 'MJPG' (Motion-JPEG, compressed)
        fmt_match = re.search(r"'(\w+)'", result.stdout)
        if not fmt_match:
            logger.error(f"Cannot parse pixel format from {device_path}")
            return None

        pixel_format = fmt_match.group(1)

        # Cerca la risoluzione: riga tipo  Size: Discrete 1280x720
        res_match = re.search(r"Size:\s+\w+\s+(\d+)x(\d+)", result.stdout)
        if not res_match:
            logger.error(f"Cannot parse resolution from {device_path}")
            return None

        width = int(res_match.group(1))
        height = int(res_match.group(2))

        return (pixel_format, width, height)

    except Exception as e:
        logger.error(f"Error reading format for {device_path}: {e}")
        return None