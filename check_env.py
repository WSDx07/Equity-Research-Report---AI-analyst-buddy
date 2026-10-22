import os

from dotenv import load_dotenv


load_dotenv()

api_key = os.getenv("API_KEY", "")
sec_user_agent = os.getenv("SEC_USER_AGENT", "")

print(f"{api_key[:4]}...")
print(sec_user_agent)
