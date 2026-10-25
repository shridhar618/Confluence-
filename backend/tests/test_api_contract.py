import base64
import io

from PIL import Image, ImageDraw

from tests.test_work_management import _create_assignment


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


def _assert_iso_datetime(value):
    assert isinstance(value, str)
    assert "T" in value


def _assert_user_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {
        "id",
        "username",
        "email",
        "role",
        "role_id",
        "created_at",
        "is_active",
        "face_enrolled",
        "sensitive_query_count",
        "is_suspicious",
        "flagged_at",
    }
    assert isinstance(payload["id"], int)
    assert isinstance(payload["username"], str)
    assert isinstance(payload["email"], str)
    assert isinstance(payload["role"], str)
    assert payload["role_id"] is None or isinstance(payload["role_id"], int)
    _assert_iso_datetime(payload["created_at"])
    assert isinstance(payload["is_active"], bool)
    assert isinstance(payload["face_enrolled"], bool)
    assert isinstance(payload["sensitive_query_count"], int)
    assert isinstance(payload["is_suspicious"], bool)
    assert payload["flagged_at"] is None or isinstance(payload["flagged_at"], str)


def _assert_kpi_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {
        "expected_units",
        "total_completed_units",
        "completion_ratio",
        "weighted_score",
    }
    for key in payload:
        assert isinstance(payload[key], (int, float))


def _assert_capacity_risk_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {"level", "reasons", "signals"}
    assert isinstance(payload["level"], str)
    assert isinstance(payload["reasons"], list)
    assert all(isinstance(reason, str) for reason in payload["reasons"])
    assert set(payload["signals"]) == {"completion_ratio", "days_until_due"}
    assert isinstance(payload["signals"]["completion_ratio"], (int, float))
    assert payload["signals"]["days_until_due"] is None or isinstance(payload["signals"]["days_until_due"], int)


def _assert_progress_update_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {
        "id",
        "assignment_id",
        "reported_by_user_id",
        "reported_by_username",
        "completed_units",
        "note",
        "created_at",
    }
    assert isinstance(payload["id"], int)
    assert isinstance(payload["assignment_id"], int)
    assert isinstance(payload["reported_by_user_id"], int)
    assert payload["reported_by_username"] is None or isinstance(payload["reported_by_username"], str)
    assert isinstance(payload["completed_units"], (int, float))
    assert payload["note"] is None or isinstance(payload["note"], str)
    _assert_iso_datetime(payload["created_at"])


def _assert_assignment_summary_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {"id", "title", "status"}
    assert isinstance(payload["id"], int)
    assert isinstance(payload["title"], str)
    assert isinstance(payload["status"], str)


