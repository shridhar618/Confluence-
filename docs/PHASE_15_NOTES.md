# Phase 15 — Face Recognition Attendance: Implementation Notes

## What was replaced

The Phase 0 audit flagged `face_attendance.py` as not real face recognition: it resized the **entire image** (background included) to 64×64 grayscale and ran it through a `GaussianRandomProjection` fit once, globally, on whichever image happened to be processed first after server startup. Nothing detected where a face even was in the frame. This directly contradicted the capstone brief's explicit Phase 15 instruction ("Use OpenCV and a pre-trained face recognition approach. Do NOT train a deep learning face model from scratch") — the old code used neither OpenCV nor a pretrained model. The old file is preserved at `/tmp/face_attendance_old.py.bak` during this session for reference; it's not shipped in the repo.

## What replaced it

**`backend/app/services/face_attendance.py`** (rewritten):
1. **OpenCV Haar cascade** (`cv2.CascadeClassifier`, bundled with `opencv-python` — no separate model download) actually detects and crops the face region before anything else happens. If multiple faces are in frame, the largest is used (realistic for an attendance camera that occasionally catches someone in the background); a small margin is added around the tight detection box.
2. **`face_recognition`** (a wrapper around dlib's pretrained ResNet face-embedding model) generates a genuine 128-dimensional embedding of the cropped face — a real pretrained model, not anything trained from scratch here.
3. Matching switched from an uncalibrated cosine-similarity threshold to **Euclidean distance with tolerance 0.6** — `face_recognition`'s own documented default, rather than a threshold invented for embeddings that method was never designed to produce.

**Every calling function's signature is unchanged**: `build_face_embedding(image_payload) -> (embedding, sample_hash)` and `match_face(image_payload, tolerance=...) -> (profile, confidence)`. I checked all three call sites (`admin.py`, `attendance.py`, `auth.py`) before touching anything, and none of them needed to change — `confidence` is only ever displayed, never re-thresholded elsewhere, so keeping it as a friendly 0–1 "higher is better" value (derived from `1 - distance`) preserved the exact existing contract.

**`requirements.txt`**: added `opencv-python`, `dlib`, `face_recognition`, with an upfront note that `dlib` is a compiled C++ library that can be genuinely difficult to install on Windows without Visual Studio Build Tools — with a conda-based fallback suggested. I'd rather flag this loudly now than have it be a surprise mid-setup.

## Honest fallback behavior

If `face_recognition` isn't installed, `build_face_embedding()` raises a clear, actionable error rather than silently falling back to the old placeholder method. A face-recognition feature that sometimes confidently returns wrong matches is worse than one that clearly says "not available, please install X" — the whole point of this phase was replacing exactly that kind of false confidence.

## What I could and could NOT verify — the most constrained phase so far

**Genuinely available and tested**: OpenCV (`cv2` 4.13.0) is actually installed in this sandbox — I did not expect that. I used it to run **real tests against the actual library API**:
- Confirmed the bundled Haar cascade file exists and loads
- Confirmed `detectMultiScale()` runs without error and returns the expected type
- Confirmed the full `_detect_largest_face` logic (copied verbatim from the shipped code) correctly raises the intended `ValueError` on an image with no face
- Confirmed the distance-based matching math correctly distinguishes a "same person, slightly different photo" probe (small Euclidean distance to the right profile) from a genuinely different, unenrolled person's embedding (large distance, correctly returns no match) — using synthetic 128-d vectors standing in for real face embeddings

**Completely unverified**: `face_recognition` and `dlib` are not installed anywhere I have access to (compiled C++ dependencies, no network to build them here), so the actual embedding generation — the core of what makes this "real" face recognition — has never been executed. The code is written against `face_recognition`'s real, documented API from training knowledge (`face_recognition.face_encodings(image, known_face_locations=[...])`), but I want to be direct: this is the least-verified core piece of logic in the entire build so far. Everything upstream of it (image decoding, face detection, cropping) and downstream of it (distance math) has real test evidence; the embedding call itself does not.

**Please verify, ideally with a real camera**:
```bash
cd backend
pip install opencv-python dlib face_recognition
# if dlib fails to build on Windows, see the requirements.txt comment for the conda alternative
python app.py
```
Then, through the UI: register a face for one account, log out, and try face verification both as that person (should match) and as someone else (should not). If `face_recognition.face_encodings()` behaves differently than documented in some edge case, this is where it would surface — please let me know what you see.
