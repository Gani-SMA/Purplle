import json
import os

class ZoneClassifier:
    def __init__(self, layout_path=None):
        if layout_path is None:
            layout_path = os.path.join(os.path.dirname(__file__), "store_layout.json")
        
        with open(layout_path, "r") as f:
            self.layout = json.load(f)

    def is_point_in_polygon(self, x, y, polygon):
        """Ray casting algorithm to check if point (x,y) is inside a polygon."""
        num_vertices = len(polygon)
        inside = False
        p1x, p1y = polygon[0]
        for i in range(1, num_vertices + 1):
            p2x, p2y = polygon[i % num_vertices]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        return inside

    def classify_zone(self, store_id, camera_id, norm_bbox):
        """
        Classifies which zone a bounding box belongs to.
        norm_bbox: [xmin, ymin, xmax, ymax] normalized [0, 1]
        """
        xmin, ymin, xmax, ymax = norm_bbox
        # Centroid of the bounding box
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0

        store = self.layout.get(store_id, {})
        camera = store.get(camera_id, {})

        for zone_id, polygon in camera.items():
            if self.is_point_in_polygon(cx, cy, polygon):
                return zone_id
        
        return None
