from __future__ import annotations
from datetime import datetime
from src.orm import SimpleORM
from typing import Optional

class ChannelManager:
    def __init__(self, orm: SimpleORM):
        self.orm = orm
        self.table = "channels"

    def add_channel(self, source_id: int, dest_id: int) -> int:
        """Add new channel mapping to database"""
        return self.orm.insert(
            self.table,
            {
                "source_channel_id": source_id,
                "destination_channel_id": dest_id,
                "created_at": datetime.now().isoformat()
            }
        )

    def get_all_channels(self) -> list[dict]:
        """Get all channel mappings"""
        return self.orm.all(self.table)

    def get_channel(self, channel_id: int) -> dict | None:
        """Find channel by internal ID"""
        return self.orm.find_by_id(self.table, channel_id)

    def update_channel(self, channel_id: int, source_id: int | None = None, dest_id: int | None = None) -> bool:
        """Update source or destination channel"""
        values = {}
        if source_id is not None:
            values["source_channel_id"] = source_id
        if dest_id is not None:
            values["destination_channel_id"] = dest_id
        return self.orm.update_by_id(self.table, channel_id, values)

    def delete_channel(self, channel_id: int) -> bool:
        """Delete channel mapping"""
        return self.orm.delete_by_id(self.table, channel_id)

class UserManager:
    """CRUD operations for 'users' table"""

    def __init__(self, orm: SimpleORM):
        self.orm = orm

    def get_user(self, user_id: int) -> Optional[dict]:
        """Get user by ID"""
        return self.orm.find_by_id("users", user_id)

    def create_user(self, user_id: int, step: str = "none", status: str = "none", data: str = None) -> int:
        """Create a new user in the database"""
        values = {
            "id": user_id,
            "step": step,
            "status": status,
            "data": data or ""
        }
        return self.orm.insert("users", values)

    def update_user(self, user_id: int, step: str = None, status: str = None, data: str = None) -> bool:
        """Update existing user"""
        values = {}
        if step is not None:
            values["step"] = step
        if status is not None:
            values["status"] = status
        if data is not None:
            values["data"] = data
        if not values:
            return False
        return self.orm.update_by_id("users", user_id, values)

    def delete_user(self, user_id: int) -> bool:
        """Delete user from database"""
        return self.orm.delete_by_id("users", user_id)

    def ensure_user(self, user_id: int, step: str) -> dict:
        """Make sure user exists in DB. Return user dict"""
        user = self.get_user(user_id)
        if not user:
            # اگر کاربر وجود نداشت، بسازش
            new_id = self.orm.insert("users", {
                "id": user_id,
                "status": 'none',
                "step": f"{step}",  # default step
                "data": None
            })
            user = self.get_user(new_id)  # دوباره از DB بخونش
        return user