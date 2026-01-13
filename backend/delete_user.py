#!/usr/bin/env python3
"""Script to delete a user and their associated tenant from MongoDB by email."""

import asyncio
import sys

from app.core.config import settings
from app.core.tenant_store import tenant_store
from motor.motor_asyncio import AsyncIOMotorClient


async def delete_user_by_email(email: str):
    """Delete a user and their associated tenant from MongoDB by email."""
    # Extract base MongoDB URL (without database name) for user store
    # MONGODB_URL format: mongodb://host:port/database_name
    # We need: mongodb://host:port (base URL) for connection
    if '/' in settings.MONGODB_URL:
        # Split on last '/' to get base URL
        mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
    else:
        mongo_base_url = settings.MONGODB_URL

    db_name = "dbrevel_platform"

    # Connect to MongoDB
    client = AsyncIOMotorClient(mongo_base_url)
    db = client[db_name]

    try:
        # Find the user
        user_doc = await db.users.find_one({"email": email})

        if not user_doc:
            print(f"User with email '{email}' not found in database.")
            return False

        tenant_id = user_doc.get("tenant_id")
        user_id = user_doc.get("id")

        print(f"Found user:")
        print(f"  User ID: {user_id}")
        print(f"  Email: {email}")
        print(f"  Tenant ID: {tenant_id}")
        print()

        # Delete associated tenant if it exists and is not the demo tenant
        if tenant_id and tenant_id != "demo":
            print(f"Attempting to delete tenant '{tenant_id}'...")
            try:
                # Delete tenant from tenant store
                from app.core.tenant_store import MongoDBTenantStore, tenant_store
                if isinstance(tenant_store, MongoDBTenantStore):
                    # Delete from MongoDB directly for tenants
                    # Tenants are stored in dbrevel_platform database (same as users)
                    tenant_client = AsyncIOMotorClient(mongo_base_url)
                    tenant_db = tenant_client[db_name]  # Use same db_name as users

                    tenant_result = await tenant_db.tenants.delete_one({"tenant_id": tenant_id})
                    tenant_client.close()

                    if tenant_result.deleted_count > 0:
                        print(f"✓ Successfully deleted tenant '{tenant_id}' from database.")
                    else:
                        print(f"⚠ Warning: Tenant '{tenant_id}' not found in tenant collection (may have been deleted already).")
                else:
                    # For other store types, use the delete method
                    success = tenant_store.delete_tenant(tenant_id)
                    if success:
                        print(f"✓ Successfully deleted tenant '{tenant_id}'.")
                    else:
                        print(f"⚠ Warning: Failed to delete tenant '{tenant_id}' (may not exist).")
            except Exception as e:
                print(f"⚠ Warning: Could not delete tenant '{tenant_id}': {e}")
                print("  Continuing with user deletion...")
            print()

        # Delete email verification records
        print("Deleting email verification records...")
        email_verification_result = await db.email_verifications.delete_many({"user_id": user_id})
        if email_verification_result.deleted_count > 0:
            print(f"✓ Deleted {email_verification_result.deleted_count} email verification record(s).")

        # Delete password reset records
        print("Deleting password reset records...")
        password_reset_result = await db.password_resets.delete_many({"user_id": user_id})
        if password_reset_result.deleted_count > 0:
            print(f"✓ Deleted {password_reset_result.deleted_count} password reset record(s).")

        # Delete the user
        print("Deleting user...")
        result = await db.users.delete_one({"email": email})

        if result.deleted_count > 0:
            print()
            print(f"✓ Successfully deleted user '{email}' and associated data from database.")
            return True
        else:
            print(f"✗ Failed to delete user '{email}' from database.")
            return False

    except Exception as e:
        print(f"✗ Error during deletion: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        client.close()


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python delete_user.py <email>")
        print("Example: python delete_user.py godfreysam09@gmail.com")
        sys.exit(1)

    email = sys.argv[1]
    print(f"Attempting to delete user with email: {email}")
    print(f"MongoDB URL: {settings.MONGODB_URL}")
    print()

    success = await delete_user_by_email(email)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
