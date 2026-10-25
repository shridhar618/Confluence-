from app import db
from app.models.project import Project
from app.models.work_assignment import WorkAssignment


def _create_project(app, name="Platform Upgrade", description="Project workspace"):
    with app.app_context():
        project = Project(name=name, description=description)
        db.session.add(project)
        db.session.commit()
        db.session.refresh(project)
        return project.id


def test_manager_can_create_project_and_manage_members(client, auth_headers, app, users):
    create_response = client.post(
        "/api/projects",
        headers=auth_headers("admin", "admin123"),
        json={"name": "AI Operations", "description": "Generated work stream"},
    )
    assert create_response.status_code == 201, create_response.get_json()
    project = create_response.get_json()["project"]
    assert project["name"] == "AI Operations"
    assert project["is_archived"] is False

    member_response = client.post(
        f"/api/projects/{project['id']}/members",
        headers=auth_headers("hr_jane", "hr123"),
        json={"user_id": users["intern_bob"]},
    )
    assert member_response.status_code == 201, member_response.get_json()
    assert member_response.get_json()["membership"]["user"]["username"] == "intern_bob"

    archive_response = client.patch(
        f"/api/projects/{project['id']}",
        headers=auth_headers("admin", "admin123"),
        json={"is_archived": True},
    )
    assert archive_response.status_code == 200
    assert archive_response.get_json()["project"]["is_archived"] is True

    with app.app_context():
        stored_project = db.session.get(Project, project["id"])
        assert stored_project.is_archived is True
        member_ids = {member.id for member in stored_project.members}
        assert member_ids == {users["intern_bob"]}


def test_assignments_can_be_filtered_by_project(client, auth_headers, app, users):
    project_id = _create_project(app)

    with app.app_context():
        db.session.add_all([
            WorkAssignment(
                project_id=project_id,
                title="Scoped Task",
                assigned_by_user_id=users["admin"],
                assigned_to_user_id=users["intern_bob"],
                expected_units=5,
                weight=0.5,
                status="todo",
            ),
            WorkAssignment(
                title="Unscoped Task",
                assigned_by_user_id=users["admin"],
                assigned_to_user_id=users["intern_bob"],
                expected_units=3,
                weight=0.4,
                status="todo",
            ),
        ])
        db.session.commit()

    response = client.get(
        f"/api/work/assignments?project_id={project_id}",
        headers=auth_headers("admin", "admin123"),
    )

    assert response.status_code == 200
    assignments = response.get_json()["assignments"]
    assert len(assignments) == 1
    assert assignments[0]["title"] == "Scoped Task"
    assert assignments[0]["project"]["id"] == project_id
