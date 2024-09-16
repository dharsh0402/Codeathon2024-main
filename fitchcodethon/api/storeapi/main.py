from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.exception_handlers import http_exception_handler
from storeapi.routers.user_routes import router as user_router

# from typing import List
from storeapi.routers.campaign import router as campaign_router
from storeapi.database import database
from asgi_correlation_id import CorrelationIdMiddleware

from storeapi.logging_conf import configure_logging

import logging

logger = logging.getLogger(__name__)


# Set up the asyn connection to the database before serving any requests
# the asyncontextmanager is a function that does some setup and teardown
# this function sets up the db connection and then pauses execution (yield statement) and hands over
# execution to the caller until the calling function (FastAPI) tells it to continue
@asynccontextmanager
async def lifespan(app: FastAPI):
    # configure logging before any other activity
    configure_logging()
    logger.info("Logging setup completed")
    # db startup goes here
    await database.connect()
    # print("Starting up database connection...")
    yield
    await database.disconnect()


# call the startup (setup) function before serving any requests, i.e. lifespan
app = FastAPI(lifespan=lifespan)
# add the correlation id middleware to the app
# this middleware helps to group logs by request and is useful to track parallel requests
app.add_middleware(CorrelationIdMiddleware)

app.include_router(campaign_router)
app.include_router(user_router)



# add a global HTTPException handler for the API
@app.exception_handler(HTTPException)
async def http_exception_handle_logging(request, exc: HTTPException):
    logger.error(f"HttpException: {exc.status_code} {exc.detail}")
    return await http_exception_handler(request, exc)