def _assert_assignment_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {
        "id",
        "project_id",
        "parent_id",
        "title",
        "description",
        "assigned_by_user_id",
        "assigned_to_user_id",
        "expected_units",
        "weight",
        "github_issue_id",
        "github_branch",
        "due_date",
        "status",
        "created_at",
        "updated_at",
        "child_count",
        "is_leaf",
        "kpi",
        "progress_updates",
        "assigned_by_username",
        "assigned_to_username",
        "assigned_by_user",
        "assigned_to_user",
        "project",
        "parent",
        "breadcrumbs",
        "children",
        "capacity_risk",
        "open_escalation",
    }
    assert isinstance(payload["id"], int)
    assert payload["project_id"] is None or isinstance(payload["project_id"], int)
    assert payload["parent_id"] is None or isinstance(payload["parent_id"], int)
    assert isinstance(payload["title"], str)
    assert payload["description"] is None or isinstance(payload["description"], str)
    assert isinstance(payload["assigned_by_user_id"], int)
    assert isinstance(payload["assigned_to_user_id"], int)
    assert isinstance(payload["expected_units"], (int, float))
    assert isinstance(payload["weight"], (int, float))
    assert payload["github_issue_id"] is None or isinstance(payload["github_issue_id"], str)
    assert payload["github_branch"] is None or isinstance(payload["github_branch"], str)
    assert payload["due_date"] is None or isinstance(payload["due_date"], str)
    assert isinstance(payload["status"], str)
    _assert_iso_datetime(payload["created_at"])
    _assert_iso_datetime(payload["updated_at"])
    assert isinstance(payload["child_count"], int)
    assert isinstance(payload["is_leaf"], bool)
    _assert_kpi_contract(payload["kpi"])
    assert isinstance(payload["progress_updates"], list)
    for update in payload["progress_updates"]:
        _assert_progress_update_contract(update)
    assert payload["assigned_by_username"] is None or isinstance(payload["assigned_by_username"], str)
    assert payload["assigned_to_username"] is None or isinstance(payload["assigned_to_username"], str)
    assert payload["assigned_by_user"] is None or _assert_user_contract(payload["assigned_by_user"]) is None
    assert payload["assigned_to_user"] is None or _assert_user_contract(payload["assigned_to_user"]) is None
    if payload["project"] is not None:
        assert isinstance(payload["project"], dict)
    if payload["parent"] is not None:
        _assert_assignment_summary_contract(payload["parent"])
    assert isinstance(payload["breadcrumbs"], list)
    for item in payload["breadcrumbs"]:
        _assert_assignment_summary_contract(item)
    if payload["children"] is not None:
        assert isinstance(payload["children"], list)
    _assert_capacity_risk_contract(payload["capacity_risk"])
    if payload["open_escalation"] is not None:
        _assert_escalation_contract(payload["open_escalation"])


def _assert_escalation_contract(payload):
    assert isinstance(payload, dict)
    assert set(payload) == {
        "id",
        "assignment_id",
        "reason",
        "status",
        "created_by_user_id",
        "created_by_username",
        "assignment_title",
        "created_at",
        "assignment",
    }
    assert isinstance(payload["id"], int)
    assert isinstance(payload["assignment_id"], int)
    assert payload["reason"] is None or isinstance(payload["reason"], str)
    assert isinstance(payload["status"], str)
    assert isinstance(payload["created_by_user_id"], int)
    assert payload["created_by_username"] is None or isinstance(payload["created_by_username"], str)
    assert payload["assignment_title"] is None or isinstance(payload["assignment_title"], str)
    _assert_iso_datetime(payload["created_at"])
    if payload["assignment"] is not None:
        _assert_assignment_summary_contract(payload["assignment"])


def test_login_endpoint_contract(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"token", "user"}
    assert isinstance(body["token"], str)
    assert body["token"]
    _assert_user_contract(body["user"])


def test_users_endpoint_contract(client, auth_headers):
    response = client.get(
        "/api/users",
        headers=auth_headers("admin", "admin123"),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"users"}
    assert isinstance(body["users"], list)
    assert body["users"]
    for user in body["users"]:
        _assert_user_contract(user)
    assert all(user["username"] != "admin" for user in body["users"])


def test_roles_endpoint_includes_expanded_role_catalog(client):
    response = client.get("/api/roles")

    assert response.status_code == 200
    body = response.get_json()
    role_names = {role["name"] for role in body["roles"]}
    assert {"Admin", "HR", "Developer", "Project Manager", "DevOps Engineer", "Recruiter"} <= role_names


def test_list_assignments_endpoint_contract(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Contract List Assignment",
        expected_units=8,
        weight=0.5,
    )

    response = client.get(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"assignments", "count"}
    assert isinstance(body["assignments"], list)
    assert all(isinstance(item, dict) for item in body["assignments"])
    assert isinstance(body["count"], int)
    assignment = next(item for item in body["assignments"] if item["id"] == assignment_id)
    _assert_assignment_contract(assignment)


