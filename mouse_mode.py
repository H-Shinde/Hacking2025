import sys
import cv2
import numpy as np
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QWidget, QMessageBox
from PyQt5.QtGui import QPainter, QPen, QImage, QCursor, QColor
from PyQt5.QtCore import Qt, QTimer
import pyautogui
import math

mp_hands = mp.solutions.hands

class MouseMode(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Air Mouse - Hand Controlled")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.cap = cv2.VideoCapture(0)
        self.hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)

        # Mouse control settings
        self.position_buffer = []
        self.buffer_size = 3
        self.smoothing_factor = 0.5
        
        # Mouse states
        self.left_click_down = False
        self.right_click_down = False
        self.is_dragging = False
        self.is_scrolling = False
        self.neutral_mode = True  # Start in neutral (just moving) mode
        
        # Gesture tracking
        self.gesture_cooldown = 0
        self.last_gesture = None
        
        # Scroll settings
        self.scroll_start_y = 0
        self.scroll_threshold = 50
        
        # Visual feedback
        self.click_animation = 0
        self.cursor_color = QColor(0, 255, 0)  # Green cursor
        self.show_instructions = True
        self.instruction_timer = 200  # Show instructions for 2 seconds

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(10)  # 100 FPS for responsive mouse control

    def smooth_position(self, x, y):
        self.position_buffer.append((x, y))
        if len(self.position_buffer) > self.buffer_size:
            self.position_buffer.pop(0)
        
        avg_x = sum(pos[0] for pos in self.position_buffer) / len(self.position_buffer)
        avg_y = sum(pos[1] for pos in self.position_buffer) / len(self.position_buffer)
        
        return int(avg_x), int(avg_y)

    def distance(self, pos1, pos2):
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)

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

    def get_thumb_index_distance(self, landmarks, frame_shape):
        """Get distance between thumb and index finger"""
        h, w = frame_shape[:2]
        thumb_tip = landmarks.landmark[4]
        index_tip = landmarks.landmark[8]
        
        thumb_x, thumb_y = int(thumb_tip.x * w), int(thumb_tip.y * h)
        index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)
        
        return self.distance((thumb_x, thumb_y), (index_x, index_y))

    def get_palm_orientation(self, landmarks, frame_shape):
        """Check if palm is facing up/down for scroll detection"""
        h, w = frame_shape[:2]
        
        # Use wrist and middle finger MCP to determine orientation
        wrist = landmarks.landmark[0]
        middle_mcp = landmarks.landmark[9]
        
        # If middle MCP is above wrist, palm is facing up (scrolling)
        return middle_mcp.y < wrist.y

    def check_gestures(self, landmarks, frame_shape):
        extended_fingers = self.count_extended_fingers(landmarks, frame_shape)
        thumb_index_dist = self.get_thumb_index_distance(landmarks, frame_shape)
        palm_up = self.get_palm_orientation(landmarks, frame_shape)
        
        self.gesture_cooldown = max(0, self.gesture_cooldown - 1)
        
        if self.gesture_cooldown > 0:
            return self.last_gesture
            
        gesture = None
        
        # NEUTRAL MODE - Just pointing (index extended, others relaxed)
        if extended_fingers == 1 and thumb_index_dist > 40:
            gesture = "neutral"
        
        # Left Click - Index and thumb pinched
        elif extended_fingers == 1 and thumb_index_dist < 30:
            gesture = "left_click"
        
        # Right Click - Two fingers pinched (peace sign with thumb)
        elif extended_fingers == 2 and thumb_index_dist < 30:
            gesture = "right_click"
            
        # Drag - Closed hand (fist)
        elif extended_fingers == 0:
            gesture = "drag"
            
        # Scroll - Open palm facing up
        elif extended_fingers == 5 and palm_up:
            gesture = "scroll"
            
        # Double Click - Three fingers extended
        elif extended_fingers == 3:
            gesture = "double_click"
        
        if gesture and gesture != self.last_gesture:
            self.last_gesture = gesture
            self.gesture_cooldown = 15
            
        return gesture

    def execute_gesture(self, gesture, current_pos):
        if gesture == "neutral":
            # Just move cursor, no action
            self.neutral_mode = True
            # Release any active actions
            if self.left_click_down:
                pyautogui.mouseUp(button='left')
                self.left_click_down = False
                self.is_dragging = False
            if self.right_click_down:
                pyautogui.mouseUp(button='right')
                self.right_click_down = False
            if self.is_scrolling:
                self.is_scrolling = False
            print("🟢 Neutral Mode - Just moving cursor")
            
        elif gesture == "left_click":
            if not self.left_click_down:
                print("🖱️ Left Click")
                pyautogui.mouseDown(button='left')
                self.left_click_down = True
                self.neutral_mode = False
                self.click_animation = 10
                
        elif gesture == "right_click":
            if not self.right_click_down:
                print("🖱️ Right Click")
                pyautogui.mouseDown(button='right')
                self.right_click_down = True
                self.neutral_mode = False
                self.click_animation = 10
                
        elif gesture == "drag":
            if not self.is_dragging and self.left_click_down:
                print("📦 Started Dragging")
                self.is_dragging = True
                self.neutral_mode = False
                
        elif gesture == "scroll":
            if not self.is_scrolling:
                print("🔄 Scroll Mode Activated")
                self.is_scrolling = True
                self.neutral_mode = False
                self.scroll_start_y = current_pos[1]
                
        elif gesture == "double_click":
            print("🖱️ Double Click")
            pyautogui.doubleClick()
            self.neutral_mode = True
            self.click_animation = 15

    def release_gesture(self, gesture):
        if gesture == "left_click" and self.left_click_down:
            pyautogui.mouseUp(button='left')
            self.left_click_down = False
            self.is_dragging = False
            self.neutral_mode = True
            print("🖱️ Left Click Released")
            
        elif gesture == "right_click" and self.right_click_down:
            pyautogui.mouseUp(button='right')
            self.right_click_down = False
            self.neutral_mode = True
            print("🖱️ Right Click Released")
            
        elif gesture == "scroll" and self.is_scrolling:
            self.is_scrolling = False
            self.neutral_mode = True
            print("🔄 Scroll Mode Deactivated")
            
        elif gesture == "drag" and self.is_dragging:
            self.is_dragging = False
            self.neutral_mode = True
            print("📦 Drag Released")

    def handle_scroll(self, current_y):
        if not self.is_scrolling:
            return
            
        scroll_delta = current_y - self.scroll_start_y
        scroll_amount = -int(scroll_delta / 10)  # Invert for natural scrolling
        
        if abs(scroll_amount) > 0:
            pyautogui.scroll(scroll_amount)
            self.scroll_start_y = current_y

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

            # Get index finger tip for cursor
            ix, iy = int(lm[8].x * w), int(lm[8].y * h)

            # Convert to screen coordinates
            screen_w, screen_h = self.width(), self.height()
            sx = int(ix * (screen_w / w))
            sy = int(iy * (screen_h / h))

            # Smooth cursor movement
            smooth_x, smooth_y = self.smooth_position(sx, sy)
            
            # Move actual mouse cursor
            QCursor.setPos(smooth_x, smooth_y)
            current_pos = (smooth_x, smooth_y)

            # Check for gestures
            gesture = self.check_gestures(results.multi_hand_landmarks[0], frame.shape)
            
            if gesture:
                self.execute_gesture(gesture, current_pos)
            elif self.last_gesture and self.last_gesture != "neutral":
                # Release any active gestures when returning to neutral
                self.release_gesture(self.last_gesture)
                self.last_gesture = None

            # Handle scrolling
            self.handle_scroll(smooth_y)

        else:
            # No hand detected - release all actions and return to neutral
            if self.left_click_down:
                pyautogui.mouseUp(button='left')
                self.left_click_down = False
            if self.right_click_down:
                pyautogui.mouseUp(button='right')
                self.right_click_down = False
            if self.is_dragging:
                self.is_dragging = False
            if self.is_scrolling:
                self.is_scrolling = False
            self.neutral_mode = True
            self.last_gesture = None

        # Update animation
        self.click_animation = max(0, self.click_animation - 1)
        
        # Update instruction timer
        self.instruction_timer = max(0, self.instruction_timer - 1)
        if self.instruction_timer == 0:
            self.show_instructions = False

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw cursor
        cursor_pos = QCursor.pos()
        cursor_size = 20
        
        # Set cursor color based on mode
        if self.neutral_mode:
            self.cursor_color = QColor(0, 255, 0)  # Green - Neutral
        elif self.left_click_down:
            self.cursor_color = QColor(255, 255, 0)  # Yellow - Left Click
        elif self.right_click_down:
            self.cursor_color = QColor(255, 0, 0)    # Red - Right Click
        elif self.is_dragging:
            self.cursor_color = QColor(255, 165, 0)  # Orange - Dragging
        elif self.is_scrolling:
            self.cursor_color = QColor(0, 191, 255)  # Blue - Scrolling
        
        # Animate cursor on click
        if self.click_animation > 0:
            cursor_size += self.click_animation
        
        # Draw cursor circle
        painter.setBrush(self.cursor_color)
        painter.setPen(QPen(Qt.black, 2))
        painter.drawEllipse(cursor_pos.x() - cursor_size//2, 
                          cursor_pos.y() - cursor_size//2, 
                          cursor_size, cursor_size)
        
        # Draw crosshair for precision (only in neutral mode)
        if self.neutral_mode:
            painter.setPen(QPen(Qt.black, 1))
            painter.drawLine(cursor_pos.x() - 10, cursor_pos.y(), cursor_pos.x() + 10, cursor_pos.y())
            painter.drawLine(cursor_pos.x(), cursor_pos.y() - 10, cursor_pos.x(), cursor_pos.y() + 10)
        
        # Status text
        status_text = f"Mouse Mode - {self.get_status_text()}"
        painter.setPen(QPen(Qt.white))
        painter.drawText(10, 30, status_text)
        
        # Instructions
        if self.show_instructions:
            painter.drawText(10, 55, "👆 Point = Move Cursor (Neutral)")
            painter.drawText(10, 75, "👆+👍 Pinch = Left Click")
            painter.drawText(10, 95, "✌️+👍 Pinch = Right Click")
            painter.drawText(10, 115, "✊ Fist = Drag")
            painter.drawText(10, 135, "🖐️ Palm up = Scroll")
            painter.drawText(10, 155, "🤟 3 fingers = Double Click")

    def get_status_text(self):
        if self.neutral_mode:
            return "NEUTRAL (Moving)"
        elif self.left_click_down and self.is_dragging:
            return "DRAGGING"
        elif self.left_click_down:
            return "LEFT CLICK"
        elif self.right_click_down:
            return "RIGHT CLICK"
        elif self.is_scrolling:
            return "SCROLLING"
        else:
            return "READY"

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mouse_mode = MouseMode()
    
    print("🖱️  Air Mouse Mode Activated!")
    print("===============================")
    print("Mouse Controls:")
    print("👆  Point finger  - Move cursor (NEUTRAL MODE)")
    print("👆+👍 Pinch       - Left Click") 
    print("✌️+👍 Pinch       - Right Click")
    print("✊ Fist           - Drag (while left clicking)")
    print("🖐️ Palm up        - Scroll vertically")
    print("🤟 3 fingers      - Double Click")
    print("🖖 4 fingers      - Return to Menu")
    print("")
    print("✨ Visual Feedback:")
    print("• Green  - Neutral (just moving)")
    print("• Yellow - Left clicking")
    print("• Red    - Right clicking") 
    print("• Orange - Dragging")
    print("• Blue   - Scrolling")
    print("===============================")
    
    sys.exit(app.exec_())