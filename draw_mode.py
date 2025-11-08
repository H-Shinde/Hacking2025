import sys
import cv2
import numpy as np
import mediapipe as mp
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QPainter, QPen, QImage, QCursor
from PyQt5.QtCore import Qt, QTimer

mp_hands = mp.solutions.hands

class Overlay(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Air Draw Overlay")

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.showFullScreen()

        self.canvas = QImage(self.size(), QImage.Format_RGBA8888)
        self.canvas.fill(Qt.transparent)

        self.cap = cv2.VideoCapture(0)
        self.hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)

        self.prev = None
        self.drawing = True

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(5)

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

            ix, iy = int(lm[8].x * w), int(lm[8].y * h)  # index tip
            tx, ty = int(lm[4].x * w), int(lm[4].y * h)  # thumb tip

            dist = ((ix - tx)**2 + (iy - ty)**2)**0.5

            # reversed logic: draw normally, pinch breaks
            self.drawing = dist >= 40

            # convert to screen coords
            screen_w, screen_h = self.width(), self.height()
            sx = int(ix * (screen_w / w))
            sy = int(iy * (screen_h / h))

            # ---- NEW: MOVE MOUSE ----
            QCursor.setPos(sx, sy)

            # drawing logic
            if self.drawing:
                if self.prev is not None:
                    self.draw_line(self.prev[0], self.prev[1], sx, sy)
                self.prev = (sx, sy)
            else:
                self.prev = None
        else:
            self.prev = None

        self.update()

    def draw_line(self, x1, y1, x2, y2):
        painter = QPainter(self.canvas)
        pen = QPen(Qt.red, 6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(x1, y1, x2, y2)
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.canvas)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_C:
            self.canvas.fill(Qt.transparent)
            self.update()
        if event.key() == Qt.Key_Q:
            QApplication.quit()

app = QApplication(sys.argv)
overlay = Overlay()
sys.exit(app.exec_())
