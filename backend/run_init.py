from app.core.ensure_admin import ensure_admin_user
from app.core.demo_account import ensure_demo_account
from app.core.user_store import init_user_store
from app.core.project_store import initialize_project_store
from app.core.password_reset import init_password_reset_store
from app.core.email_verification import init_email_verification_store
from app.core.admin_otp import init_admin_otp_store
from app.core.config import settings
from app.core.account_store import init_account_store
import asyncio
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))


# Initialize account store with configured MongoDB URL
print("Initializing account store with MONGODB_URL:", settings.MONGODB_URL)
# Use base Mongo URL (without database name) for store initializers like main.py
if "/" in settings.MONGODB_URL:
    mongo_base_url = "/".join(settings.MONGODB_URL.rsplit("/", 1)[:-1])
else:
    mongo_base_url = settings.MONGODB_URL

init_account_store(mongo_base_url, "dbrevel_platform")


# Initialize other stores (similar to app.main.lifespan)
init_user_store(mongo_base_url, "dbrevel_platform")
init_password_reset_store(mongo_base_url, "dbrevel_platform")
init_email_verification_store(mongo_base_url, "dbrevel_platform")
initialize_project_store(mongo_base_url, "dbrevel_platform")
init_admin_otp_store(mongo_base_url, "dbrevel_platform")


async def run():
    print("Running ensure_demo_account()...")
    try:
        demo_ok = await ensure_demo_account()
        print("ensure_demo_account returned:", demo_ok)
    except Exception as e:
        print("ensure_demo_account error:", e)

    print("Running ensure_admin_user()...")
    try:
        await ensure_admin_user()
        print("ensure_admin_user completed")
    except Exception as e:
        print("ensure_admin_user error:", e)


if __name__ == "__main__":
    asyncio.run(run())
