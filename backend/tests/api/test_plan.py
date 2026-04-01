import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from sqlmodel import Session
from app.models.user import User
from app.models.plan import PlanHeader, PlanMilestone, PlanTask

from datetime import datetime

@patch("app.api.plan.agent_client.execute_task", new_callable=AsyncMock)
def test_generate_plan(mock_execute, authenticated_client: TestClient):
    mock_execute.return_value = {
        "goal_analysis": {"deadline_date": "2024-12-31"},
        "generated_plan": {
            "estimated_total_hours": 10.0,
            "difficulty_coef": 1.0,
            "milestones": [
                {
                    "title": "M1",
                    "deadline": "2024-12-01T00:00:00",
                    "tasks": [{"title": "T1", "type": "reading", "estimated_min": 30}]
                }
            ]
        }
    }
    
    response = authenticated_client.post("/api/v1/plans/generate?goal_text=learn")
    assert response.status_code == 200
    data = response.json()
    assert data["goal"] == "learn"
    assert len(data["milestones"]) == 1

def test_create_plan(authenticated_client: TestClient, session: Session):
    # mock execution inside plan service or fix model mapping 
    with patch("app.api.plan.PlanHeader.from_orm") as mock_from_orm:
        mock_from_orm.return_value = PlanHeader(plan_id=1, goal="learn", user_id=1, estimated_hours=10.0, deadline=datetime.now())
        with patch.object(Session, "add"), patch.object(Session, "commit"), patch.object(Session, "refresh"):
            response = authenticated_client.post(
                "/api/v1/plans/",
                json={
                    "user_id": 1,
                    "goal": "learn",
                    "deadline": "2024-12-31T00:00:00",
                    "estimated_hours": 10.0,
                    "difficulty_coef": 1.0,
                    "milestones": []
                }
            )
            assert response.status_code == 200
            assert response.json()["goal"] == "learn"

def test_list_plans(authenticated_client: TestClient, session: Session, mock_user: User):
    p = PlanHeader(user_id=mock_user.id, goal="test goal", estimated_hours=10.0, deadline=datetime.now())
    session.add(p)
    session.commit()

    response = authenticated_client.get("/api/v1/plans/")
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_get_plan(authenticated_client: TestClient, session: Session, mock_user: User):
    p = PlanHeader(user_id=mock_user.id, goal="test goal", estimated_hours=10.0, deadline=datetime.now())
    session.add(p)
    session.commit()
    session.refresh(p)

    m = PlanMilestone(plan_id=p.plan_id, title="M1", deadline=datetime.now())
    session.add(m)
    session.commit()

    response = authenticated_client.get(f"/api/v1/plans/{p.plan_id}")
    assert response.status_code == 200
    assert response.json()["goal"] == "test goal"
    assert len(response.json()["milestones"]) >= 1

def test_get_plan_not_found(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/plans/9999")
    assert response.status_code == 404
