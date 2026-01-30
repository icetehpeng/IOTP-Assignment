import cv2
import av
from datetime import datetime

class VideoProcessor:
    def __init__(self):
        self.previous_frame = None
        self.motion_detected = False
        self.motion_count = 0
        self.last_motion_time = None
        
    def recv(self, frame):
        """Process video frame"""
        img = frame.to_ndarray(format="bgr24")
        
        # Motion detection
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        
        if self.previous_frame is None:
            self.previous_frame = gray
        else:
            frame_diff = cv2.absdiff(self.previous_frame, gray)
            thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            
            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            self.motion_detected = False
            for contour in contours:
                if cv2.contourArea(contour) < 1000:
                    continue
                    
                self.motion_detected = True
                self.motion_count += 1
                self.last_motion_time = datetime.now()
                
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cv2.putText(img, "MOTION", (x, y-10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            self.previous_frame = gray
        
        # Add overlays
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(img, f"LIVE: {timestamp}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(img, f"Motions: {self.motion_count}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")
