from datetime import UTC, datetime, timedelta

from app import db
from app.models.attendance_record import AttendanceRecord
from app.models.audit_log import AuditLog
from app.models.role import Role
from app.models.user import User
from app.models import WorkAssignment, WorkEscalation, WorkProgressUpdate
import pytest
from sqlalchemy import text
from werkzeug.security import generate_password_hash


def _create_assignment(app, **overrides):
    payload = {
        "title": "Process Support Tickets",
        "description": "Handle inbound support queue",
        "assigned_by_user_id": overrides.pop("assigned_by_user_id"),
        "assigned_to_user_id": overrides.pop("assigned_to_user_id"),
        "expected_units": 50,
        "weight": 0.4,
        "status": "pending",
    }
    payload.update(overrides)

    with app.app_context():
        assignment = WorkAssignment(**payload)
        db.session.add(assignment)
        db.session.commit()
        db.session.refresh(assignment)
        return assignment.id


def _add_progress(app, assignment_id, reported_by_user_id, completed_units, note=None):
    with app.app_context():
        update = WorkProgressUpdate(
            assignment_id=assignment_id,
            reported_by_user_id=reported_by_user_id,
            completed_units=completed_units,
            note=note,
        )
        db.session.add(update)
        db.session.commit()
        return update.id


def _add_attendance(app, user_id, *, days_ago=0, event_type="check_in"):
    with app.app_context():
        record = AttendanceRecord(
            user_id=user_id,
            event_type=event_type,
            confidence=0.98,
            source="test",
            created_at=datetime.now(UTC) - timedelta(days=days_ago),
        )
        db.session.add(record)
        db.session.commit()
        return record.id


def test_assignment_model_defaults(app, users):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Review Customer Replies",
        expected_units=10,
    )

    with app.app_context():
        assignment = db.session.get(WorkAssignment, assignment_id)
        assert assignment.status == "pending"
        assert assignment.weight == 0.4
        assert assignment.expected_units == 10


def test_parent_child_creation_and_tree_fetch(client, auth_headers, users, app):
    parent_response = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Parent Assignment",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 10,
            "weight": 0.5,
        },
    )
    parent_id = parent_response.get_json()["assignment"]["id"]

    child_response = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Child Assignment",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 4,
            "weight": 0.4,
            "parent_id": parent_id,
        },
    )
    assert child_response.status_code == 201, child_response.get_json()
    child = child_response.get_json()["assignment"]
    assert child["parent_id"] == parent_id

    tree_response = client.get(
        f"/api/work/assignments/{parent_id}/tree",
        headers=auth_headers("admin", "admin123"),
    )
    assert tree_response.status_code == 200
    tree = tree_response.get_json()["assignment"]
    assert tree["child_count"] == 1
    assert tree["children"][0]["id"] == child["id"]


def test_parent_completion_is_derived_from_descendants(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Derived Parent",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 10,
            "weight": 0.6,
        },
    ).get_json()["assignment"]
    first_child = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Leaf 1",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 4,
            "weight": 0.4,
            "parent_id": parent["id"],
        },
    ).get_json()["assignment"]
    second_child = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Leaf 2",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 6,
            "weight": 0.4,
            "parent_id": parent["id"],
        },
    ).get_json()["assignment"]

    patch_parent = client.patch(
        f"/api/work/assignments/{parent['id']}/status",
        headers=auth_headers("admin", "admin123"),
        json={"status": "completed"},
    )
    assert patch_parent.status_code == 400

    client.post(
        f"/api/work/assignments/{first_child['id']}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 4},
    )
    mid_tree = client.get(
        f"/api/work/assignments/{parent['id']}/tree",
        headers=auth_headers("admin", "admin123"),
    ).get_json()["assignment"]
    assert mid_tree["status"] == "in_progress"

    client.post(
        f"/api/work/assignments/{second_child['id']}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 6},
    )
    final_tree = client.get(
        f"/api/work/assignments/{parent['id']}/tree",
        headers=auth_headers("admin", "admin123"),
    ).get_json()["assignment"]
    assert final_tree["status"] == "completed"


