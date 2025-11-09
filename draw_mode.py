import sys
import cv2
import numpy as np
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtGui import QPainter, QPen, QImage, QCursor
from PyQt5.QtCore import Qt, QTimer
import os
from datetime import datetime
import pytesseract

mp_hands = mp.solutions.hands
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Air Draw - Perfect Writing")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.canvas = QImage(self.size(), QImage.Format_RGBA8888)
        self.canvas.fill(Qt.transparent)

        self.cap = cv2.VideoCapture(0)
        self.hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

        # Optimized for writing - less smoothing, more precision
        self.position_buffer = []
        self.buffer_size = 4  # Smaller buffer for more responsiveness
        
        # Writing-optimized settings
        self.min_distance = 3  # Very small for precise writing
        self.smoothing_factor = 0.3  # Light smoothing to reduce jitter but maintain precision
        self.prediction_strength = 0.1  # Minimal prediction
        
        self.prev = None
        self.drawing = True
        self.last_smooth_pos = None
        self.gesture_cooldown = 0
        
        # Writing-specific settings
        self.brush_size = 4  # Thinner lines for writing
        self.stabilization_threshold = 15  # Ignore very small jitters

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(10)  # Fast updates for responsive writing

    def smooth_position(self, x, y):
        # Add current position to buffer
        self.position_buffer.append((x, y))
        if len(self.position_buffer) > self.buffer_size:
            self.position_buffer.pop(0)
        
        # Simple average for writing (no complex weighting)
        avg_x = sum(pos[0] for pos in self.position_buffer) / len(self.position_buffer)
        avg_y = sum(pos[1] for pos in self.position_buffer) / len(self.position_buffer)
        
        # Very light exponential smoothing for writing
        if self.last_smooth_pos:
            smooth_x = (self.smoothing_factor * self.last_smooth_pos[0] + 
                       (1 - self.smoothing_factor) * avg_x)
            smooth_y = (self.smoothing_factor * self.last_smooth_pos[1] + 
                       (1 - self.smoothing_factor) * avg_y)
        else:
            smooth_x, smooth_y = avg_x, avg_y
            
        self.last_smooth_pos = (smooth_x, smooth_y)
        
        return int(smooth_x), int(smooth_y)

    def distance(self, pos1, pos2):
        return ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5

    def is_stable_movement(self, new_pos, prev_pos):
        """Check if movement is intentional (not jitter)"""
        if prev_pos is None:
            return True
            
        dist = self.distance(new_pos, prev_pos)
        # If movement is very small, it's probably jitter
        return dist >= self.stabilization_threshold

    def count_extended_fingers(self, landmarks, frame_shape):
        h, w = frame_shape[:2]
        fingers = []
        
        # Thumb
        thumb_tip = landmarks.landmark[4]
        thumb_ip = landmarks.landmark[3]
        if thumb_tip.x < thumb_ip.x:
            fingers.append(1)
        else:
            fingers.append(0)
        
        # Other fingers
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
        h, w = frame_shape[:2]
        
        # Check thumb - for fist, thumb should be closed
        thumb_tip = landmarks.landmark[4]
        thumb_mcp = landmarks.landmark[2]
        thumb_closed = thumb_tip.x > thumb_mcp.x  # Thumb is not extended
        
        # Check other fingers
        finger_tips = [8, 12, 16, 20]  # index, middle, ring, pinky tips
        finger_mcps = [5, 9, 13, 17]   # MCP joints (base of fingers)
        
        fingers_closed = True
        for tip_id, mcp_id in zip(finger_tips, finger_mcps):
            tip = landmarks.landmark[tip_id]
            mcp = landmarks.landmark[mcp_id]
            if tip.y < mcp.y:  # Finger tip is above MCP (finger is extended)
                fingers_closed = False
                break
        
        return thumb_closed and fingers_closed

    def check_gestures(self, landmarks, frame_shape):
        extended_fingers = self.count_extended_fingers(landmarks, frame_shape)
        is_fist_gesture = self.is_fist(landmarks, frame_shape)
        
        self.gesture_cooldown = max(0, self.gesture_cooldown - 1)
        
        if self.gesture_cooldown > 0:
            return None
            
        gesture = None
        
        # Fist gesture for clearing
        if is_fist_gesture:
            gesture = "clear"
        # 3 fingers for save
        elif extended_fingers == 3:
            gesture = "save"
        # 4 fingers for quit
        elif extended_fingers == 4:
            gesture = "quit"
            
        if gesture:
            self.gesture_cooldown = 30
            
        return gesture

    def execute_gesture(self, gesture):
        if gesture == "clear":
            self.clear_canvas()
        elif gesture == "save":
            self.save_image()
        elif gesture == "quit":
            self.quit_application()

    def clear_canvas(self):
        self.canvas.fill(Qt.transparent)
        self.update()
        self.position_buffer.clear()
        self.last_smooth_pos = None
        print("🎨 Canvas cleared!")

    def save_image(self):
        try:
            if not os.path.exists("saves"):
                os.makedirs("saves")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"saves/drawing.png"
            # Save original drawing first
            self.canvas.save(filename, "PNG")
            # --- Convert QImage → OpenCV Mat ---
            img = cv2.imread(filename)  # BGR format
            # Convert to HSV for red stroke detection
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            lower1 = np.array([0, 120, 70])
            upper1 = np.array([10, 255, 255])
            lower2 = np.array([170, 120, 70])
            upper2 = np.array([180, 255, 255])
            mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(hsv, lower2, upper2)
            # Create black background (0) with white strokes (255)
            letter = np.zeros_like(img)  # all black background
            letter[mask > 0] = (255, 255, 255)  # white strokes
            # Convert to grayscale (white strokes on black bg)
            letter = cv2.cvtColor(letter, cv2.COLOR_BGR2GRAY)
            # Dilate white strokes to thicken them
            kernel = np.ones((7, 7), np.uint8)
            dilated = cv2.dilate(letter, kernel, iterations=5)
            # Invert image so strokes become black on white background
            final_img = cv2.bitwise_not(dilated)
            # Save the processed image
            cv2.imwrite(filename, final_img)
            print(f"✅ Saved (OCR-ready): {filename}")
            img = cv2.imread("saves/drawing.png", cv2.IMREAD_GRAYSCALE)
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(img, config=custom_config)
            print("OCR Text: " + text)
        except Exception as e:
            print(f"Error saving image: {e}")
        self.clear_canvas()

    def quit_application(self):
        reply = QMessageBox.question(self, "Quit Application", 
                                   "Are you sure you want to quit?",
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            print("👋 Application quitting...")
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

            ix, iy = int(lm[8].x * w), int(lm[8].y * h)
            tx, ty = int(lm[4].x * w), int(lm[4].y * h)

            dist = ((ix - tx)**2 + (iy - ty)**2)**0.5

            # Responsive drawing control
            if dist >= 40:  # Slightly more sensitive for writing
                self.drawing = True
            elif dist <= 30:
                self.drawing = False

            gesture = self.check_gestures(results.multi_hand_landmarks[0], frame.shape)
            if gesture:
                self.execute_gesture(gesture)

            screen_w, screen_h = self.width(), self.height()
            sx = int(ix * (screen_w / w))
            sy = int(iy * (screen_h / h))

            # Light smoothing for writing
            smooth_x, smooth_y = self.smooth_position(sx, sy)
            QCursor.setPos(smooth_x, smooth_y)

            # Writing-optimized drawing logic
            if self.drawing:
                current_pos = (smooth_x, smooth_y)
                
                if self.prev is not None:
                    # Check if movement is intentional (not jitter)
                    if self.is_stable_movement(current_pos, self.prev):
                        # Draw immediately for responsive writing
                        self.draw_line(self.prev[0], self.prev[1], smooth_x, smooth_y)
                        self.prev = current_pos
                    # else: ignore small jitter movements
                else:
                    self.prev = current_pos
            else:
                self.prev = None
                self.position_buffer.clear()  # Clear buffer when not writing
        else:
            self.prev = None
            self.position_buffer.clear()

        self.update()

    def draw_line(self, x1, y1, x2, y2):
        painter = QPainter(self.canvas)
        
        # Crisp, thin lines perfect for writing
        pen = QPen(Qt.red, self.brush_size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(x1, y1, x2, y2)
        
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.canvas)
        
        # Display instructions
        painter.setPen(QPen(Qt.darkBlue))
        painter.drawText(10, 30, "✊ Fist = Clear    🤟 3 fingers = Save    🖖 4 fingers = Quit")
        painter.drawText(10, 50, "✍️  Writing Mode - Pinch to pause, unpinch to write")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    overlay = Overlay()
    
    print("✍️  Air Write - Perfect Writing Mode")
    print("=====================================")
    print("Optimized for precise writing:")
    print("• Pinch thumb & index to pause writing")
    print("• Unpinch to write")
    print("• ✊ FIST - Clear canvas")
    print("• 🤟 3 fingers - Save writing") 
    print("• 🖖 4 fingers - Quit application")
    print("")
    print("✨ Writing features:")
    print("• Thin, crisp lines")
    print("• Minimal smoothing for precision")
    print("• Jitter reduction")
    print("• Responsive tracking")
    print("=====================================")
    
    sys.exit(app.exec_())