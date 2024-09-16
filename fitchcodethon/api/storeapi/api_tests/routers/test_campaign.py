import pytest
from httpx import AsyncClient
from storeapi.main import app
from storeapi.security import valid_access_token


@pytest.fixture(autouse=True)
def access_token():
    # Mock the token data
    token_data = {"resource_access": {"elbaapi": {"roles": ["admin"]}}}

    # Mock the valid_access_token dependency
    app.dependency_overrides[valid_access_token] = lambda: token_data


@pytest.fixture
async def create_campaign(async_api_test_client: AsyncClient) -> dict:
    # Define the campaign data
    campaign_data = {
        "name": "New Campaign",
        "template": "asdf",
        "isDraft": True,
        "isPublished": False,
        "isEnded": False,
    }

    response = await async_api_test_client.post("/admin/campaign", json=campaign_data)
    print(response.json())
    return response.json()


@pytest.mark.anyio
async def test_create_campaign(async_api_test_client: AsyncClient):

    # Define the campaign data
    campaign_data = {
        "name": "New Campaign",
        "template": "asdf",
        "isDraft": True,
        "isPublished": False,
        "isEnded": False,
    }

    response = await async_api_test_client.post("/admin/campaign", json=campaign_data)

    responseJson = response.json()
    assert response.status_code == 201
    assert response.json()["name"] == "New Campaign"
    print(response.json()["id"])
    assert responseJson["id"] is not None
    assert responseJson["template"] == "asdf"
    assert responseJson["isDraft"] is True
    assert responseJson["isPublished"] is False
    assert responseJson["isEnded"] is False


@pytest.mark.anyio
async def test_create_campaign_duplicate_name(
    create_campaign: dict, async_api_test_client: AsyncClient
):

    # Define the campaign data
    campaign_data = create_campaign
    campaign_name = campaign_data["name"]

    response = await async_api_test_client.post("/admin/campaign", json=campaign_data)

    responseJson = response.json()
    assert response.status_code == 400
    assert (
        responseJson["detail"] == f"Campaign with name {campaign_name} already exists"
    )


@pytest.mark.anyio
async def test_campaign_can_only_be_in_one_state(
    create_campaign: dict, async_api_test_client: AsyncClient
):

    # Define the campaign data
    campaign_data = create_campaign
    campaign_data["isDraft"] = True
    campaign_data["isPublished"] = True

    print(campaign_data)
    campaign_id = campaign_data["id"]

    response = await async_api_test_client.patch(
        f"/admin/campaign/{campaign_id}", json=campaign_data
    )

    responseJson = response.json()
    assert response.status_code == 400
    assert responseJson["detail"] == "Exactly one state must be selected"
