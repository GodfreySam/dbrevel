#!/usr/bin/env python3
"""Script to list all users in MongoDB."""

import asyncio
import sys

from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient


async def list_all_users():
    """List all users from MongoDB."""
    # Extract base MongoDB URL (without database name) for user store
    if '/' in settings.MONGODB_URL:
        mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
    else:
        mongo_base_url = settings.MONGODB_URL

    db_name = "dbrevel_platform"

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_base_url)
    db = client[db_name]

    try:
        # Get all users
        users = await db.users.find({}).to_list(length=100)

        if not users:
            print("No users found in database.")
            return

        print(f"Found {len(users)} user(s):\n")
        for user in users:
            print(f"  Email: {user.get('email', 'N/A')}")
            print(f"  User ID: {user.get('id', 'N/A')}")
            print(f"  Tenant ID: {user.get('tenant_id', 'N/A')}")
            print(f"  Email Verified: {user.get('email_verified', False)}")
            print(f"  Created At: {user.get('created_at', 'N/A')}")
            print()

    except Exception as e:
        print(f"Error listing users: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


async def list_all_tenants():
    """List all tenants from MongoDB."""
    # Extract base MongoDB URL (without database name)
    if '/' in settings.MONGODB_URL:
        mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
    else:
        mongo_base_url = settings.MONGODB_URL

    db_name = "dbrevel_platform"

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_base_url)
    db = client[db_name]

    try:
        # Get all tenants
        tenants = await db.tenants.find({}).to_list(length=100)

        if not tenants:
            print("No tenants found in database.")
            return

        print(f"Found {len(tenants)} tenant(s):\n")
        for tenant in tenants:
            print(f"  Tenant ID: {tenant.get('tenant_id', 'N/A')}")
            print(f"  Name: {tenant.get('name', 'N/A')}")
            print(
                f"  API Key: {tenant.get('api_key', 'N/A')[:20]}..." if tenant.get('api_key') else 'N/A')
            print(f"  Created At: {tenant.get('created_at', 'N/A')}")
            print()

    except Exception as e:
        print(f"Error listing tenants: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


async def main():
    """Main function."""
    print("=" * 60)
    print("USERS")
    print("=" * 60)
    await list_all_users()

    print("\n" + "=" * 60)
    print("TENANTS")
    print("=" * 60)
    await list_all_tenants()


if __name__ == "__main__":
    asyncio.run(main())