def test_work_board_endpoint_contract(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Contract Board Assignment",
        expected_units=4,
    )

    response = client.get(
        "/api/work/board",
        headers=auth_headers("admin", "admin123"),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"assignments", "columns", "count"}
    assert isinstance(body["assignments"], list)
    assert all(isinstance(item, dict) for item in body["assignments"])
    assert isinstance(body["columns"], list)
    assert all(isinstance(column, str) for column in body["columns"])
    assert body["columns"] == ["todo", "in_progress", "blocked", "completed"]
    assert isinstance(body["count"], int)
    assignment = next(item for item in body["assignments"] if item["id"] == assignment_id)
    _assert_assignment_contract(assignment)


def test_create_assignment_endpoint_contract(client, auth_headers, users):
    response = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Contract Create Assignment",
            "description": "Contract check payload",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 12,
            "weight": 0.6,
            "due_date": "2026-05-01",
        },
    )

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"message", "assignment"}
    assert isinstance(body["message"], str)
    assert isinstance(body["assignment"], dict)
    _assert_assignment_contract(body["assignment"])


def test_update_assignment_status_endpoint_contract(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["hr_jane"],
        assigned_to_user_id=users["intern_bob"],
        title="Contract Patch Assignment",
        expected_units=7,
    )

    response = client.patch(
        f"/api/work/assignments/{assignment_id}/status",
        headers=auth_headers("hr_jane", "hr123"),
        json={"status": "blocked"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"message", "assignment"}
    assert isinstance(body["message"], str)
    assert isinstance(body["assignment"], dict)
    _assert_assignment_contract(body["assignment"])
    assert body["assignment"]["status"] == "blocked"


def test_create_escalation_endpoint_contract(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Contract Escalation Assignment",
        expected_units=9,
    )

    response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "Contract escalation"},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"message", "escalation"}
    assert isinstance(body["message"], str)
    assert isinstance(body["escalation"], dict)
    _assert_escalation_contract(body["escalation"])


def test_list_escalations_endpoint_contract(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Contract Escalation List Assignment",
        expected_units=6,
    )
    create_response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "List contract escalation"},
    )
    escalation_id = create_response.get_json()["escalation"]["id"]

    response = client.get(
        "/api/work/escalations",
        headers=auth_headers("hr_jane", "hr123"),
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"escalations", "count"}
    assert isinstance(body["escalations"], list)
    assert all(isinstance(item, dict) for item in body["escalations"])
    assert isinstance(body["count"], int)
    escalation = next(item for item in body["escalations"] if item["id"] == escalation_id)
    _assert_escalation_contract(escalation)


def test_update_escalation_endpoint_contract(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Contract Escalation Patch Assignment",
        expected_units=5,
    )
    create_response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "Resolve contract escalation"},
    )
    escalation_id = create_response.get_json()["escalation"]["id"]

    response = client.patch(
        f"/api/work/escalations/{escalation_id}",
        headers=auth_headers("hr_jane", "hr123"),
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert isinstance(body, dict)
    assert set(body) == {"message", "escalation"}
    assert isinstance(body["message"], str)
    assert isinstance(body["escalation"], dict)
    _assert_escalation_contract(body["escalation"])
    assert body["escalation"]["status"] == "resolved"


def test_admin_create_user_requires_face_image(client, auth_headers):
    response = client.post(
        "/api/admin/create-user",
        headers=auth_headers("admin", "admin123"),
        json={"username": "new_joiner", "role": "intern"},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Username, role, and face image are required"


def test_admin_create_user_returns_face_profile_contract(client, auth_headers):
    response = client.post(
        "/api/admin/create-user",
        headers=auth_headers("admin", "admin123"),
        json={
            "username": "new_joiner",
            "role": "intern",
            "image_base64": _sample_face_image(),
        },
    )

    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert set(body) == {"message", "login_code", "user", "face_profile"}
    assert isinstance(body["message"], str)
    assert isinstance(body["login_code"], str)
    _assert_user_contract(body["user"])
    assert body["user"]["face_enrolled"] is True
    assert isinstance(body["face_profile"], dict)
    assert body["face_profile"]["user_id"] == body["user"]["id"]
    assert body["face_profile"]["username"] == body["user"]["username"]
