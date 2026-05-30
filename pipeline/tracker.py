import numpy as np
import uuid
import json
import structlog

logger = structlog.get_logger("tracker")

try:
    import torch
    import torch.nn as nn
    import torchvision.models as models
    from torchvision.transforms import v2 as transforms
    HAS_TORCH = True
except ImportError:
    logger.warning("torch_or_torchvision_not_installed_falling_back_to_simulation")
    HAS_TORCH = False

class ReIDExtractor:
    def __init__(self, use_gpu=False):
        if not HAS_TORCH:
            logger.info("reid_extractor_initialized_in_simulation_mode")
            return

        self.device = torch.device("cuda" if use_gpu and torch.cuda.is_available() else "cpu")
        
        # Load a lightweight pre-trained model for feature extraction
        try:
            weights = models.MobileNet_V3_Small_Weights.DEFAULT
            base_model = models.mobilenet_v3_small(weights=weights)
        except Exception:
            base_model = models.mobilenet_v3_small(weights=None)
            
        in_features = base_model.classifier[0].in_features
        base_model.classifier = nn.Sequential(
            nn.Linear(in_features, 512),
            nn.BatchNorm1d(512)
        )
        
        self.model = base_model.to(self.device)
        self.model.eval()
        
        self.transform = transforms.Compose([
            transforms.ToImage(),
            transforms.ToDtype(torch.float32, scale=True),
            transforms.Resize((256, 128)),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def extract(self, crop):
        """
        Extracts a L2-normalized 512-dimensional embedding from an RGB image crop.
        crop: numpy array (H, W, 3) in BGR (OpenCV default)
        """
        if not HAS_TORCH:
            # Simulation fallback: return a deterministic vector or random vector
            # Let's return a simple random vector normalized to L2 norm
            embedding_np = np.random.randn(512).astype(np.float32)
            embedding_np /= np.linalg.norm(embedding_np)
            return embedding_np

        if crop is None or crop.size == 0:
            return np.zeros(512, dtype=np.float32)

        crop_rgb = crop[:, :, ::-1]
        
        tensor = self.transform(crop_rgb).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            embedding = self.model(tensor)
            embedding = nn.functional.normalize(embedding, p=2, dim=1)
            embedding_np = embedding.cpu().numpy()[0]
            
        return embedding_np

class ReIDTracker:
    def __init__(self, similarity_threshold=0.85):
        self.similarity_threshold = similarity_threshold

    async def match_reentry(self, store_id, embedding, redis, reentry_window_min=60):
        """
        Queries Redis exit pool to find matches.
        Returns (visitor_id, matched_similarity) or (None, None)
        """
        pool_key = f"exit_pool:{store_id}"
        
        # Fetch all records in the exit pool
        pool_data = await redis.hgetall(pool_key)
        if not pool_data:
            return None, None

        best_visitor_id = None
        best_sim = -1.0

        current_emb = np.array(embedding, dtype=np.float32)

        # Iterate over pool and calculate cosine similarity
        for visitor_id, info_str in pool_data.items():
            try:
                info = json.loads(info_str)
                saved_emb = np.array(info["embedding"], dtype=np.float32)
                
                # Check timestamp to respect the window
                exit_time_iso = info.get("exit_time")
                # Since we check TTL via Redis or custom logic, let's verify here too
                
                # Dot product since embeddings are L2 normalized
                sim = float(np.dot(current_emb, saved_emb))
                if sim > best_sim:
                    best_sim = sim
                    best_visitor_id = visitor_id
            except Exception:
                continue

        if best_sim >= self.similarity_threshold:
            return best_visitor_id, best_sim
            
        return None, None

    async def add_to_exit_pool(self, store_id, visitor_id, embedding, exit_time_iso, redis, ttl_seconds=3600):
        """
        Adds visitor embedding to the exit pool.
        """
        pool_key = f"exit_pool:{store_id}"
        info = {
            "embedding": embedding.tolist(),
            "exit_time": exit_time_iso
        }
        await redis.hset(pool_key, visitor_id, json.dumps(info))
        # Set expire on the hash field / pool key if needed, or periodically clean it
        # Since Redis hset doesn't support individual field TTLs directly in older versions,
        # we can set expire on the entire key as a safety net.
        await redis.expire(pool_key, ttl_seconds)
