from httpx import *
from os import *
from dotenv import load_dotenv

load_dotenv()

def auth_Login(password: str) -> str:
    url = getenv("API_BASE") + "/api/v1/auth/login"
    response = post(url, json={"password": password})
    if response.status_code == 200:
        token = response.json().get('access_token')
        environ["ACCESS_TOKEN"] = token
        return token
    return None