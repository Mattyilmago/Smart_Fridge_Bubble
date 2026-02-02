#!/usr/bin/env python3
"""
Test script per verificare la lettura del sensore BMP280
"""

import board
import adafruit_bmp280
import time

print("Inizializzazione sensore BMP280...")
i2c = board.I2C()
sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c, address=0x76)

print("Sensore inizializzato correttamente!")
print("\nLettura temperature ogni secondo (premi Ctrl+C per terminare):\n")

try:
    while True:
        temperature = sensor.temperature
        pressure = sensor.pressure
        
        print(f"Temperatura: {temperature:.2f}°C | Pressione: {pressure:.2f} hPa")
        time.sleep(1)
except KeyboardInterrupt:
    print("\n\nTest terminato.")
