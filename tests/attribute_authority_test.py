from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from attribute_authority.api.dependencies import optional_user_claims
from attribute_authority.db.session import get_async_db
from attribute_authority.main import app


async def _override_db():
	yield object()


@pytest.fixture
def client():
	app.dependency_overrides = {}
	with TestClient(app) as test_client:
		yield test_client
	app.dependency_overrides = {}


def test_openapi_keeps_json_api_and_excludes_ui_routes(client):
	response = client.get("/api/v1/openapi.json")

	assert response.status_code == 200
	paths = response.json()["paths"]

	assert "/api/v1/definitions/{attribute_id}" in paths
	assert "/api/v1/privileges/{privilege_id}" in paths
	assert "/admin/users" not in paths
	assert "/login" not in paths
	assert "/auth/authorize/{provider}" not in paths
	assert "/api/v1/invitations/{invitation_hash}/accept" not in paths
	assert "/api/v1/invitations/{invitation_hash}/confirm" not in paths


def test_login_page_renders_provider_links(client, monkeypatch):
	monkeypatch.setattr(
		"attribute_authority.web.routes.providers",
		["demo-op"],
	)

	response = client.get("/login?next=/admin/users")

	assert response.status_code == 200
	assert "Continue with demo-op" in response.text
	assert "/auth/authorize/demo-op?next=%2Fadmin%2Fusers" in response.text


def test_my_attributes_redirects_when_logged_out(client):
	app.dependency_overrides[get_async_db] = _override_db

	response = client.get("/me/attributes", follow_redirects=False)

	assert response.status_code == 302
	assert response.headers["location"].endswith("/login?next=%2Fme%2Fattributes")


def test_my_attributes_page_renders_with_claims(client, monkeypatch):
	async def _claims_override():
		return {
			"sub": "subject-1",
			"iss": "issuer-1",
			"name": "Taylor Example",
			"email": "taylor@example.org",
		}

	async def _get_user_by_claims(_db, _sub, _iss):
		return SimpleNamespace(
			id=1,
			sub="subject-1",
			iss="issuer-1",
			name="Taylor Example",
			email="taylor@example.org",
		)

	async def _get_user_attributes(_db, _sub, _iss):
		return {
			"eduPersonAffiliation": [{"id": 1, "value": "staff"}],
			"group": [{"id": 2, "value": "research"}],
		}

	app.dependency_overrides[get_async_db] = _override_db
	app.dependency_overrides[optional_user_claims] = _claims_override
	monkeypatch.setattr(
		"attribute_authority.web.routes.users.get_by_sub_and_iss",
		_get_user_by_claims,
	)
	monkeypatch.setattr(
		"attribute_authority.web.routes.user_attributes.get_user_attributes",
		_get_user_attributes,
	)

	response = client.get("/me/attributes")

	assert response.status_code == 200
	assert "Manage Invitations" in response.text
	assert "eduPersonAffiliation" in response.text
	assert "research" in response.text


def test_invitation_accept_redirects_to_login_when_logged_out(client, monkeypatch):
	async def _claims_override():
		return None

	invitation = SimpleNamespace(
		hash="invite-123",
		group_key="entitlement",
		group_value="urn:example:group",
		max_uses=3,
		current_uses=0,
		expires_at="2030-01-01T00:00:00+00:00",
		status="active",
		invited_user_sub=None,
		invited_user_iss=None,
	)

	async def _get_invitation(_db, _hash):
		return invitation

	app.dependency_overrides[get_async_db] = _override_db
	app.dependency_overrides[optional_user_claims] = _claims_override
	monkeypatch.setattr(
		"attribute_authority.web.routes.invitation_service.get_by_hash",
		_get_invitation,
	)
	monkeypatch.setattr(
		"attribute_authority.web.routes.invitation_service.check_invitation_valid",
		lambda _invitation: True,
	)

	response = client.get("/invitations/invite-123/accept", follow_redirects=False)

	assert response.status_code == 302
	assert response.headers["location"].endswith(
		"/login?next=%2Finvitations%2Finvite-123%2Faccept"
	)
