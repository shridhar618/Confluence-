"""
Phase 15 — real face recognition, replacing the Phase 0-flagged placeholder.

The previous implementation resized the ENTIRE image (background and all)
to 64x64 grayscale and ran it through a GaussianRandomProjection fit once
on whichever image happened to be processed first after server startup --
not real face recognition by any definition, and specifically not what
the capstone brief asks for ("Use OpenCV and a pre-trained face
recognition approach. Do NOT train a deep learning face model from
scratch.").

This version:
  1. Uses OpenCV's bundled Haar cascade to actually DETECT and crop the
     face region first -- previously nothing located the face at all, so
     framing/background dominated the "embedding."
  2. Uses the `face_recognition` library (a thin wrapper around dlib's
     pretrained ResNet face-embedding model) to generate a genuine 128-d
     face embedding of the cropped region -- a real pretrained model, not
     one trained from scratch here.
  3. Matches using face_recognition's own documented metric (Euclidean
     distance, default tolerance 0.6) rather than an arbitrary
     cosine-similarity threshold that was never calibrated for these
     vectors.

IMPORTANT -- verification status (see docs/PHASE_15_NOTES.md):
`face_recognition`/`dlib` could not be installed or tested in the sandbox
this was written in (no network for the compiled dependency). OpenCV
itself WAS available and the Haar cascade detection path was verified
against the library's real API. The embedding/matching code below is
written against face_recognition's real, documented interface from
training knowledge, but has never been executed. Please treat this
phase's face-recognition accuracy as unverified until you've tested it
with a real camera.

If `face_recognition` is not installed, this module raises a clear,
actionable error rather than silently falling back to the old
placeholder -- a wrong "no match" is safer than a confident-looking match
from a method that doesn't actually recognize faces.
"""

import base64
import hashlib
import io

import numpy as np

from app.models.face_profile import FaceProfile

MATCH_TOLERANCE = 0.6  # face_recognition's own documented default; lower = stricter
_FACE_CASCADE = None


def _get_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        import cv2
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _FACE_CASCADE = cv2.CascadeClassifier(cascade_path)
        if _FACE_CASCADE.empty():
            raise RuntimeError("Failed to load OpenCV's bundled Haar cascade for face detection.")
    return _FACE_CASCADE


def _decode_image_bytes(image_payload: str) -> bytes:
    if not image_payload:
        raise ValueError("Image payload is required")

    payload = image_payload.strip()
    if "," in payload and payload.startswith("data:image"):
        payload = payload.split(",", 1)[1]

    try:
        return base64.b64decode(payload, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid base64 image payload") from exc


def _load_rgb_array(raw_bytes: bytes) -> np.ndarray:
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError("Pillow is required for image decoding. Install backend dependencies first.") from exc

    try:
        image = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Unsupported image format") from exc

    return np.asarray(image, dtype=np.uint8)


def _detect_largest_face(rgb_array: np.ndarray):
    """Returns (top, right, bottom, left) of the largest detected face, or
    raises ValueError if none is found. Using the largest face (rather
    than erroring on multiple detections) matches the realistic case of an
    attendance camera occasionally picking up a second person in the
    background.
    """
    import cv2

    gray = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2GRAY)
    cascade = _get_face_cascade()
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    if len(faces) == 0:
        raise ValueError("No face detected in image. Please ensure your face is clearly visible and well-lit.")

    # (x, y, w, h) -> pick the largest by area, then add a small margin so
    # the embedding model sees a bit of context around the tightly-cropped
    # Haar box rather than a razor-tight crop that can hurt embedding quality.
    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
    margin = int(0.15 * max(w, h))
    top = max(0, y - margin)
    left = max(0, x - margin)
    bottom = min(rgb_array.shape[0], y + h + margin)
    right = min(rgb_array.shape[1], x + w + margin)
    return (top, right, bottom, left)


def build_face_embedding(image_payload: str) -> tuple[np.ndarray, str]:
    try:
        import face_recognition
    except ImportError as exc:
        raise ValueError(
            "Face recognition is not available in this environment: the 'face_recognition' "
            "package (and its 'dlib' dependency) is not installed. Install backend "
            "dependencies (see requirements.txt) before using face enrollment or verification."
        ) from exc

    raw = _decode_image_bytes(image_payload)
    rgb_array = _load_rgb_array(raw)
    face_location = _detect_largest_face(rgb_array)

    encodings = face_recognition.face_encodings(rgb_array, known_face_locations=[face_location])
    if not encodings:
        raise ValueError(
            "A face region was located but a usable embedding could not be generated. "
            "Try a clearer, front-facing, well-lit photo."
        )

    embedding = encodings[0].astype(np.float32)
    sample_hash = hashlib.sha256(raw).hexdigest()
    return embedding, sample_hash


def match_face(image_payload: str, tolerance: float = MATCH_TOLERANCE):
    """Returns (best_profile_or_None, confidence) where confidence is a
    friendly 0-1 "higher is better" value derived from the underlying
    Euclidean distance, for API/UI consistency with the previous
    implementation -- callers only ever display this, they don't
    re-threshold it (see docs/PHASE_15_NOTES.md), so keeping the same
    contract shape means no caller needed to change.
    """
    probe_embedding, _ = build_face_embedding(image_payload)
    profiles = FaceProfile.query.all()
    if not profiles:
        return None, 0.0

    best_profile = None
    best_distance = float("inf")

    for profile in profiles:
        known = profile.get_embedding()
        distance = float(np.linalg.norm(known - probe_embedding))
        if distance < best_distance:
            best_distance = distance
            best_profile = profile

    confidence = max(0.0, 1.0 - best_distance)
    if best_profile is None or best_distance > tolerance:
        return None, confidence
    return best_profile, confidence