def test_cycle_prevention_blocks_invalid_reparenting(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Cycle Parent",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 5,
            "weight": 0.5,
        },
    ).get_json()["assignment"]
    child = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Cycle Child",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 5,
            "weight": 0.5,
            "parent_id": parent["id"],
        },
    ).get_json()["assignment"]

    self_parent = client.patch(
        f"/api/work/assignments/{parent['id']}",
        headers=auth_headers("admin", "admin123"),
        json={"parent_id": parent["id"]},
    )
    assert self_parent.status_code == 400

    cycle = client.patch(
        f"/api/work/assignments/{parent['id']}",
        headers=auth_headers("admin", "admin123"),
        json={"parent_id": child["id"]},
    )
    assert cycle.status_code == 400
    assert "cycles" in cycle.get_json()["error"].lower()


def test_assignment_update_success(client, auth_headers, users):
    assignment = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Update Me",
            "description": "old description",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 8,
            "weight": 0.4,
            "due_date": "2026-05-10",
        },
    ).get_json()["assignment"]

    response = client.patch(
        f"/api/work/assignments/{assignment['id']}",
        headers=auth_headers("hr_jane", "hr123"),
        json={
            "title": "Updated Assignment",
            "description": "new description",
            "assigned_to_user_id": users["intern_amy"],
            "expected_units": 12,
            "weight": 0.7,
            "due_date": "2026-05-20",
            "github_issue_id": "GH-123",
            "github_branch": "feature/work-update",
        },
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()["assignment"]
    assert body["title"] == "Updated Assignment"
    assert body["description"] == "new description"
    assert body["assigned_to_user_id"] == users["intern_amy"]
    assert body["expected_units"] == 12
    assert body["weight"] == 0.7
    assert body["due_date"] == "2026-05-20"
    assert body["github_issue_id"] == "GH-123"
    assert body["github_branch"] == "feature/work-update"


def test_parent_kpi_aggregates_from_descendants(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("hr_jane", "hr123"),
        json={
            "title": "Aggregate Parent",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 99,
            "weight": 0.5,
        },
    ).get_json()["assignment"]
    child_ids = []
    for title, expected in (("Aggregate A", 3), ("Aggregate B", 7)):
        child = client.post(
            "/api/work/assignments",
            headers=auth_headers("hr_jane", "hr123"),
            json={
                "title": title,
                "assigned_to_user_id": users["intern_bob"],
                "expected_units": expected,
                "weight": 0.5,
                "parent_id": parent["id"],
            },
        ).get_json()["assignment"]
        child_ids.append((child["id"], expected))

    client.post(
        f"/api/work/assignments/{child_ids[0][0]}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 3},
    )
    client.post(
        f"/api/work/assignments/{child_ids[1][0]}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 2},
    )

    kpi_response = client.get(
        f"/api/work/assignments/{parent['id']}/kpi",
        headers=auth_headers("hr_jane", "hr123"),
    )
    assert kpi_response.status_code == 200
    assert kpi_response.get_json()["kpi"] == {
        "expected_units": 10,
        "total_completed_units": 5,
        "completion_ratio": 0.5,
        "weighted_score": 0.25,
    }


def test_parent_delete_is_blocked_while_children_exist(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Delete Parent",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 5,
            "weight": 0.5,
        },
    ).get_json()["assignment"]
    client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Delete Child",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 2,
            "weight": 0.5,
            "parent_id": parent["id"],
        },
    )

    response = client.delete(
        f"/api/work/assignments/{parent['id']}",
        headers=auth_headers("admin", "admin123"),
    )
    assert response.status_code == 400
    assert "child assignments" in response.get_json()["error"]


def test_leaf_delete_succeeds(client, auth_headers, users):
    assignment = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Delete Leaf",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 3,
            "weight": 0.5,
        },
    ).get_json()["assignment"]

    response = client.delete(
        f"/api/work/assignments/{assignment['id']}",
        headers=auth_headers("admin", "admin123"),
    )
    assert response.status_code == 200
    assert response.get_json()["message"] == "Assignment deleted"


