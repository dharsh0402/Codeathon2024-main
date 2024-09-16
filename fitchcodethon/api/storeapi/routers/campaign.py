from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Annotated

from storeapi.database import database, campaign_table
import logging
import sqlalchemy
from enum import Enum


from storeapi.security import (
    has_role,
)

from storeapi.models.campaign import Campaign, CampaignIn

router = APIRouter()

logger = logging.getLogger(__name__)


async def find_campaign(campaign_name: str) -> Campaign:
    logger.info(f"Finding campaign with name {campaign_name}")
    query = campaign_table.select().where(campaign_table.c.name == campaign_name)
    logger.debug(query)
    campaign = await database.fetch_one(query)
    return campaign


async def find_campaign_id(campaign_id: int) -> Campaign:
    logger.info(f"Finding campaign with Id {campaign_id}")
    query = campaign_table.select().where(campaign_table.c.id == campaign_id)
    logger.debug(query)
    campaign = await database.fetch_one(query)
    return campaign


# # ---


# @router.get("/private", dependencies=[Depends(valid_access_token)])
# def read_item():
#     return {"message": "This message is private"}


# @router.get("/public")
# def get_public():
#     return {"message": "This endpoint is public"}


# @router.get("/admin", dependencies=[Depends(has_role("admin"))])
# def get_private():
#     return {"message": "Admin only"}


@router.post(
    "/admin/campaign",
    response_model=Campaign,
    status_code=201,
    dependencies=[Depends(has_role("admin"))],
)
async def create_campaign(campaign: CampaignIn) -> Campaign:
    logger.info("Creating a new campaign")
    data = {**campaign.model_dump()}
    existing_campaign = await find_campaign(data["name"])
    if existing_campaign:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign with name {campaign.name} already exists",
        )

    if not campaign.isDraft or (campaign.isPublished or campaign.isEnded):
        raise HTTPException(
            status_code=400,
            detail=f"Campaign needs to be a Draft",
        )

    query = campaign_table.insert().values(data)
    logger.debug(query)
    campaign_id = await database.execute(query)
    created_campaign = {**data, "id": campaign_id}
    return created_campaign


class CampaignState(str, Enum):
    draft = "draft"
    published = "published"
    ended = "ended"
    all = "all"


@router.get(
    "/admin/campaign",
    response_model=List[Campaign],
    dependencies=[Depends(has_role("admin"))],
)
async def get_campaigns(
    campaign_state: CampaignState = CampaignState.all,
) -> List[Campaign]:
    logger.info(f"Getting {campaign_state} campaigns")

    match campaign_state:
        case CampaignState.all:
            query = campaign_table.select()
        case CampaignState.ended:
            query = campaign_table.select().where(campaign_table.c.isEnded == True)
        case CampaignState.draft:
            query = campaign_table.select().where(campaign_table.c.isDraft == True)
        case CampaignState.published:
            query = campaign_table.select().where(campaign_table.c.isPublished == True)

    logger.debug(query)
    campaigns = await database.fetch_all(query)
    return campaigns


@router.get(
    "/admin/campaign/{campaign_id}",
    response_model=Campaign,
    dependencies=[Depends(has_role("admin"))],
)
async def get_campaign(campaign_id: int) -> Campaign:
    logger.info(f"Getting campaign with id {campaign_id}")
    campaign = await find_campaign_id(campaign_id=campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=404, detail=f"Campaign with Id {campaign_id} not found"
        )
    return campaign


@router.patch(
    "/admin/campaign/{campaign_id}",
    response_model=Campaign,
    dependencies=[Depends(has_role("admin"))],
)
async def update_campaign(campaign_id: int, campaign: CampaignIn) -> Campaign:
    logger.info(f"Updating campaign with id {campaign_id}")

    existing_campaign = await find_campaign_id(campaign_id=campaign_id)
    if not existing_campaign:
        raise HTTPException(
            status_code=404, detail=f"Campaign with Id {campaign_id} not found"
        )

    duplicate_campaign = await find_campaign(campaign.name)
    if duplicate_campaign and duplicate_campaign.id != campaign_id:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign with name {campaign.name} already exists",
        )

    selected_states = [
        campaign.isDraft,
        campaign.isPublished,
        campaign.isEnded,
    ]

    if selected_states.count(True) != 1:
        raise HTTPException(
            status_code=400, detail=f"Exactly one state must be selected"
        )

    # cannot end draft campaigns
    if existing_campaign.isDraft and (campaign.isEnded):
        raise HTTPException(
            status_code=400, detail=f"Campaign: {campaign_id} is a draft"
        )

    if existing_campaign.isPublished and (campaign.isDraft):
        raise HTTPException(
            status_code=400, detail=f"Campaign: {campaign_id} is published"
        )

    # ended campaigns is an end state
    if existing_campaign.isEnded:
        raise HTTPException(
            status_code=400, detail=f"Campaign: {campaign_id} has ended"
        )

    data = {**campaign.model_dump()}

    if existing_campaign.isDraft:
        query = (
            campaign_table.update()
            .where(
                sqlalchemy.and_(
                    campaign_table.c.id == campaign_id,
                    campaign_table.c.isDraft == True,
                )
            )
            .values(data)
        )

    if existing_campaign.isPublished:
        query = (
            campaign_table.update()
            .where(
                sqlalchemy.and_(
                    campaign_table.c.id == campaign_id,
                    campaign_table.c.isPublished == True,
                )
            )
            .values({"isPublished": data["isPublished"], "isEnded": data["isEnded"]})
        )

    logger.debug(query)
    await database.execute(query)
    updated_campaign = await get_campaign(campaign_id)  # {**data, "id": campaign_id}
    return updated_campaign


@router.delete(
    "/admin/campaign/{campaign_id}",
    dependencies=[Depends(has_role("admin"))],
)
async def delete_campaign(campaign_id: int) -> None:
    logger.info(f"Deleting campaign with id {campaign_id}")
    existing_campaign = await find_campaign_id(campaign_id=campaign_id)
    if not existing_campaign:
        raise HTTPException(
            status_code=404, detail=f"Campaign with Id {campaign_id} not found"
        )

    if not existing_campaign.isDraft:
        raise HTTPException(
            status_code=400, detail=f"Campaign with Id {campaign_id} is not a draft"
        )

    query = campaign_table.delete().where(campaign_table.c.id == campaign_id)
    logger.debug(query)
    await database.execute(query)


@router.get("/public/campaign", response_model=List[Campaign])
async def get_published_campaigns() -> List[Campaign]:
    logger.info("Getting published campaigns")
    campaigns = await get_campaigns(CampaignState.published)
    return campaigns


@router.get("/public/campaign/{campaign_id}", response_model=Campaign)
async def get_published_campaign(campaign_id: int) -> Campaign:
    logger.info(f"Getting campaign with id {campaign_id}")
    campaign = await find_campaign_id(campaign_id=campaign_id)

    if not campaign:
        raise HTTPException(
            status_code=404, detail=f"Campaign with Id {campaign_id} not found"
        )

    if not campaign.isPublished:
        raise HTTPException(
            status_code=400, detail=f"Campaign with Id {campaign_id} is not published"
        )
    return campaign
