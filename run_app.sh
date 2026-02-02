#!/bin/bash
cd /home/pub/Desktop/Smart_Fridge_Bubble
source venv/bin/activate
export DISPLAY=:0
export PYTHONUNBUFFERED=1
python app.py