def test_admin_and_hr_can_create_assignment(client, auth_headers, users, app):
    for username, password in (("admin", "admin123"), ("hr_jane", "hr123")):
        response = client.post(
            "/api/work/assignments",
            headers=auth_headers(username, password),
            json={
                "title": f"Assignment from {username}",
                "assigned_to_user_id": users["intern_bob"],
                "expected_units": 12,
                "weight": 0.5,
                "due_date": "2026-05-01",
            },
        )
        assert response.status_code == 201, response.get_json()
        body = response.get_json()["assignment"]
        assert body["title"] == f"Assignment from {username}"
        assert body["status"] == "pending"
        assert body["kpi"]["expected_units"] == 12
        assert body["kpi"]["total_completed_units"] == 0

    with app.app_context():
        audit_queries = [
            row.query
            for row in db.session.query(AuditLog).order_by(AuditLog.id.asc()).all()
        ]
        assert len(audit_queries) == 2
        assert "Created work assignment" in audit_queries[0]
        assert "Created work assignment" in audit_queries[1]


def test_manager_role_can_create_assignment(client, auth_headers, users, app):
    with app.app_context():
        role = Role.query.filter_by(name="Manager").first()
        manager = User(
            username="manager_mia",
            email="manager@secureai.com",
            password_hash=generate_password_hash("manager123"),
            role="manager",
            role_id=role.id if role else None,
            login_code="MANAGER001",
        )
        db.session.add(manager)
        db.session.commit()

    response = client.post(
        "/api/work/assignments",
        headers=auth_headers("manager_mia", "manager123"),
        json={
            "title": "Assignment from manager",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 12,
            "weight": 0.5,
        },
    )

    assert response.status_code == 201, response.get_json()
    assert response.get_json()["assignment"]["title"] == "Assignment from manager"


def test_non_privileged_user_cannot_create_assignment(client, auth_headers, users):
    response = client.post(
        "/api/work/assignments",
        headers=auth_headers("intern_bob", "intern123"),
        json={
            "title": "Unauthorized Assignment",
            "assigned_to_user_id": users["intern_amy"],
            "expected_units": 10,
            "weight": 0.2,
        },
    )
    assert response.status_code == 403
    assert response.get_json()["error"] == "Manager access required"


def test_assignee_list_is_scoped_and_kpi_is_aggregated(client, auth_headers, users, app):
    bob_assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Bob Assignment",
        expected_units=50,
        weight=0.4,
    )
    _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_amy"],
        title="Amy Assignment",
        expected_units=20,
        weight=0.7,
    )
    _add_progress(app, bob_assignment_id, users["intern_bob"], 15, "Morning batch")
    _add_progress(app, bob_assignment_id, users["intern_bob"], 25, "Afternoon batch")

    response = client.get(
        "/api/work/assignments",
        headers=auth_headers("intern_bob", "intern123"),
    )

    assert response.status_code == 200
    assignments = response.get_json()["assignments"]
    assert len(assignments) == 1
    assignment = assignments[0]
    assert assignment["title"] == "Bob Assignment"
    assert assignment["kpi"]["expected_units"] == 50
    assert assignment["kpi"]["total_completed_units"] == 40
    assert assignment["kpi"]["completion_ratio"] == 0.8
    assert assignment["kpi"]["weighted_score"] == pytest.approx(0.32)


def test_list_assignments_query_filters(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Root Parent",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 10,
            "weight": 0.5,
        },
    ).get_json()["assignment"]
    child = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Nested Child",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 4,
            "weight": 0.4,
            "parent_id": parent["id"],
        },
    ).get_json()["assignment"]
    draft = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Draft Assignment",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 2,
            "weight": 0.2,
            "status": "draft",
        },
    ).get_json()["assignment"]

    root_only_response = client.get(
        "/api/work/assignments?root_only=true",
        headers=auth_headers("admin", "admin123"),
    )
    root_ids = {item["id"] for item in root_only_response.get_json()["assignments"]}
    assert parent["id"] in root_ids
    assert child["id"] not in root_ids

    include_children_response = client.get(
        "/api/work/assignments?root_only=true&include_children=1",
        headers=auth_headers("admin", "admin123"),
    )
    included_parent = next(
        item for item in include_children_response.get_json()["assignments"]
        if item["id"] == parent["id"]
    )
    assert included_parent["children"][0]["id"] == child["id"]

    intern_default = client.get(
        "/api/work/assignments",
        headers=auth_headers("intern_bob", "intern123"),
    )
    intern_titles = {item["title"] for item in intern_default.get_json()["assignments"]}
    assert "Draft Assignment" not in intern_titles

    intern_with_drafts = client.get(
        "/api/work/assignments?include_drafts=true",
        headers=auth_headers("intern_bob", "intern123"),
    )
    intern_with_draft_titles = {item["title"] for item in intern_with_drafts.get_json()["assignments"]}
    assert "Draft Assignment" in intern_with_draft_titles
    assert draft["id"] in {item["id"] for item in intern_with_drafts.get_json()["assignments"]}


