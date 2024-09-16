import requests
from fastapi import HTTPException
from storeapi.config import config

# Fetch PayPal token
def fetch_paypal_token():
    url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US",
    }
    auth = (config.PAYPAL_CLIENT_ID, config.PAYPAL_SECRET)

    data = {
        "grant_type": "client_credentials"
    }

    response = requests.post(url, headers=headers, data=data, auth=auth)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Unable to fetch PayPal token")

    return response.json().get("access_token")

# Create PayPal payment
def create_paypal_payment(token, payment):
    url = "https://api-m.sandbox.paypal.com/v1/payments/payment"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    data = {
        "intent": "sale",
        "payer": {
            "payment_method": payment.payment_method,
        },
        "transactions": [{
            "amount": {
                "total": str(payment.amount),
                "currency": "GBP",
            },
            "description": "Payment description."
        }],
        "redirect_urls": {
            "return_url": "https://yourapp.com/payment-success",
            "cancel_url": "https://yourapp.com/payment-cancel"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 201:
        raise HTTPException(status_code=500, detail="Unable to create PayPal payment")

    return response.json()

def process_paypal_refund(payment_id, amount):
    # Get PayPal access token
    token = fetch_paypal_token()

    url = f"https://api-m.sandbox.paypal.com/v1/payments/sale/{payment_id}/refund"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    data = {
        "amount": {
            "total": str(amount),
            "currency": "USD"
        }
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code != 201:
        raise HTTPException(status_code=500, detail=f"PayPal refund failed: {response.text}")

    return response.json()
