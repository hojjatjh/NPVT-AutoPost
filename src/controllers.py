from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.orm import SimpleORM


class ChannelManager:
    def __init__(self, orm: SimpleORM):
        self.orm = orm
        self.table = "channels"

    def add_channel(self, source_id: int, dest_id: int) -> int:
        return self.orm.insert(
            self.table,
            {
                "source_channel_id": int(source_id),
                "destination_channel_id": int(dest_id),
                "created_at": datetime.now().isoformat(),
            },
        )

    def get_all_channels(self) -> list[dict]:
        return self.orm.all(self.table)

    def count_channels(self) -> int:
        return self.orm.count(self.table)

    def get_channel(self, channel_id: int) -> dict | None:
        return self.orm.find_by_id(self.table, channel_id)

    def update_channel(self, channel_id: int, source_id: int | None = None, dest_id: int | None = None) -> bool:
        values = {}
        if source_id is not None:
            values["source_channel_id"] = int(source_id)
        if dest_id is not None:
            values["destination_channel_id"] = int(dest_id)
        return self.orm.update_by_id(self.table, channel_id, values)

    def delete_channel(self, channel_id: int) -> bool:
        return self.orm.delete_by_id(self.table, channel_id)

    def get_by_source(self, source_id: int) -> dict | None:
        return self.orm.find_one_by(self.table, {"source_channel_id": int(source_id)})


class ConfigManager:
    def __init__(self, orm: SimpleORM):
        self.orm = orm
        self.table = "configs"

    def next_npvt_index(self) -> int:
        return self.orm.count(self.table) + 1

    def log_transfer(
        self,
        *,
        file_id: str,
        file_hash: str,
        name: str,
        from_chat: str,
        to_chat: str,
        from_message_id: str,
        to_message_id: str,
    ) -> int:
        payload = {
            "file_id": file_id,
            "file_hash": file_hash,
            "name": name,
            "from_chat": from_chat,
            "to_chat": to_chat,
            "from_messsage_id": from_message_id,
            "to_messsage_id": to_message_id,
            "date": datetime.now().isoformat(),
        }
        try:
            return self.orm.insert(self.table, payload)
        except Exception:
            # Backward-compatible fallback if DB schema has not yet added file_hash.
            payload.pop("file_hash", None)
            return self.orm.insert(self.table, payload)

    def exists_file_id(self, file_id: str) -> bool:
        if not file_id or file_id == "not_set":
            return False
        return self.orm.find_one_by(self.table, {"file_id": file_id}) is not None

    def exists_file_hash(self, file_hash: str) -> bool:
        if not file_hash or file_hash == "not_set":
            return False
        try:
            return self.orm.find_one_by(self.table, {"file_hash": file_hash}) is not None
        except Exception:
            return False

    def get_stats(self) -> dict[str, str | int]:
        total_transfers = self.orm.count(self.table)
        unique_source_chats = self.orm.count_distinct(self.table, "from_chat", ignore_value="not_set")
        unique_destination_chats = self.orm.count_distinct(self.table, "to_chat", ignore_value="not_set")
        unique_file_ids = self.orm.count_distinct(self.table, "file_id", ignore_value="not_set")

        try:
            unique_file_hashes = self.orm.count_distinct(self.table, "file_hash", ignore_value="not_set")
        except Exception:
            unique_file_hashes = 0

        latest_row = self.orm.latest(self.table, order_by="id")
        latest_transfer_date = "not_set"
        if latest_row is not None:
            latest_transfer_date = str(latest_row.get("date", "not_set"))

        return {
            "total_transfers": total_transfers,
            "unique_source_chats": unique_source_chats,
            "unique_destination_chats": unique_destination_chats,
            "unique_file_ids": unique_file_ids,
            "unique_file_hashes": unique_file_hashes,
            "latest_transfer_date": latest_transfer_date,
        }

    def reset_all_transfers(self) -> int:
        total_before = self.orm.count(self.table)
        self.orm.truncate_table(self.table)
        return total_before


