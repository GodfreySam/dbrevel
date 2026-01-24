"""Admin OTP management for secure admin login."""

import random
from datetime import datetime, timedelta
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient


class AdminOTPStore:
    """Store for managing admin login OTPs."""

    def __init__(self, mongo_url: str, db_name: str = "dbrevel_platform"):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.mongo_url = mongo_url
        self.db_name = db_name

    async def _ensure_connected(self):
        """Ensure MongoDB connection is established."""
        if self.client is None:
            from motor.motor_asyncio import AsyncIOMotorClient

            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            # Create index on expiration for cleanup
            await self.db.admin_otps.create_index("expires_at", expireAfterSeconds=0)
            await self.db.admin_otps.create_index("email")

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP code."""
        return f"{random.randint(100000, 999999)}"

    async def create_admin_otp(
        self, user_id: str, email: str, expires_in_minutes: int = 10
    ) -> str:
        """
        Create an admin login OTP.

        Args:
            user_id: Admin user ID
            email: Admin email
            expires_in_minutes: OTP expiration time in minutes (default 10)

        Returns:
            OTP code string (6 digits)
        """
        await self._ensure_connected()

        # Invalidate any existing OTPs for this admin
        await self.db.admin_otps.update_many(
            {"user_id": user_id, "used": False},
            {"$set": {"used": True, "used_at": datetime.utcnow()}},
        )

        # Generate OTP
        otp = self.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=expires_in_minutes)

        # Store OTP
        await self.db.admin_otps.insert_one(
            {
                "otp": otp,
                "user_id": user_id,
                "email": email,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "used": False,
                "attempts": 0,  # Track verification attempts
            }
        )

        return otp

    async def verify_otp(self, email: str, otp: str) -> Optional[dict]:
        """
        Verify an admin OTP code.

        Args:
            email: Admin email
            otp: OTP code to verify

        Returns:
            OTP document if valid, None otherwise
        """
        await self._ensure_connected()

        otp_doc = await self.db.admin_otps.find_one(
            {
                "email": email,
                "otp": otp,
                "used": False,
                "expires_at": {"$gt": datetime.utcnow()},
            }
        )

        if not otp_doc:
            # Increment attempts for rate limiting (even if OTP not found)
            await self.db.admin_otps.update_many(
                {"email": email, "used": False}, {"$inc": {"attempts": 1}}
            )
            return None

        # Check if too many attempts
        if otp_doc.get("attempts", 0) >= 5:
            # Mark as used to prevent further attempts
            await self.db.admin_otps.update_one(
                {"_id": otp_doc["_id"]},
                {"$set": {"used": True, "used_at": datetime.utcnow()}},
            )
            return None

        return otp_doc

    async def mark_otp_used(self, email: str, otp: str) -> bool:
        """
        Mark an OTP as used.

        Args:
            email: Admin email
            otp: OTP code

        Returns:
            True if OTP was found and marked, False otherwise
        """
        await self._ensure_connected()

        result = await self.db.admin_otps.update_one(
            {"email": email, "otp": otp},
            {"$set": {"used": True, "used_at": datetime.utcnow()}},
        )

        return result.modified_count > 0

    async def invalidate_admin_otps(self, user_id: str) -> int:
        """
        Invalidate all OTPs for an admin user.

        Args:
            user_id: Admin user ID

        Returns:
            Number of OTPs invalidated
        """
        await self._ensure_connected()

        result = await self.db.admin_otps.update_many(
            {"user_id": user_id, "used": False},
            {"$set": {"used": True, "used_at": datetime.utcnow()}},
        )

        return result.modified_count


# Global admin OTP store instance
admin_otp_store: Optional[AdminOTPStore] = None


def init_admin_otp_store(mongo_url: str, db_name: str = "dbrevel_platform"):
    """Initialize the global admin OTP store."""
    global admin_otp_store
    admin_otp_store = AdminOTPStore(mongo_url, db_name)
    return admin_otp_store


def get_admin_otp_store() -> Optional[AdminOTPStore]:
    """Get the global admin OTP store instance."""
    return admin_otp_store
