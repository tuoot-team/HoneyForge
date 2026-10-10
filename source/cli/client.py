import httpx
import os

url = os.getenv("API_BASE")

def get_Token():
    return os.environ.get("ACCESS_TOKEN")

def get_Health():
    return httpx.get(url + "/api/v1/health").json()