def test_assignee_can_submit_progress_and_status_transitions(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        expected_units=10,
        weight=0.5,
    )

    first = client.post(
        f"/api/work/assignments/{assignment_id}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 4},
    )
    assert first.status_code == 201, first.get_json()
    assert first.get_json()["progress_update"]["note"] is None
    assert first.get_json()["assignment"]["status"] == "in_progress"

    second = client.post(
        f"/api/work/assignments/{assignment_id}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 6, "note": "Closed remaining tickets"},
    )
    assert second.status_code == 201, second.get_json()
    assert second.get_json()["assignment"]["status"] == "completed"
    assert second.get_json()["assignment"]["kpi"]["total_completed_units"] == 10


def test_non_assignee_cannot_submit_progress(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
    )

    response = client.post(
        f"/api/work/assignments/{assignment_id}/progress",
        headers=auth_headers("intern_amy", "intern456"),
        json={"completed_units": 3, "note": "Should fail"},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Only the assignee can submit progress"


def test_parent_progress_submission_is_rejected(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Parent For Progress Rejection",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 10,
            "weight": 0.6,
        },
    ).get_json()["assignment"]
    client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Child Leaf",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 5,
            "weight": 0.5,
            "parent_id": parent["id"],
        },
    )

    response = client.post(
        f"/api/work/assignments/{parent['id']}/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 1},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "Progress can only be submitted to leaf assignments"


def test_kpi_endpoint_returns_correct_values(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["hr_jane"],
        assigned_to_user_id=users["intern_bob"],
        expected_units=25,
        weight=0.6,
    )
    _add_progress(app, assignment_id, users["intern_bob"], 10)
    _add_progress(app, assignment_id, users["intern_bob"], 5)

    response = client.get(
        f"/api/work/assignments/{assignment_id}/kpi",
        headers=auth_headers("intern_bob", "intern123"),
    )

    assert response.status_code == 200
    assert response.get_json()["kpi"] == {
        "expected_units": 25,
        "total_completed_units": 15,
        "completion_ratio": 0.6,
        "weighted_score": 0.36,
    }
    assert response.get_json()["capacity_risk"]["level"] in {"low", "medium", "high"}


def test_invalid_payloads_and_assignment_ids_are_rejected(client, auth_headers, users, app):
    admin_headers = auth_headers("admin", "admin123")

    bad_due_date = client.post(
        "/api/work/assignments",
        headers=admin_headers,
        json={
            "title": "Bad Due Date",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 10,
            "weight": 0.3,
            "due_date": "not-a-date",
        },
    )
    assert bad_due_date.status_code == 400
    assert "due_date" in bad_due_date.get_json()["error"]

    bad_expected_units = client.post(
        "/api/work/assignments",
        headers=admin_headers,
        json={
            "title": "Bad Units",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 0,
            "weight": 0.3,
        },
    )
    assert bad_expected_units.status_code == 400
    assert "expected_units" in bad_expected_units.get_json()["error"]

    missing_assignment_progress = client.post(
        "/api/work/assignments/9999/progress",
        headers=auth_headers("intern_bob", "intern123"),
        json={"completed_units": 1},
    )
    assert missing_assignment_progress.status_code == 404

    missing_assignment_kpi = client.get(
        "/api/work/assignments/9999/kpi",
        headers=admin_headers,
    )
    assert missing_assignment_kpi.status_code == 404


def test_compute_kpi_handles_zero_expected_units_and_over_completion(app, users):
    zero_assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Zero Target",
        expected_units=0,
        weight=0.9,
    )
    over_assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Over Completion",
        expected_units=5,
        weight=0.5,
    )
    _add_progress(app, over_assignment_id, users["intern_bob"], 7)

    with app.app_context():
        zero_assignment = db.session.get(WorkAssignment, zero_assignment_id)
        over_assignment = db.session.get(WorkAssignment, over_assignment_id)

        assert zero_assignment.compute_kpi() == {
            "expected_units": 0,
            "total_completed_units": 0,
            "completion_ratio": 0.0,
            "weighted_score": 0.0,
        }
        assert over_assignment.compute_kpi() == {
            "expected_units": 5,
            "total_completed_units": 7,
            "completion_ratio": 1.4,
            "weighted_score": 0.5,
        }


