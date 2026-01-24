"""Ensure default admin user exists on startup."""

from app.core.account_keys import generate_account_key
from app.core.account_store import get_account_store
from app.core.user_store import get_user_store
from bson import ObjectId


async def ensure_admin_user():
    """
    Ensure the default admin user exists.

    Creates freymantechnology@gmail.com as admin with role="admin" if not exists.
    This runs on server startup to guarantee admin access.
    """
    user_store = get_user_store()
    if not user_store:
        print("⚠ User store not initialized, skipping admin user creation")
        return

    account_store = get_account_store()
    if not account_store:
        print("⚠ Account store not initialized, skipping admin user creation")
        return

    # Ensure user_store database connection is ready
    if hasattr(user_store, '_ensure_connected'):
        await user_store._ensure_connected()

    admin_email = "freymantechnology@gmail.com"

    # Check if admin user already exists (query database directly to avoid cache issues)
    existing_admin = await user_store.db.users.find_one({"email": admin_email})

    if existing_admin:
        # User exists - ensure they have admin role
        if existing_admin.get("role") != "admin":
            print(
                f"⚠ User {admin_email} exists but is not admin, updating role...")
            await user_store.db.users.update_one(
                {"_id": existing_admin["_id"]},
                {"$set": {"role": "admin", "email_verified": True}}
            )
            print(f"✓ Updated {admin_email} to admin role")
        else:
            print(f"✓ Admin user {admin_email} already exists")
        return

    # Admin user doesn't exist - create it
    print(f"Creating default admin user: {admin_email}")

    # Generate a secure random password (user will use OTP login anyway)
    import secrets
    temp_password = secrets.token_urlsafe(32)

    # Create account for admin user (use async version to avoid event loop issues)
    api_key = generate_account_key()
    admin_account = await account_store.create_account_async(
        name="Freyman Technology",
        api_key=api_key,
        postgres_url="",
        mongodb_url="",
        gemini_mode="platform",
        gemini_api_key=None,
    )

    if not admin_account or not admin_account.id:
        print("✗ Failed to create account for admin user")
        return

    # Create admin user
    try:
        admin_user = await user_store.create_user(
            email=admin_email,
            password=temp_password,
            account_id=admin_account.id,
        )

        # Set admin role and mark email as verified
        await user_store.db.users.update_one(
            {"_id": ObjectId(admin_user.id)},
            {"$set": {"role": "admin", "email_verified": True}}
        )

        print(f"✓ Created admin user: {admin_email}")
        print("  - Role: admin")
        print("  - Email verified: True")
        print("  - OTP login enabled at /admin/login")

    except Exception as e:
        error_msg = str(e)
        # If duplicate key error, user already exists (race condition during startup)
        if "E11000" in error_msg or "duplicate key" in error_msg:
            print(
                f"ℹ️  Admin user {admin_email} already exists (created by another process)")
            # Clean up the extra tenant we created
            await account_store.delete_account_async(admin_account.id)
        else:
            print(f"✗ Failed to create admin user: {e}")
            # Clean up tenant if user creation failed
            await account_store.delete_account_async(admin_account.id)
