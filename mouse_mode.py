# mouse_mode.py - Mouse control mode
import sys
import cv2
import numpy as np
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QPen, QCursor, QColor, QFont
from PyQt5.QtCore import Qt, QTimer
import pyautogui
import time

mp_hands = mp.solutions.hands

class MouseMode(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mouse Mode")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.cap = cv2.VideoCapture(0)
        self.hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

        self.gesture_cooldown = 0
        self.smoothing_factor = 0.7
        self.last_smooth_pos = None
        self.last_click_time = 0
        self.click_cooldown = 0.3
        self.menu_visible = True  # Track menu visibility
        
        # Improved click/drag states
        self.is_dragging = False
        self.left_click_held = False
        self.was_pinched = False
        self.pinch_start_time = 0
        self.pinch_hold_threshold = 0.3  # Seconds to hold for drag vs click
        
        # For detecting quick releases
        self.last_release_time = 0
        self.double_click_threshold = 0.5  # Time for double click detection

        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(5)

        print("\n🖱️  MOUSE MODE ACTIVE")
        print("="*60)
        print("• Index finger = Move cursor")
        print("• Quick pinch = Left click")
        print("• Hold pinch (>0.3s) = Drag/Select")
        print("• Double pinch = Double click")
        print("• 🤟 3 fingers = Right click")
        print("• 🤘 Rock sign = Toggle menu")
        print("• 🖖 4 fingers = Return to Menu")
        print("="*60 + "\n")

    def smooth_position(self, x, y):
        if self.last_smooth_pos is None:
            self.last_smooth_pos = (x, y)
            return x, y
        
        smooth_x = self.smoothing_factor * x + (1 - self.smoothing_factor) * self.last_smooth_pos[0]
        smooth_y = self.smoothing_factor * y + (1 - self.smoothing_factor) * self.last_smooth_pos[1]
        
        self.last_smooth_pos = (smooth_x, smooth_y)
        return int(smooth_x), int(smooth_y)

    def count_extended_fingers(self, landmarks, frame_shape):
        fingers = []
        
        thumb_tip = landmarks.landmark[4]
        thumb_ip = landmarks.landmark[3]
        if thumb_tip.x < thumb_ip.x:
            fingers.append(1)
        else:
            fingers.append(0)
        
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        
        for tip_id, pip_id in zip(finger_tips, finger_pips):
            tip = landmarks.landmark[tip_id]
            pip = landmarks.landmark[pip_id]
            if tip.y < pip.y:
                fingers.append(1)
            else:
                fingers.append(0)
        
        return sum(fingers)

    def is_fist(self, landmarks, frame_shape):
        """Check if hand is making a fist (all fingers closed)"""
        fingers = []
        
        # Thumb - check if thumb is across palm
        thumb_tip = landmarks.landmark[4]
        thumb_mcp = landmarks.landmark[2]
        if thumb_tip.x > thumb_mcp.x:  # Thumb across palm
            fingers.append(0)
        else:
            fingers.append(1)
        
        # Other fingers - check if tips are below PIP joints
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        
        for tip_id, pip_id in zip(finger_tips, finger_pips):
            tip = landmarks.landmark[tip_id]
            pip = landmarks.landmark[pip_id]
            if tip.y > pip.y:  # Finger tip below PIP joint (closed)
                fingers.append(0)
            else:
                fingers.append(1)
        
        # Fist if no fingers are extended
        return sum(fingers) == 0

    def is_rock_sign(self, landmarks, frame_shape):
        """Check for rock sign 🤘 (index + pinky extended)"""
        fingers = []
        
        # Check thumb
        thumb_tip = landmarks.landmark[4]
        thumb_ip = landmarks.landmark[3]
        fingers.append(1 if thumb_tip.x < thumb_ip.x else 0)
        
        # Check other fingers
        finger_tips = [8, 12, 16, 20]
        finger_pips = [6, 10, 14, 18]
        
        for tip_id, pip_id in zip(finger_tips, finger_pips):
            tip = landmarks.landmark[tip_id]
            pip = landmarks.landmark[pip_id]
            fingers.append(1 if tip.y < pip.y else 0)
        
        # Index and pinky extended, middle and ring closed
        # [thumb, index, middle, ring, pinky]
        return fingers[1] == 1 and fingers[2] == 0 and fingers[3] == 0 and fingers[4] == 1

    def toggle_menu_visibility(self):
        """Toggle the info panel visibility"""
        self.menu_visible = not self.menu_visible
        self.update()  # Redraw to show/hide panel
        status = "visible" if self.menu_visible else "hidden"
        print(f"📋 Menu {status}")

    def quit_mode(self):
        print("👋 Returning to menu...")
        self.cleanup()
        QApplication.quit()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if results.multi_hand_landmarks:
            h, w, _ = frame.shape
            lm = results.multi_hand_landmarks[0].landmark
            current_time = time.time()

            # Check for gestures
            extended_fingers = self.count_extended_fingers(results.multi_hand_landmarks[0], frame.shape)
            self.gesture_cooldown = max(0, self.gesture_cooldown - 1)
            
            # Check for quit gesture (4 fingers)
            if extended_fingers == 4 and self.gesture_cooldown == 0:
                self.gesture_cooldown = 30
                self.quit_mode()
                return

            # Check for right click gesture (3 fingers)
            if extended_fingers == 3 and self.gesture_cooldown == 0:
                if (current_time - self.last_click_time) > self.click_cooldown:
                    pyautogui.rightClick()
                    self.last_click_time = current_time
                    self.gesture_cooldown = 30
                    print("🖱️ Right Click!")
                return

            # Check for rock sign (toggle menu)
            if self.is_rock_sign(results.multi_hand_landmarks[0], frame.shape) and self.gesture_cooldown == 0:
                self.toggle_menu_visibility()
                self.gesture_cooldown = 30
                return

            # Index finger position
            ix, iy = int(lm[8].x * w), int(lm[8].y * h)
            tx, ty = int(lm[4].x * w), int(lm[4].y * h)

            # Map to screen
            screen_w, screen_h = pyautogui.size()
            sx = int(ix * (screen_w / w))
            sy = int(iy * (screen_h / h))

            smooth_x, smooth_y = self.smooth_position(sx, sy)
            pyautogui.moveTo(smooth_x, smooth_y, duration=0)

            # Calculate pinch distance
            dist = ((ix - tx)**2 + (iy - ty)**2)**0.5
            is_pinched = dist < 40
            
            # Handle left click gestures
            if is_pinched:
                if not self.was_pinched:
                    # Just started pinching - record start time
                    self.pinch_start_time = current_time
                    self.was_pinched = True
                
                # Check if this is a long press (drag) or should remain as potential click
                pinch_duration = current_time - self.pinch_start_time
                
                if pinch_duration > self.pinch_hold_threshold and not self.is_dragging:
                    # Start dragging after hold threshold
                    pyautogui.mouseDown()
                    self.left_click_held = True
                    self.is_dragging = True
                    print("🖱️ Drag started")
            
            # Handle release
            else:  # not pinched
                if self.was_pinched:
                    pinch_duration = current_time - self.pinch_start_time
                    
                    if self.is_dragging:
                        # Was dragging - release mouse
                        pyautogui.mouseUp()
                        self.left_click_held = False
                        self.is_dragging = False
                        print("🖱️ Drag ended")
                    
                    elif not self.left_click_held and pinch_duration < self.pinch_hold_threshold:
                        # This was a quick pinch - handle as click
                        if (current_time - self.last_release_time) < self.double_click_threshold:
                            # Double click detected
                            pyautogui.doubleClick()
                            print("🖱️ Double Click!")
                        else:
                            # Single click
                            pyautogui.click()
                            print("🖱️ Left Click!")
                        
                        self.last_click_time = current_time
                        self.last_release_time = current_time
                    
                    self.was_pinched = False
                    self.left_click_held = False

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Only draw menu if visible
        if not self.menu_visible:
            return
        
        # Draw compact info panel with white opaque background
        panel_width = 600
        panel_height = 120
        margin = 20
        
        # Semi-transparent white background
        painter.setBrush(QColor(255, 255, 255, 230))  # White with opacity
        painter.setPen(QPen(QColor(0, 0, 0, 150), 2))
        painter.drawRoundedRect(margin, margin, panel_width, panel_height, 10, 10)
        
        # Title and status
        font = QFont('Arial', 12, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(Qt.black))
        
        status = "Ready"
        if self.is_dragging:
            status = "🔵 DRAGGING"
        elif self.was_pinched and not self.is_dragging:
            status = "⚪ READY TO CLICK"
            
        title = f"🖱️ MOUSE MODE - Status: {status}"
        painter.drawText(margin + 10, margin + 25, title)
        
        # Instructions
        small_font = QFont('Arial', 11)
        painter.setFont(small_font)
        
        y_pos = margin + 50
        instructions = [
            "Pinch = Click/Drag  |  🤟 3 fingers = Right Click",
            "🤘 Rock sign = Toggle menu  |  🖖 4 fingers = Menu"
        ]
        
        for instruction in instructions:
            painter.drawText(margin + 10, y_pos, instruction)
            y_pos += 30

    def cleanup(self):
        # Release mouse button if held down
        if self.left_click_held:
            pyautogui.mouseUp()
        if self.cap:
            self.cap.release()
        if self.hands:
            self.hands.close()

    def closeEvent(self, event):
        self.cleanup()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mode = MouseMode()
    sys.exit(app.exec_())