from pydantic import BaseModel, ConfigDict
from typing import List


class CampaignIn(BaseModel):
    name: str
    template: str
    isDraft: bool = True
    isPublished: bool = False
    isEnded: bool = False


class Campaign(CampaignIn):
    # model_config instructs pydantic how to deal with SQLAlchemy objects returned from DB queries
    model_config = ConfigDict(from_attributes=True)
    id: int