def test_overdue_assignment_is_high_capacity_risk(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        due_date=(datetime.now(UTC).date() - timedelta(days=1)),
        expected_units=20,
        weight=0.5,
    )

    response = client.get(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
    )

    assignment = next(item for item in response.get_json()["assignments"] if item["id"] == assignment_id)
    assert assignment["capacity_risk"]["level"] == "high"
    assert "Overdue and not completed." in assignment["capacity_risk"]["reasons"]


def test_due_soon_low_completion_and_no_recent_attendance_raise_risk(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["hr_jane"],
        assigned_to_user_id=users["intern_bob"],
        due_date=(datetime.now(UTC).date() + timedelta(days=2)),
        expected_units=10,
        weight=0.4,
    )
    _add_progress(app, assignment_id, users["intern_bob"], 2)
    _add_attendance(app, users["intern_bob"], days_ago=5)

    response = client.get(
        f"/api/work/assignments/{assignment_id}/kpi",
        headers=auth_headers("hr_jane", "hr123"),
    )

    risk = response.get_json()["capacity_risk"]
    assert risk["level"] == "high"
    assert "Due within 2 days with low completion." in risk["reasons"]
    assert "No recent attendance signal for assignee." in risk["reasons"]


def test_many_incomplete_assignments_raise_medium_risk(client, auth_headers, users, app):
    assignment_ids = [
        _create_assignment(
            app,
            assigned_by_user_id=users["admin"],
            assigned_to_user_id=users["intern_bob"],
            title=f"Assignment {index}",
            expected_units=10,
            weight=0.3,
            due_date=(datetime.now(UTC).date() + timedelta(days=10)),
        )
        for index in range(1, 4)
    ]
    _add_attendance(app, users["intern_bob"], days_ago=1)

    response = client.get(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
    )

    risky_assignments = [
        item for item in response.get_json()["assignments"]
        if item["id"] in assignment_ids
    ]
    assert len(risky_assignments) == 3
    for item in risky_assignments:
        assert item["capacity_risk"]["level"] == "medium"
        assert "Assignee has many active incomplete assignments." in item["capacity_risk"]["reasons"]


