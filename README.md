Hand Gesture Control System

A full-featured hand-tracking interaction system built with MediaPipe, OpenCV, PyQt5, and pyautogui.
Control your computer using hand gestures, air-drawing, virtual mouse control, and even handwriting OCR powered by Microsoft TrOCR.

🚀 Features
🖌️ Drawing Mode (draw_mode.py)

Draw in the air and write digitally using your hand.

✏️ Pinch (index + thumb apart) → Draw

✊ Fist → Clear canvas

🤟 3 fingers → Save + OCR handwriting → Auto-type recognized text

🤘 Rock sign → Toggle UI panel

🖖 4 fingers → Return to Menu

Smooth stroke tracking

Uses TrOCR handwritten model for handwriting recognition

Automatically types recognized text on the keyboard

🖱️ Mouse Mode (mouse_mode.py)

Hands-free mouse control with precision smoothing.

☝️ Index finger → Move cursor

🤏 Quick pinch → Left click

🤏 Hold pinch (>0.3s) → Drag

🤏🤏 Double pinch → Double click

🤟 3 fingers → Right click

🤘 Rock sign → Toggle menu

🖖 4 fingers → Exit to menu

👐 Gesture Mode (emote_mode.py)

Control common Windows shortcuts using gesture recognition.

✊ Fist → Copy (Ctrl+C)

🖐️ 5 fingers → Paste (Ctrl+V)

🤟 3 fingers → Save (Ctrl+S)

👍 Thumbs up → Enter

✌️ Peace sign → Space

🤙 Pinky only → Undo (Ctrl+Z)

🤘 Rock sign → Toggle menu

👏 Clap → Trigger shutdown

🖖 4 fingers → Return to Main Menu

📋 Main Menu (menu.py)

Gesture-based mode launcher.

☝️ 1 finger → Drawing Mode

🤟 3 fingers → Mouse Mode

🖐️ 5 fingers → Gesture Mode

🖖 4 fingers → Quit Application

Launches each mode as a separate subprocess

📂 Project Structure
/
├── menu.py            # Main gesture-based menu
├── draw_mode.py       # Drawing + OCR mode
├── mouse_mode.py      # Gesture-based mouse controller
├── emote_mode.py      # Windows shortcut gesture mode
├── gesture.py         # Older combined demo (optional)
└── saves/             # Auto-created folder for drawings

🛠️ Installation
Python Version

Recommended:

Python 3.8 – 3.11

Install Dependencies
pip install opencv-python mediapipe pyqt5 pyautogui numpy pillow transformers


⚠️ Note:

TrOCR model downloads automatically (~500MB).

pyautogui may require admin permission for drag/click automation.

▶️ Running the Application

Start from the main gesture-based menu:

python menu.py


Then select modes using hand gestures.

🧠 How It Works

MediaPipe Hands detects 21 hand landmarks in real time.

Custom gesture classifiers determine finger counts, thumb direction, and special gestures.

Drawing mode renders strokes onto a PyQt transparent canvas.

OCR processed via microsoft/trocr-base-handwritten → auto-typed with pyautogui.

Mouse mode maps finger coordinates → screen coordinates with smoothing.

⚠️ Safety Notes

Keep your hand fully in the webcam frame.

Disable Windows Sticky Keys for uninterrupted use.

OCR works best with large, clean handwriting.

Shutdown gesture (👏 clap) is real — use responsibly.

📌 Future Improvements (Optional Ideas)

UI sensitivity calibration

Adjustable thresholds for gestures

Support for multiple hand interactions

On-screen gesture debugging visualization
