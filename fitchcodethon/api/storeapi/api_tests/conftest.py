# pytest fixture file - allows the sharing of data between multiple tests
import os
from typing import Generator, AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport, Request, Response

# make sure that the tests use the test database
# doing this effectively overwrites the value of ENV_STATE as read from the .env file
os.environ["ENV_STATE"] = "test"
from storeapi.database import database  # noqa: E402
from storeapi.main import app  # noqa: E402


# with scope set to session the fixture will only run once before all tests are executed
# this tells the pytest framework to use the built-in asyncio framework to run async tests
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def api_test_client() -> Generator:
    yield TestClient(app)


# with autouse set to true the fixture runs before each test
# and means that the db fixture need not be specified as a dependency injected parameter for
# each test fixture
@pytest.fixture(autouse=True)
async def db() -> AsyncGenerator:

    # db startup goes here
    await database.connect()
    print("Starting up database connection...")
    yield
    await database.disconnect()


# with pytest, the test framework will dependency inject the api_test_client fixture into this fixture
# so fixtures can be composed with eachother
@pytest.fixture()
async def async_api_test_client(api_test_client: TestClient) -> AsyncGenerator:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=api_test_client.base_url
    ) as client:
        yield client
