from pydantic import BaseModel

class Payment(BaseModel):
    id: int
    payment_method: str
    amount: float

class RefundRequest(BaseModel):
    payment_id: int
    amount: float