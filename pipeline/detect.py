import os
import structlog

logger = structlog.get_logger("detector")

try:
    from ultralytics import YOLO
    HAS_ULTRALYTICS = True
except ImportError:
    logger.warning("ultralytics_yolo_not_installed_falling_back_to_simulation")
    HAS_ULTRALYTICS = False

class PersonDetector:
    def __init__(self, model_path=None):
        if not HAS_ULTRALYTICS:
            logger.info("person_detector_initialized_in_simulation_mode")
            return

        if model_path is None:
            model_path = os.getenv("YOLO_MODEL_PATH", "yolov8x.pt")
            
        dir_name = os.path.dirname(model_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        logger.info("loading_yolo_model", model_path=model_path)
        self.model = YOLO(model_path)
        
    def detect(self, frame, conf_threshold=0.45):
        """
        Runs YOLOv8 person detection on a single frame.
        Returns a list of detections: [ [xmin, ymin, xmax, ymax, conf] ]
        """
        if not HAS_ULTRALYTICS:
            return []

        results = self.model(frame, classes=[0], conf=conf_threshold, verbose=False)
        
        detections = []
        if len(results) > 0:
            result = results[0]
            boxes = result.boxes
            for box in boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                detections.append([
                    float(xyxy[0]), # xmin
                    float(xyxy[1]), # ymin
                    float(xyxy[2]), # xmax
                    float(xyxy[3]), # ymax
                    conf
                ])
                
        return detections
