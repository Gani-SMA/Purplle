import cv2
import numpy as np

class StaffClassifier:
    def __init__(self, staff_colors=None):
        """
        staff_colors: list of dicts with 'lower' and 'upper' HSV ranges.
        Default is Purplle brand purple/violet.
        OpenCV HSV ranges: Hue [0, 179], Saturation [0, 255], Value [0, 255].
        """
        if staff_colors is None:
            # Purplle brand color range in HSV:
            # Hue around 125 to 160 (OpenCV scale: 250-320 degrees)
            self.staff_colors = [
                {
                    "lower": np.array([120, 40, 40]),
                    "upper": np.array([165, 255, 255])
                }
            ]
        else:
            self.staff_colors = staff_colors

    def is_staff_member(self, frame, bbox, threshold_pct=8.0):
        """
        Checks if the bounding box corresponds to staff based on upper body uniform color.
        bbox: [xmin, ymin, xmax, ymax] absolute pixel coords
        """
        if frame is None:
            # Fallback or mock behaviour
            return False

        h, w, _ = frame.shape
        xmin, ymin, xmax, ymax = map(int, bbox)
        
        # Clamp to frame dimensions
        xmin, ymin = max(0, xmin), max(0, ymin)
        xmax, ymax = min(w, xmax), min(h, ymax)

        if xmin >= xmax or ymin >= ymax:
            return False

        # Upper body region: top 1/3 of the bounding box
        box_h = ymax - ymin
        upper_ymin = ymin
        upper_ymax = ymin + int(box_h * 0.35)

        if upper_ymin >= upper_ymax:
            return False

        crop = frame[upper_ymin:upper_ymax, xmin:xmax]
        if crop.size == 0:
            return False

        # Convert to HSV
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

        # Create mask for all defined staff colors
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for color_range in self.staff_colors:
            lower = color_range["lower"]
            upper = color_range["upper"]
            mask |= cv2.inRange(hsv, lower, upper)

        # Calculate percentage of matching pixels
        matching_pixels = np.sum(mask > 0)
        total_pixels = mask.size
        pct = (matching_pixels / total_pixels) * 100.0

        return pct >= threshold_pct