class RelaySettingsManager:
    DEFAULT_CAPTION = "#npvt best"
    DEFAULT_SEND_INTERVAL_SECONDS = 6.0
    DEFAULT_SOURCE_CACHE_SECONDS = 20
    DEFAULT_FILENAME_PREFIX = "npvt"
    DEFAULT_RELAY_ENABLED = True
    DEFAULT_DEDUP_ENABLED = True

    def __init__(self, orm: SimpleORM):
        self.orm = orm
        self.table = "relay_settings"

    def _get_raw(self, key: str) -> str | None:
        row = self.orm.find_one_by(self.table, {"setting_key": key})
        if row is None:
            return None
        return str(row.get("setting_value", "")).strip()

    def _set_raw(self, key: str, value: str) -> None:
        row = self.orm.find_one_by(self.table, {"setting_key": key})
        payload = {
            "setting_key": key,
            "setting_value": value,
            "updated_at": datetime.now().isoformat(),
        }
        if row is None:
            self.orm.insert(self.table, payload)
            return
        self.orm.update_by_id(self.table, int(row["id"]), payload)

    def get_runtime_settings(self) -> dict[str, str | float | int]:
        caption = self._get_raw("caption") or self.DEFAULT_CAPTION
        prefix = self.normalize_filename_prefix(self._get_raw("filename_prefix") or self.DEFAULT_FILENAME_PREFIX)

        try:
            send_interval = float(self._get_raw("send_interval_seconds") or self.DEFAULT_SEND_INTERVAL_SECONDS)
        except ValueError:
            send_interval = self.DEFAULT_SEND_INTERVAL_SECONDS
        send_interval = max(1.0, send_interval)

        try:
            source_cache = int(self._get_raw("source_cache_seconds") or self.DEFAULT_SOURCE_CACHE_SECONDS)
        except ValueError:
            source_cache = self.DEFAULT_SOURCE_CACHE_SECONDS
        source_cache = max(5, source_cache)

        relay_enabled_raw = (self._get_raw("relay_enabled") or "").lower()
        relay_enabled = relay_enabled_raw in {"1", "true", "on", "yes", "enabled"}
        if relay_enabled_raw == "":
            relay_enabled = self.DEFAULT_RELAY_ENABLED

        dedup_enabled_raw = (self._get_raw("dedup_enabled") or "").lower()
        dedup_enabled = dedup_enabled_raw in {"1", "true", "on", "yes", "enabled"}
        if dedup_enabled_raw == "":
            dedup_enabled = self.DEFAULT_DEDUP_ENABLED

        return {
            "caption": caption,
            "filename_prefix": prefix,
            "send_interval_seconds": send_interval,
            "source_cache_seconds": source_cache,
            "relay_enabled": relay_enabled,
            "dedup_enabled": dedup_enabled,
        }

    def set_caption(self, caption: str) -> None:
        value = (caption or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        if not value:
            value = self.DEFAULT_CAPTION
        if len(value) > 1024:
            value = value[:1024]
        self._set_raw("caption", value)

    def set_send_interval_seconds(self, seconds: float) -> None:
        value = max(1.0, float(seconds))
        self._set_raw("send_interval_seconds", str(value))

    def set_source_cache_seconds(self, seconds: int) -> None:
        value = max(5, int(seconds))
        self._set_raw("source_cache_seconds", str(value))

    def set_filename_prefix(self, prefix: str) -> None:
        value = self.normalize_filename_prefix(prefix)
        self._set_raw("filename_prefix", value)

    def set_relay_enabled(self, enabled: bool) -> None:
        self._set_raw("relay_enabled", "1" if enabled else "0")

    def set_dedup_enabled(self, enabled: bool) -> None:
        self._set_raw("dedup_enabled", "1" if enabled else "0")

    @classmethod
    def normalize_filename_prefix(cls, prefix: str | None) -> str:
        value = (prefix or "").replace("\r\n", " ").replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()
        value = value.replace("/", "_").replace("\\", "_")
        while "  " in value:
            value = value.replace("  ", " ")
        if not value:
            value = cls.DEFAULT_FILENAME_PREFIX
        return value[:80]


class UserManager:
    def __init__(self, orm: SimpleORM):
        self.orm = orm

    def get_user(self, user_id: int) -> Optional[dict]:
        return self.orm.find_by_id("users", user_id)

    def create_user(self, user_id: int, step: str = "none", status: str = "none", data: str | None = None) -> int:
        values = {
            "id": user_id,
            "step": step,
            "status": status,
            "data": data or "",
        }
        return self.orm.insert("users", values)

    def update_user(self, user_id: int, step: str | None = None, status: str | None = None, data: str | None = None) -> bool:
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
        return self.orm.delete_by_id("users", user_id)

    def ensure_user(self, user_id: int, step: str) -> dict:
        user = self.get_user(user_id)
        if not user:
            new_id = self.orm.insert(
                "users",
                {
                    "id": user_id,
                    "status": "none",
                    "step": step,
                    "data": None,
                },
            )
            user = self.get_user(new_id)
        return user
