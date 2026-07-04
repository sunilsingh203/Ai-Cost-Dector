from dotenv import load_dotenv
from db import init_db

load_dotenv()
print("Loaded DATABASE_URL?", bool(__import__("os").environ.get("DATABASE_URL")))
print("Loaded JWT_SECRET?", bool(__import__("os").environ.get("JWT_SECRET")))
init_db()
print("init_db completed")
