"""Face embedding service using InsightFace.

Implements face detection, embedding extraction, and similarity comparison
for character consistency across video generation.
"""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class FaceDetection:
    """Detected face with bounding box and landmarks."""
    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    landmarks: list[tuple[float, float]] | None = None
    embedding: np.ndarray | None = None
    age: int | None = None
    gender: str | None = None


@dataclass
class FaceEmbeddingResult:
    """Result from face embedding extraction."""
    success: bool
    faces: list[FaceDetection]
    primary_embedding: np.ndarray | None = None
    error: str | None = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "success": self.success,
            "face_count": len(self.faces),
            "faces": [
                {
                    "bbox": f.bbox,
                    "confidence": f.confidence,
                    "age": f.age,
                    "gender": f.gender,
                    "has_embedding": f.embedding is not None,
                }
                for f in self.faces
            ],
            "has_primary_embedding": self.primary_embedding is not None,
            "error": self.error,
            "metadata": self.metadata,
        }


class FaceEmbeddingService:
    """Service for face detection and embedding extraction.

    Uses InsightFace for:
    - Face detection with bounding boxes
    - Face alignment and normalization
    - 512-dimensional embedding extraction
    - Face similarity comparison
    - Face quality scoring for pre-extraction filtering

    The embeddings enable character consistency across shots.
    """

    # Cosine similarity threshold for same person
    SIMILARITY_THRESHOLD = 0.4

    # Quality thresholds
    MIN_FACE_SIZE = 64  # Minimum face dimension in pixels
    MIN_CONFIDENCE = 0.5  # Minimum detection confidence
    EMBEDDING_CONFIDENCE_HIGH = 0.85  # High quality threshold
    EMBEDDING_CONFIDENCE_MEDIUM = 0.7  # Medium quality threshold

    # Model configuration
    DEFAULT_MODEL = "buffalo_l"  # Higher accuracy
    LIGHTWEIGHT_MODEL = "buffalo_s"  # Faster

    def __init__(self, model_name: str | None = None, gpu_id: int = 0) -> None:
        """Initialize the face embedding service.

        Args:
            model_name: InsightFace model to use (buffalo_l, buffalo_s)
            gpu_id: GPU ID to use (-1 for CPU)
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.gpu_id = gpu_id
        self._app = None
        self._initialized = False

    def _lazy_init(self) -> bool:
        """Lazily initialize InsightFace model."""
        if self._initialized:
            return True

        try:
            from insightface.app import FaceAnalysis

            self._app = FaceAnalysis(
                name=self.model_name,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )

            # Prepare for specific GPU or CPU
            ctx_id = self.gpu_id if self.gpu_id >= 0 else -1
            self._app.prepare(ctx_id=ctx_id, det_size=(640, 640))

            self._initialized = True
            logger.info(f"InsightFace initialized with model {self.model_name}")
            return True

        except ImportError:
            logger.warning("InsightFace not installed. Face embedding disabled.")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize InsightFace: {e}")
            return False

    def extract_embedding(
        self,
        image_path: str | Path,
        select_largest: bool = True,
    ) -> FaceEmbeddingResult:
        """Extract face embeddings from an image.

        Args:
            image_path: Path to image file
            select_largest: If multiple faces, use largest as primary

        Returns:
            FaceEmbeddingResult with detected faces and embeddings
        """
        image_path = Path(image_path)

        if not image_path.exists():
            return FaceEmbeddingResult(
                success=False,
                faces=[],
                error=f"Image not found: {image_path}",
            )

        if not self._lazy_init():
            return FaceEmbeddingResult(
                success=False,
                faces=[],
                error="InsightFace not available",
            )

        try:
            import cv2

            # Load image
            img = cv2.imread(str(image_path))
            if img is None:
                return FaceEmbeddingResult(
                    success=False,
                    faces=[],
                    error=f"Could not read image: {image_path}",
                )

            # Detect faces
            detected = self._app.get(img)

            if not detected:
                return FaceEmbeddingResult(
                    success=True,
                    faces=[],
                    metadata={"image_shape": img.shape},
                )

            # Convert to FaceDetection objects
            faces = []
            for face in detected:
                bbox = tuple(int(x) for x in face.bbox)
                detection = FaceDetection(
                    bbox=bbox,
                    confidence=float(face.det_score),
                    landmarks=face.kps.tolist() if face.kps is not None else None,
                    embedding=face.embedding,
                    age=int(face.age) if hasattr(face, 'age') and face.age else None,
                    gender='male' if hasattr(face, 'gender') and face.gender == 1 else 'female' if hasattr(face, 'gender') else None,
                )
                faces.append(detection)

            # Sort by face size (largest first)
            faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

            # Select primary embedding
            primary_embedding = None
            if select_largest and faces:
                primary_embedding = faces[0].embedding

            return FaceEmbeddingResult(
                success=True,
                faces=faces,
                primary_embedding=primary_embedding,
                metadata={
                    "image_shape": img.shape,
                    "face_count": len(faces),
                },
            )

        except Exception as e:
            logger.exception(f"Error extracting embedding: {e}")
            return FaceEmbeddingResult(
                success=False,
                faces=[],
                error=str(e),
            )

    def extract_embedding_from_bytes(
        self,
        image_data: bytes,
        select_largest: bool = True,
    ) -> FaceEmbeddingResult:
        """Extract face embeddings from image bytes.

        Args:
            image_data: Raw image bytes
            select_largest: If multiple faces, use largest as primary

        Returns:
            FaceEmbeddingResult with detected faces and embeddings
        """
        if not self._lazy_init():
            return FaceEmbeddingResult(
                success=False,
                faces=[],
                error="InsightFace not available",
            )

        try:
            import cv2

            # Decode image from bytes
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return FaceEmbeddingResult(
                    success=False,
                    faces=[],
                    error="Could not decode image data",
                )

            # Same logic as file-based extraction
            detected = self._app.get(img)

            if not detected:
                return FaceEmbeddingResult(
                    success=True,
                    faces=[],
                    metadata={"image_shape": img.shape},
                )

            faces = []
            for face in detected:
                bbox = tuple(int(x) for x in face.bbox)
                detection = FaceDetection(
                    bbox=bbox,
                    confidence=float(face.det_score),
                    landmarks=face.kps.tolist() if face.kps is not None else None,
                    embedding=face.embedding,
                    age=int(face.age) if hasattr(face, 'age') and face.age else None,
                    gender='male' if hasattr(face, 'gender') and face.gender == 1 else 'female' if hasattr(face, 'gender') else None,
                )
                faces.append(detection)

            faces.sort(key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]), reverse=True)

            primary_embedding = faces[0].embedding if select_largest and faces else None

            return FaceEmbeddingResult(
                success=True,
                faces=faces,
                primary_embedding=primary_embedding,
                metadata={"image_shape": img.shape, "face_count": len(faces)},
            )

        except Exception as e:
            logger.exception(f"Error extracting embedding from bytes: {e}")
            return FaceEmbeddingResult(
                success=False,
                faces=[],
                error=str(e),
            )

    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """Compute cosine similarity between two face embeddings.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            Cosine similarity score (0-1, higher = more similar)
        """
        if embedding1 is None or embedding2 is None:
            return 0.0

        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)

        # Clamp to [0, 1]
        return float(max(0.0, min(1.0, (similarity + 1) / 2)))

    def is_same_person(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        threshold: float | None = None,
    ) -> tuple[bool, float]:
        """Check if two embeddings are from the same person.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Similarity threshold (default: SIMILARITY_THRESHOLD)

        Returns:
            Tuple of (is_same_person, similarity_score)
        """
        threshold = threshold or self.SIMILARITY_THRESHOLD
        similarity = self.compute_similarity(embedding1, embedding2)
        return (similarity >= threshold, similarity)

    def find_best_match(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: list[np.ndarray],
    ) -> tuple[int, float]:
        """Find the best matching embedding from candidates.

        Args:
            query_embedding: The embedding to match
            candidate_embeddings: List of candidate embeddings

        Returns:
            Tuple of (best_index, similarity_score)
        """
        if not candidate_embeddings:
            return (-1, 0.0)

        best_idx = -1
        best_sim = 0.0

        for idx, candidate in enumerate(candidate_embeddings):
            sim = self.compute_similarity(query_embedding, candidate)
            if sim > best_sim:
                best_sim = sim
                best_idx = idx

        return (best_idx, best_sim)

    def save_embedding(
        self,
        embedding: np.ndarray,
        output_path: str | Path,
    ) -> bool:
        """Save embedding to file.

        Args:
            embedding: Face embedding array
            output_path: Path to save the embedding

        Returns:
            True if saved successfully
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            np.save(str(output_path), embedding)
            return True
        except Exception as e:
            logger.error(f"Failed to save embedding: {e}")
            return False

    def load_embedding(
        self,
        embedding_path: str | Path,
    ) -> np.ndarray | None:
        """Load embedding from file.

        Args:
            embedding_path: Path to the embedding file

        Returns:
            Embedding array or None
        """
        try:
            embedding_path = Path(embedding_path)
            if not embedding_path.exists():
                return None
            return np.load(str(embedding_path))
        except Exception as e:
            logger.error(f"Failed to load embedding: {e}")
            return None

    def crop_face(
        self,
        image_path: str | Path,
        detection: FaceDetection,
        padding: float = 0.3,
    ) -> np.ndarray | None:
        """Crop and align face from image.

        Args:
            image_path: Path to image
            detection: FaceDetection with bbox
            padding: Padding ratio around face

        Returns:
            Cropped face image as numpy array
        """
        try:
            import cv2

            img = cv2.imread(str(image_path))
            if img is None:
                return None

            x1, y1, x2, y2 = detection.bbox
            h, w = img.shape[:2]

            # Add padding
            pad_w = int((x2 - x1) * padding)
            pad_h = int((y2 - y1) * padding)

            x1 = max(0, x1 - pad_w)
            y1 = max(0, y1 - pad_h)
            x2 = min(w, x2 + pad_w)
            y2 = min(h, y2 + pad_h)

            return img[y1:y2, x1:x2]

        except Exception as e:
            logger.error(f"Failed to crop face: {e}")
            return None

    def score_face_quality(
        self,
        detection: FaceDetection,
        image_shape: tuple[int, int, int] | None = None,
    ) -> dict[str, Any]:
        """Score face quality for embedding reliability.

        Evaluates multiple quality factors to determine if the face
        is suitable for reliable embedding extraction.

        Args:
            detection: FaceDetection object to score
            image_shape: Optional (height, width, channels) of source image

        Returns:
            Dict with quality scores and recommendations
        """
        scores = {}

        # 1. Face size score (larger = better for embedding)
        x1, y1, x2, y2 = detection.bbox
        face_width = x2 - x1
        face_height = y2 - y1
        face_width * face_height

        if face_width < self.MIN_FACE_SIZE or face_height < self.MIN_FACE_SIZE:
            size_score = 0.2
        elif face_width < 128 or face_height < 128:
            size_score = 0.5
        elif face_width < 256 or face_height < 256:
            size_score = 0.75
        else:
            size_score = 1.0
        scores["size"] = size_score

        # 2. Detection confidence score
        confidence_score = min(1.0, detection.confidence / self.EMBEDDING_CONFIDENCE_HIGH)
        scores["confidence"] = confidence_score

        # 3. Position score (centered faces are typically better)
        if image_shape is not None:
            h, w = image_shape[:2]
            center_x = (x1 + x2) / 2
            center_y = (y1 + y2) / 2

            # Distance from center as proportion
            dx = abs(center_x - w/2) / (w/2)
            dy = abs(center_y - h/2) / (h/2)
            position_score = 1.0 - (dx + dy) / 2
        else:
            position_score = 0.8  # Default if no image shape
        scores["position"] = position_score

        # 4. Aspect ratio score (faces should be roughly square to slightly taller)
        aspect = face_width / max(face_height, 1)
        if 0.7 <= aspect <= 1.0:
            aspect_score = 1.0
        elif 0.5 <= aspect <= 1.3:
            aspect_score = 0.75
        else:
            aspect_score = 0.5
        scores["aspect_ratio"] = aspect_score

        # 5. Landmark quality (if available)
        if detection.landmarks:
            # Check if landmarks form reasonable face structure
            landmarks_score = 0.9 if len(detection.landmarks) >= 5 else 0.6
        else:
            landmarks_score = 0.5
        scores["landmarks"] = landmarks_score

        # Calculate overall score (weighted average)
        weights = {
            "size": 0.25,
            "confidence": 0.30,
            "position": 0.15,
            "aspect_ratio": 0.10,
            "landmarks": 0.20,
        }

        overall = sum(scores[k] * weights[k] for k in weights)

        # Determine quality tier
        if overall >= 0.85:
            quality_tier = "high"
            recommendation = "Excellent for embedding extraction"
        elif overall >= 0.70:
            quality_tier = "medium"
            recommendation = "Acceptable for embedding, may have minor issues"
        elif overall >= 0.50:
            quality_tier = "low"
            recommendation = "May produce unreliable embedding, consider alternatives"
        else:
            quality_tier = "poor"
            recommendation = "Not recommended for embedding extraction"

        return {
            "overall_score": round(overall, 3),
            "quality_tier": quality_tier,
            "recommendation": recommendation,
            "component_scores": scores,
            "face_dimensions": {"width": face_width, "height": face_height},
            "usable_for_embedding": overall >= self.MIN_CONFIDENCE,
        }

    def select_best_face(
        self,
        faces: list[FaceDetection],
        image_shape: tuple[int, int, int] | None = None,
    ) -> tuple[FaceDetection | None, dict[str, Any]]:
        """Select the best face from multiple detections for embedding.

        Args:
            faces: List of detected faces
            image_shape: Source image shape for quality scoring

        Returns:
            Tuple of (best_face, quality_info)
        """
        if not faces:
            return None, {"error": "No faces provided"}

        best_face = None
        best_score = -1.0
        all_scores = []

        for i, face in enumerate(faces):
            quality = self.score_face_quality(face, image_shape)
            all_scores.append({"face_index": i, **quality})

            if quality["overall_score"] > best_score:
                best_score = quality["overall_score"]
                best_face = face

        return best_face, {
            "selected_score": best_score,
            "all_face_scores": all_scores,
            "total_faces": len(faces),
        }


# Singleton instance
_face_service: FaceEmbeddingService | None = None


def get_face_embedding_service() -> FaceEmbeddingService:
    """Get or create the face embedding service singleton."""
    global _face_service
    if _face_service is None:
        _face_service = FaceEmbeddingService()
    return _face_service
