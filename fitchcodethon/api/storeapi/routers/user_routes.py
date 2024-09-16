from fastapi import APIRouter, HTTPException, Depends
from storeapi.database import database, users,refund_requests, store_payment, payments
from storeapi.paypal_integration.paypal import process_paypal_refund
from storeapi.security import (
    verify_password, 
    create_access_token, 
    get_password_hash,
    has_role
)
from storeapi.models.user import UserIn, User, UserLogin
from storeapi.models.payment import Payment, RefundRequest
from storeapi.paypal_integration.paypal import fetch_paypal_token, create_paypal_payment  # PayPal Integration
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

async def find_user_by_email(email: str) -> User:
    query = users.select().where(users.c.email == email)
    user = await database.fetch_one(query)
    return user

async def find_user_by_id(user_id: int) -> User:
    query = users.select().where(users.c.id == user_id)
    user = await database.fetch_one(query)
    return user

# User Registration
@router.post("/user/register", response_model=User, status_code=201)
async def create_user(user: UserIn) -> User:
    logger.info("Registering new user")
    
    # Check if the email is already registered
    existing_user = await find_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed_password = get_password_hash(user.password)
    
    # Prepare the data to insert into the database
    user_data = {
        "username": user.name,  # Assuming 'name' is 'username' in your table
        "email": user.email,
        "hashed_password": hashed_password
    }
    
    # Insert the new user data into the database
    query = users.insert().values(user_data)
    user_id = await database.execute(query)

    # Return the user information without the password (response_model is User)
    return {"id": user_id, "name": user.name, "email": user.email}


# User Login
@router.post("/user/login")
async def login_user(user: UserLogin):
    logger.info(f"User login attempt for email {user.email}")
    
    # Find user by email
    db_user = await find_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user['hashed_password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create the access token
    access_token = create_access_token(data={"sub": db_user['email']})
    
    # Return the access token
    return {"access_token": access_token, "token_type": "bearer"}


# PayPal Payment Route
@router.post("/user/payment", response_model=Payment)
async def process_payment(payment: Payment, user: User = Depends(find_user_by_email)):
    logger.info(f"Processing payment for amount: {payment.amount}")
    
    # Fetch PayPal token
    paypal_token = fetch_paypal_token()

    if not paypal_token:
        raise HTTPException(status_code=500, detail="Unable to process payment with PayPal")
    
    # Create the payment with PayPal
    payment_response = create_paypal_payment(paypal_token, payment)
    
    # Store the payment status for the user
    status = payment_response.get("state", "failed")
    await store_payment(user_id=user.id, amount=payment.amount, status=status, payment_method=payment.payment_method)
    
    # Return the payment response
    return {
        "id": payment_response.get("id"),
        "payment_method": payment.payment_method,
        "amount": payment.amount,
        "status": status,
        "redirect_url": payment_response.get("links", [{}])[1].get("href")  # URL to redirect the user to PayPal for payment
    }

@router.post("/donor/request-refund", status_code=201)
async def request_refund(refund: RefundRequest, user: dict = Depends(find_user_by_email)):
    logger.info(f"User {user['email']} is requesting a refund for payment ID {refund.payment_id}")

    # Check if the payment exists and belongs to the user
    query = payments.select().where(payments.c.id == refund.payment_id, payments.c.user_id == user['id'])
    payment = await database.fetch_one(query)

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found or does not belong to this user")

    # Ensure the refund amount does not exceed the original payment amount
    if refund.amount > payment['amount']:
        raise HTTPException(status_code=400, detail="Refund amount exceeds the original payment")

    # Insert refund request with pending status
    refund_data = {
        "user_id": user['id'],
        "payment_id": refund.payment_id,
        "amount": refund.amount,
        "status": "pending",
    }
    query = refund_requests.insert().values(refund_data)
    await database.execute(query)

    return {"message": "Refund request submitted successfully, awaiting admin approval."}


# Admin approves or rejects refund
@router.post("/admin/manage-refund/{refund_id}", dependencies=[Depends(has_role("admin"))])
async def manage_refund(refund_id: int, decision: str):
    logger.info(f"Admin is reviewing refund ID {refund_id}")

    # Fetch the refund request
    query = refund_requests.select().where(refund_requests.c.id == refund_id)
    refund_request = await database.fetch_one(query)

    if not refund_request:
        raise HTTPException(status_code=404, detail="Refund request not found")

    # Only approve or reject pending refunds
    if refund_request['status'] != "pending":
        raise HTTPException(status_code=400, detail="Refund request is already processed")

    # Admin decision to approve or reject
    if decision == "approve":
        # Call PayPal refund API to process the refund
        try:
            paypal_response = process_paypal_refund(refund_request['payment_id'], refund_request['amount'])
            logger.info(f"PayPal refund processed: {paypal_response}")

            # Update refund request status
            query = refund_requests.update().where(refund_requests.c.id == refund_id).values(
                status="approved",
                admin_approved=True
            )
            await database.execute(query)
            return {"message": "Refund approved and processed successfully."}

        except Exception as e:
            logger.error(f"PayPal refund failed: {str(e)}")
            raise HTTPException(status_code=500, detail="PayPal refund processing failed")

    elif decision == "reject":
        # Update refund request status to rejected
        query = refund_requests.update().where(refund_requests.c.id == refund_id).values(
            status="rejected"
        )
        await database.execute(query)
        return {"message": "Refund request has been rejected."}

    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Choose 'approve' or 'reject'.")