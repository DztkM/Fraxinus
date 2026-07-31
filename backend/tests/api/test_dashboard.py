import pytest
from httpx import AsyncClient
from models.namespace import Namespace
from models.api_key import NamespaceAPIKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, db_session: AsyncSession):
    # 1) create a namespace via the API
    response = await client.post("/v1/api/dashboard/namespaces", json={
        "name": "test_namespace_api_key",
        "storage_quota_bytes": 1000
    })
    assert response.status_code == 201
    data = response.json()
    ns_id = data["id"]
    
    # 2) create an API key
    regen_response = await client.post("/v1/api/dashboard/api-key", json={"name": "test key", "namespace_id": ns_id})
    assert regen_response.status_code == 200
    regen_data = regen_response.json()
    assert "api_key" in regen_data
    assert regen_data["api_key"].startswith("frax_")
    assert regen_data["name"] == "test key"
    
    # 3) create a second api_key
    regen_response_2 = await client.post("/v1/api/dashboard/api-key", json={"name": "test key 2", "namespace_id": ns_id})
    assert regen_response_2.status_code == 200
    regen_data_2 = regen_response_2.json()
    assert regen_data_2["api_key"] != regen_data["api_key"]

@pytest.mark.asyncio
async def test_delete_api_key(client: AsyncClient, db_session: AsyncSession):
    # 1) create a namespace via the API
    response = await client.post("/v1/api/dashboard/namespaces", json={
        "name": "test_namespace_delete_key",
        "storage_quota_bytes": 1000
    })
    assert response.status_code == 201
    ns_id = response.json()["id"]
    
    # 2) create a key
    regen_response = await client.post("/v1/api/dashboard/api-key", json={"name": "test key", "namespace_id": ns_id})
    assert regen_response.status_code == 200
    key_id = regen_response.json()["id"]

    # 3) delete the API key
    del_response = await client.delete(f"/v1/api/dashboard/api-key/{key_id}")
    assert del_response.status_code == 204
    
    # 4) verify in DB
    result = await db_session.execute(select(NamespaceAPIKey).where(NamespaceAPIKey.id == key_id))
    key = result.scalar_one_or_none()
    assert key is None

@pytest.mark.asyncio
async def test_api_key_access_denied(client: AsyncClient, db_session: AsyncSession):
    # 1) create a namespace directly in DB belonging to another user
    other_ns = Namespace(
        name="other_user_ns",
        author_id="different_user"
    )
    db_session.add(other_ns)
    await db_session.commit()
    await db_session.refresh(other_ns)
    
    # 2) try to generate key for someone else's namespace
    regen_response = await client.post("/v1/api/dashboard/api-key", json={"name": "test key", "namespace_id": str(other_ns.id)})
    assert regen_response.status_code == 404
    
    # 3) try to delete a random key ID for someone else's namespace (would be 404 since it's random)
    import uuid
    del_response = await client.delete(f"/v1/api/dashboard/api-key/{uuid.uuid4()}")
    assert del_response.status_code == 404
