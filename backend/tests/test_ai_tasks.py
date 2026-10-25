from app import db
from app.models.project import Project
from app.models.work_assignment import WorkAssignment


def _create_project(app, name="AI Delivery", description="LLM-generated backlog"):
    with app.app_context():
        project = Project(name=name, description=description)
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)
        return project.id


def test_work_assignment_model_exposes_project_and_github_fields(app, users):
    project_id = _create_project(app)

    with app.app_context():
        assignment = WorkAssignment(
            project_id=project_id,
            title="Draft task",
            description="Generated from a prompt",
            assigned_by_user_id=users["admin"],
            assigned_to_user_id=users["intern_bob"],
            expected_units=8,
            weight=0.5,
            github_issue_id="123",
            github_branch="feature/ai-draft-task",
        )
        db.session.add(assignment)
        db.session.commit()
        db.session.refresh(assignment)

        payload = assignment.to_dict()
        assert payload["project_id"] == project_id
        assert payload["github_issue_id"] == "123"
        assert payload["github_branch"] == "feature/ai-draft-task"
        assert payload["status"] == "draft"


def test_ai_generated_tasks_are_saved_as_drafts_and_listed_as_pending(client, auth_headers, app, users):
    project_id = _create_project(app)

    response = client.post(
        f"/api/projects/{project_id}/tasks/ai-generate",
        headers=auth_headers("admin", "admin123"),
        json=[
            {
                "title": "Create parser",
                "description": "Build the ingestion parser",
                "assigned_to_user_id": users["intern_bob"],
                "expected_units": 5,
                "weight": 0.4,
                "github_issue_id": "GH-1",
                "github_branch": "feature/parser",
            },
            {
                "title": "Add approval UI contract",
                "assigned_to_user_id": users["intern_bob"],
                "expected_units": 3,
                "weight": 0.2,
            },
        ],
    )

    assert response.status_code == 201, response.get_json()
    body = response.get_json()
    assert body["count"] == 2
    assert all(task["status"] == "draft" for task in body["tasks"])
    assert all(task["project_id"] == project_id for task in body["tasks"])

    pending = client.get(
        f"/api/projects/{project_id}/tasks/pending",
        headers=auth_headers("hr_jane", "hr123"),
    )
    assert pending.status_code == 200
    pending_body = pending.get_json()
    assert pending_body["count"] == 2
    assert {task["title"] for task in pending_body["tasks"]} == {
        "Create parser",
        "Add approval UI contract",
    }


def test_approving_draft_tasks_moves_them_to_todo_and_hides_drafts_from_assignee_lists(client, auth_headers, app, users):
    project_id = _create_project(app)

    create_response = client.post(
        f"/api/projects/{project_id}/tasks/ai-generate",
        headers=auth_headers("admin", "admin123"),
        json=[
            {"title": "Draft task 1", "assigned_to_user_id": users["intern_bob"], "expected_units": 2},
            {"title": "Draft task 2", "assigned_to_user_id": users["intern_bob"], "expected_units": 2},
        ],
    )
    task_ids = [task["id"] for task in create_response.get_json()["tasks"]]

    my_work_before = client.get(
        "/api/work/assignments",
        headers=auth_headers("intern_bob", "intern123"),
    )
    assert my_work_before.status_code == 200
    assert all(task["id"] not in task_ids for task in my_work_before.get_json()["assignments"])

    approve_response = client.post(
        f"/api/projects/{project_id}/tasks/approve",
        headers=auth_headers("admin", "admin123"),
        json=task_ids,
    )
    assert approve_response.status_code == 200, approve_response.get_json()
    assert all(task["status"] == "todo" for task in approve_response.get_json()["tasks"])

    my_work_after = client.get(
        "/api/work/assignments",
        headers=auth_headers("intern_bob", "intern123"),
    )
    assert my_work_after.status_code == 200
    visible_ids = {task["id"] for task in my_work_after.get_json()["assignments"]}
    assert set(task_ids).issubset(visible_ids)
