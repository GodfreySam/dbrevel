"""
Clear all users from the database for fresh testing.

This script removes all users from the MongoDB users collection,
allowing you to test the signup flow from scratch.
"""

import asyncio
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient


async def clear_users():
    """Clear all users from the database."""
    # Get MongoDB connection details
    mongodb_url = os.getenv(
        "MONGODB_URL",
        "mongodb+srv://dbrevel:dbrevel@cluster0.mongodb.net/"
    )
    db_name = os.getenv("MONGODB_DB_NAME", "dbrevel_platform")

    print(f"Connecting to MongoDB database: {db_name}")

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongodb_url)
    db = client[db_name]

    try:
        # Ping to verify connection
        await client.admin.command('ping')
        print("✅ Connected to MongoDB successfully")

        # Count existing users
        users_count = await db.users.count_documents({})
        print(f"\nFound {users_count} users in the database")

        if users_count == 0:
            print("No users to delete. Database is already clean!")
            return

        # Ask for confirmation
        response = input(f"\n⚠️  Are you sure you want to delete all {users_count} users? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Operation cancelled")
            return

        # Delete all users
        result = await db.users.delete_many({})
        print(f"\n✅ Deleted {result.deleted_count} users from the database")

        # Verify deletion
        remaining = await db.users.count_documents({})
        if remaining == 0:
            print("✅ Database is now clean - ready for fresh testing!")
        else:
            print(f"⚠️  Warning: {remaining} users still remain in the database")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        client.close()
        print("\nMongoDB connection closed")


if __name__ == "__main__":
    print("=" * 60)
    print("Clear Users from Database")
    print("=" * 60)
    print()

    asyncio.run(clear_users())
