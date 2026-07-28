import pytest
from httpx import AsyncClient
from models.namespace import Namespace
from sqlalchemy.ext.asyncio import AsyncSession
from core.auth import CLERK_NAMESPACE_ID

@pytest.mark.asyncio
async def test_create_api_key(client: AsyncClient, db_session: AsyncSession):
    # 1) create a namespace via the API
    response = await client.post("/v1/api/admin/namespaces", json={
        "name": "test_namespace_api_key",
        "storage_quota_bytes": 1000
    })
    assert response.status_code == 201
    data = response.json()
    ns_id = data["id"]
    
    # 2) Try to regenerate the API key
    regen_response = await client.post(f"/v1/api/admin/namespaces/{ns_id}/api-key")
    assert regen_response.status_code == 200
    regen_data = regen_response.json()
    assert "api_key" in regen_data
    assert regen_data["api_key"].startswith("frax_")
    
    # 3) New api_key should be different from the first one
    assert regen_data["api_key"] != data["api_key"]

@pytest.mark.asyncio
async def test_delete_api_key(client: AsyncClient, db_session: AsyncSession):
    # 1) create a namespace via the API
    response = await client.post("/v1/api/admin/namespaces", json={
        "name": "test_namespace_delete_key",
        "storage_quota_bytes": 1000
    })
    assert response.status_code == 201
    ns_id = response.json()["id"]
    
    # 2) delete the API key
    del_response = await client.delete(f"/v1/api/admin/namespaces/{ns_id}/api-key")
    assert del_response.status_code == 204
    
    # 3) verify in DB
    result = await db_session.execute(
        from_sqlalchemy_select := __import__("sqlalchemy").select(Namespace).where(Namespace.id == ns_id)
    )
    ns = result.scalar_one()
    assert ns.api_key_hash is None

@pytest.mark.asyncio
async def test_api_key_access_denied(client: AsyncClient, db_session: AsyncSession):
    # 1) create a namespace directly in DB belonging to another user
    other_ns = Namespace(
        name="other_user_ns",
        author_id="different_user",
        api_key_hash="somehash"
    )
    db_session.add(other_ns)
    await db_session.commit()
    await db_session.refresh(other_ns)
    
    # 2) try to regenerate key for someone else's namespace
    regen_response = await client.post(f"/v1/api/admin/namespaces/{other_ns.id}/api-key")
    assert regen_response.status_code == 404
    
    # 3) try to delete key for someone else's namespace
    del_response = await client.delete(f"/v1/api/admin/namespaces/{other_ns.id}/api-key")
    assert del_response.status_code == 404
