# Hacking2025

Use hand gestures and movement (mainly one hand) to fully control your mouse, keyboard, and on-screen drawing tools.

Run `menu.py` to start the project.

---

## How It Works
The main menu uses finger count detection to launch different modes:

- **1 finger** → Drawing Mode  
- **3 fingers** → Mouse Mode  
- **5 fingers** → Gesture Mode  
- **4 fingers** → Quit application  

All modes run fullscreen and use MediaPipe hand tracking.

---

## Modes

### Drawing Mode (`draw_mode.py`)
Draw in the air using your index finger.  
Includes built-in handwriting OCR (TrOCR) that types recognized text.

**Gestures:**
- Pinch (index + thumb apart) → Draw  
- Fist → Clear canvas  
- 3 fingers → Save drawing + OCR + auto-type  
- Rock sign → Toggle on-screen panel  
- 4 fingers → Return to menu  

---

### Mouse Mode (`mouse_mode.py`)
Use your hand as a mouse.

**Gestures:**
- Index finger → Move cursor  
- Quick pinch → Left click  
- Hold pinch (>0.3s) → Drag  
- Double pinch → Double click  
- 3 fingers → Right click  
- Rock sign → Toggle menu  
- 4 fingers → Return to menu  

---

### Gesture Mode (`emote_mode.py`)
Trigger keyboard shortcuts with specific gestures.

**Gestures:**
- Fist → Copy (Ctrl+C)  
- 5 fingers → Paste (Ctrl+V)  
- 3 fingers → Save (Ctrl+S)  
- Thumbs up → Enter  
- Peace sign → Space  
- Pinky only → Undo (Ctrl+Z)  
- Rock sign → Toggle menu  
- Clap → Shutdown  
- 4 fingers → Return to menu  

---

## Installation

Install requirements:

