import base64
import io

from PIL import Image, ImageDraw

from app.models.face_profile import FaceProfile


def _sample_face_image(seed=0):
    image = Image.new("L", (64, 64), color=20 + seed)
    draw = ImageDraw.Draw(image)
    draw.ellipse((12, 8, 52, 48), fill=180 - seed)
    draw.ellipse((22, 22, 28, 30), fill=25 + seed)
    draw.ellipse((36, 22, 42, 30), fill=25 + seed)
    draw.arc((24, 28, 40, 42), start=0, end=180, fill=60 + seed, width=2)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def test_employee_cannot_self_register_face(client, auth_headers):
    response = client.post(
        "/api/face/register",
        headers=auth_headers("intern_bob", "intern123"),
        json={"image_base64": _sample_face_image()},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Only admin/hr can manage face enrollment"


def test_admin_can_register_face_for_existing_user(client, auth_headers, users, app):
    response = client.post(
        "/api/face/register",
        headers=auth_headers("admin", "admin123"),
        json={
            "user_id": users["intern_bob"],
            "image_base64": _sample_face_image(),
        },
    )

    assert response.status_code == 200, response.get_json()
    assert response.get_json()["profile"]["user_id"] == users["intern_bob"]

    with app.app_context():
        profile = FaceProfile.query.filter_by(user_id=users["intern_bob"]).first()
        assert profile is not None


def test_face_verify_requires_pre_enrolled_face(client, auth_headers):
    response = client.post(
        "/api/auth/face-verify",
        headers=auth_headers("intern_bob", "intern123"),
        json={"image_base64": _sample_face_image()},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "No face credential is enrolled for this account. Contact admin."


def test_attendance_mark_uses_admin_enrolled_face(client, auth_headers, users):
    create_response = client.post(
        "/api/admin/create-user",
        headers=auth_headers("admin", "admin123"),
        json={
            "username": "face_user",
            "role": "intern",
            "image_base64": _sample_face_image(seed=3),
        },
    )
    assert create_response.status_code == 201, create_response.get_json()
    login_code = create_response.get_json()["login_code"]

    user_headers = client.post(
        "/api/auth/login",
        json={"username": "face_user", "login_code": login_code},
    )
    assert user_headers.status_code == 200, user_headers.get_json()
    token = user_headers.get_json()["token"]

    verify_response = client.post(
        "/api/auth/face-verify",
        headers={"Authorization": f"Bearer {token}"},
        json={"image_base64": _sample_face_image(seed=3)},
    )
    assert verify_response.status_code == 200, verify_response.get_json()

    attendance_response = client.post(
        "/api/attendance/mark",
        headers={"Authorization": f"Bearer {token}"},
        json={"image_base64": _sample_face_image(seed=3)},
    )
    assert attendance_response.status_code == 201, attendance_response.get_json()
    assert attendance_response.get_json()["record"]["username"] == "face_user"
