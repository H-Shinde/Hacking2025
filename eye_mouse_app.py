import sys
import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import keyboard  # <--- used for Q toggle
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt6.QtCore import QThread, pyqtSignal

SMOOTHING_ALPHA = 0.2

class EyeTrackerThread(QThread):
    status = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.tracking = False
        self.calibrated = False
        self.T = None
        self.prev_smoothed = None

        self.screen_w, self.screen_h = pyautogui.size()
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.cap = None

    def iris_center(self, landmarks):
        LEFT_IRIS = [474, 475, 476, 477]
        RIGHT_IRIS = [469, 470, 471, 472]
        pts = []
        for group in (LEFT_IRIS, RIGHT_IRIS):
            xs = [landmarks[i].x for i in group]
            ys = [landmarks[i].y for i in group]
            pts.append((np.mean(xs), np.mean(ys)))
        return np.array([(pts[0][0] + pts[1][0]) / 2, (pts[0][1] + pts[1][1]) / 2])

    def map_to_screen(self, norm_xy):
        v = np.array([norm_xy[0], norm_xy[1], 1.0])
        scr = v @ self.T
        scr[0] = np.clip(scr[0], 0, self.screen_w-1)
        scr[1] = np.clip(scr[1], 0, self.screen_h-1)
        return scr.astype(int)

    def calibrate(self):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.status.emit("Error: Start camera first.")
                return

        self.status.emit("Calibration: Look, then press SPACE on each point.")
        CAP_POINTS = [
            ("top-left",   (0.1, 0.1)),
            ("top-right",  (0.9, 0.1)),
            ("bottom-left",(0.1, 0.9)),
            ("bottom-right",(0.9, 0.9)),
            ("center",     (0.5, 0.5)),
        ]
        cam_pts, scr_pts = [], []

        for name, (nx, ny) in CAP_POINTS:
            self.status.emit(f"Look at: {name}, press SPACE")
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    continue
                h, w = frame.shape[:2]
                cv2.circle(frame, (int(nx*w), int(ny*h)), 20, (0,255,0), 2)
                cv2.imshow("Calibration", frame)
                k = cv2.waitKey(1) & 0xFF
                if k == ord(' '):
                    res = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    if res.multi_face_landmarks:
                        ic = self.iris_center(res.multi_face_landmarks[0].landmark)
                        cam_pts.append(ic)
                        scr_pts.append(np.array([nx*self.screen_w, ny*self.screen_h]))
                        break
                elif k == ord('q'):
                    cv2.destroyWindow("Calibration")
                    return
        cv2.destroyWindow("Calibration")

        src = np.array(cam_pts)
        dst = np.array(scr_pts)
        A = np.hstack([src, np.ones((src.shape[0],1))])
        self.T, _, _, _ = np.linalg.lstsq(A, dst, rcond=None)
        self.calibrated = True
        self.status.emit("Calibration complete.")

    def run(self):
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if self.cap.isOpened():
            self.status.emit("Camera on.")
        else:
            self.status.emit("Camera failed.")
            return

        while self.running:
            # Q toggles tracking OFF (does NOT exit app)
            if keyboard.is_pressed('q'):
                self.tracking = False
                self.status.emit("Tracking OFF (Q pressed)")

            ret, frame = self.cap.read()
            if not ret:
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.face_mesh.process(rgb)

            if results.multi_face_landmarks and self.calibrated and self.tracking:
                ic = self.iris_center(results.multi_face_landmarks[0].landmark)
                screen_xy = self.map_to_screen(ic)

                if self.prev_smoothed is None:
                    self.prev_smoothed = screen_xy.astype(float)
                else:
                    self.prev_smoothed = SMOOTHING_ALPHA * screen_xy + (1-SMOOTHING_ALPHA)*self.prev_smoothed

                pyautogui.moveTo(int(self.prev_smoothed[0]), int(self.prev_smoothed[1]), duration=0)

        if self.cap.isOpened():
            self.cap.release()

        self.status.emit("Camera stopped.")

    def stop_thread(self):
        self.running = False


class App(QWidget):
    def __init__(self):
        super().__init__()
        self.tracker = EyeTrackerThread()
        self.tracker.start()

        self.label = QLabel("Status: Idle")
        btn_calib = QPushButton("Calibrate")
        btn_track = QPushButton("Start Tracking")

        btn_calib.clicked.connect(self.tracker.calibrate)
        btn_track.clicked.connect(self.toggle_tracking)

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(btn_calib)
        layout.addWidget(btn_track)
        self.setLayout(layout)

        self.tracker.status.connect(lambda msg: self.label.setText("Status: " + msg))

        self.setWindowTitle("Eye Control Minimal UI")
        self.setFixedSize(300, 150)

    def toggle_tracking(self):
        self.tracker.tracking = not self.tracker.tracking
        self.label.setText("Status: Tracking ON" if self.tracker.tracking else "Status: Tracking OFF")

    def closeEvent(self, event):
        self.tracker.stop_thread()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui = App()
    ui.show()
    sys.exit(app.exec())