def test_legacy_datetime_due_date_rows_still_load_for_assignments_page(client, auth_headers, app):
    with app.app_context():
        db.session.execute(
            text(
                """
                INSERT INTO work_assignments
                (title, description, assigned_by_user_id, assigned_to_user_id, expected_units, weight, due_date, status, created_at, updated_at)
                VALUES
                (:title, :description, :assigned_by_user_id, :assigned_to_user_id, :expected_units, :weight, :due_date, :status, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            {
                "title": "Legacy Due Date Assignment",
                "description": "legacy row",
                "assigned_by_user_id": 1,
                "assigned_to_user_id": 3,
                "expected_units": 8,
                "weight": 0.5,
                "due_date": "2026-04-21T00:00:00",
                "status": "pending",
            },
        )
        db.session.commit()

    response = client.get(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
    )

    assert response.status_code == 200
    assignment = next(item for item in response.get_json()["assignments"] if item["title"] == "Legacy Due Date Assignment")
    assert assignment["due_date"] == "2026-04-21"


def test_work_board_requires_manager_role_and_maps_pending_to_todo(client, auth_headers, users, app):
    _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Board Assignment",
        expected_units=8,
    )

    denied = client.get(
        "/api/work/board",
        headers=auth_headers("intern_bob", "intern123"),
    )
    assert denied.status_code == 403

    response = client.get(
        "/api/work/board",
        headers=auth_headers("admin", "admin123"),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["columns"] == ["todo", "in_progress", "blocked", "completed"]
    assignment = next(item for item in body["assignments"] if item["title"] == "Board Assignment")
    assert assignment["status"] == "todo"


def test_manager_can_patch_assignment_status_and_board_preserves_blocked(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["hr_jane"],
        assigned_to_user_id=users["intern_bob"],
        title="Blocked Assignment",
        expected_units=10,
    )

    patch_response = client.patch(
        f"/api/work/assignments/{assignment_id}/status",
        headers=auth_headers("hr_jane", "hr123"),
        json={"status": "blocked"},
    )
    assert patch_response.status_code == 200
    assert patch_response.get_json()["assignment"]["status"] == "blocked"

    board_response = client.get(
        "/api/work/board",
        headers=auth_headers("admin", "admin123"),
    )
    board_assignment = next(item for item in board_response.get_json()["assignments"] if item["id"] == assignment_id)
    assert board_assignment["status"] == "blocked"

    invalid = client.patch(
        f"/api/work/assignments/{assignment_id}/status",
        headers=auth_headers("admin", "admin123"),
        json={"status": "pending"},
    )
    assert invalid.status_code == 400


def test_children_endpoint_returns_children_for_visible_assignment(client, auth_headers, users):
    parent = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Children Endpoint Parent",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 5,
            "weight": 0.5,
        },
    ).get_json()["assignment"]
    child = client.post(
        "/api/work/assignments",
        headers=auth_headers("admin", "admin123"),
        json={
            "title": "Children Endpoint Child",
            "assigned_to_user_id": users["intern_bob"],
            "expected_units": 3,
            "weight": 0.5,
            "parent_id": parent["id"],
        },
    ).get_json()["assignment"]

    response = client.get(
        f"/api/work/assignments/{parent['id']}/children",
        headers=auth_headers("intern_bob", "intern123"),
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["assignment"]["id"] == parent["id"]
    assert body["count"] == 1
    assert body["children"][0]["id"] == child["id"]


def test_admin_or_hr_can_create_escalation(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Escalation Target",
        expected_units=10,
    )

    response = client.post(
        "/api/work/escalations",
        headers=auth_headers("hr_jane", "hr123"),
        json={"assignment_id": assignment_id, "reason": "High risk workload needs attention"},
    )

    assert response.status_code == 201, response.get_json()
    body = response.get_json()["escalation"]
    assert body["assignment_id"] == assignment_id
    assert body["created_by_username"] == "hr_jane"
    assert body["reason"] == "High risk workload needs attention"
    assert body["status"] == "open"

    with app.app_context():
        escalation = db.session.query(WorkEscalation).filter_by(assignment_id=assignment_id).one()
        assert escalation.created_by_user_id == users["hr_jane"]
        assert escalation.status == "open"


def test_escalation_rejects_invalid_assignment(client, auth_headers):
    response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": 9999},
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Assignment not found"


def test_non_manager_cannot_create_escalation(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Unauthorized Escalation Target",
        expected_units=10,
    )

    response = client.post(
        "/api/work/escalations",
        headers=auth_headers("intern_bob", "intern123"),
        json={"assignment_id": assignment_id},
    )

    assert response.status_code == 403
    assert response.get_json()["error"] == "Manager access required"


def test_duplicate_open_escalation_is_rejected(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Duplicate Escalation Target",
        expected_units=10,
    )

    first = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "Initial escalation"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/work/escalations",
        headers=auth_headers("hr_jane", "hr123"),
        json={"assignment_id": assignment_id, "reason": "Duplicate escalation"},
    )
    assert second.status_code == 400
    assert second.get_json()["error"] == "An open escalation already exists for this assignment"


def test_escalation_list_and_resolve_work_for_manager(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Resolve Escalation Target",
        expected_units=10,
    )

    create_response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "Needs review"},
    )
    escalation_id = create_response.get_json()["escalation"]["id"]

    list_response = client.get(
        "/api/work/escalations",
        headers=auth_headers("hr_jane", "hr123"),
    )
    assert list_response.status_code == 200
    escalation = next(item for item in list_response.get_json()["escalations"] if item["id"] == escalation_id)
    assert escalation["assignment"]["title"] == "Resolve Escalation Target"
    assert escalation["status"] == "open"

    resolve_response = client.patch(
        f"/api/work/escalations/{escalation_id}",
        headers=auth_headers("hr_jane", "hr123"),
        json={"status": "resolved"},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.get_json()["escalation"]["status"] == "resolved"


def test_escalation_patch_rejects_invalid_status_and_already_resolved(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Escalation Patch Validation",
        expected_units=9,
    )

    create_response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "Validation target"},
    )
    escalation_id = create_response.get_json()["escalation"]["id"]

    invalid_status_response = client.patch(
        f"/api/work/escalations/{escalation_id}",
        headers=auth_headers("admin", "admin123"),
        json={"status": "open"},
    )
    assert invalid_status_response.status_code == 400
    assert invalid_status_response.get_json()["error"] == "Only resolution to 'resolved' is supported"

    first_resolve = client.patch(
        f"/api/work/escalations/{escalation_id}",
        headers=auth_headers("admin", "admin123"),
        json={"status": "resolved"},
    )
    assert first_resolve.status_code == 200

    second_resolve = client.patch(
        f"/api/work/escalations/{escalation_id}",
        headers=auth_headers("admin", "admin123"),
        json={"status": "resolved"},
    )
    assert second_resolve.status_code == 400
    assert second_resolve.get_json()["error"] == "Escalation is already resolved"


def test_escalation_suggestion_returns_normalized_contract(client, auth_headers, users, app, monkeypatch):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="AI Suggestion Target",
        expected_units=10,
    )

    monkeypatch.setattr(
        "app.routes.work_management.get_ai_json_response",
        lambda *args, **kwargs: {
            "reason": "Staffing shortage",
            "severity": "urgent",
            "impact": "late",
            "summary": "Two employees are absent and work may slip.",
            "suggestion": "Reassign one active task and review the deadline.",
            "affected_assignment_ids": [assignment_id, 9999],
            "draft_details": "Escalating because staffing shortage may delay ticket completion.",
        },
    )

    response = client.post(
        "/api/work/escalations/suggest",
        headers=auth_headers("admin", "admin123"),
        json={
            "message": "2 employees are absent today, we can’t complete tickets",
            "assignment_ids": [assignment_id],
            "include_team_context": True,
        },
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert set(body) == {
        "reason",
        "severity",
        "impact",
        "summary",
        "suggestion",
        "affected_assignment_ids",
        "draft_details",
        "affected_assignments",
    }
    assert body["reason"] == "Staffing shortage"
    assert body["severity"] == "medium"
    assert body["impact"] == "delay"
    assert body["affected_assignment_ids"] == [assignment_id]
    assert body["affected_assignments"][0]["id"] == assignment_id


def test_escalation_suggestion_uses_deterministic_fallback_on_ai_failure(client, auth_headers, users, app, monkeypatch):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Fallback Suggestion Target",
        expected_units=10,
    )

    def failing_ai(*args, **kwargs):
        raise RuntimeError("ollama unavailable")

    monkeypatch.setattr("app.routes.work_management.get_ai_json_response", failing_ai)

    response = client.post(
        "/api/work/escalations/suggest",
        headers=auth_headers("hr_jane", "hr123"),
        json={
            "message": "2 employees are absent today, we can’t complete tickets",
            "assignment_ids": [assignment_id],
        },
    )

    assert response.status_code == 200, response.get_json()
    body = response.get_json()
    assert body["reason"] == "Operational risk detected"
    assert body["impact"] == "delay"
    assert body["affected_assignment_ids"] == [assignment_id]
    assert body["affected_assignments"][0]["title"] == "Fallback Suggestion Target"


def test_non_manager_cannot_list_or_resolve_escalations(client, auth_headers, users, app):
    assignment_id = _create_assignment(
        app,
        assigned_by_user_id=users["admin"],
        assigned_to_user_id=users["intern_bob"],
        title="Unauthorized Escalation Management",
        expected_units=10,
    )
    create_response = client.post(
        "/api/work/escalations",
        headers=auth_headers("admin", "admin123"),
        json={"assignment_id": assignment_id, "reason": "Needs manager view"},
    )
    escalation_id = create_response.get_json()["escalation"]["id"]

    denied_list = client.get(
        "/api/work/escalations",
        headers=auth_headers("intern_bob", "intern123"),
    )
    assert denied_list.status_code == 403

    denied_patch = client.patch(
        f"/api/work/escalations/{escalation_id}",
        headers=auth_headers("intern_bob", "intern123"),
        json={"status": "resolved"},
    )
    assert denied_patch.status_code == 403
