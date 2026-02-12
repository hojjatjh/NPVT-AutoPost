from __future__ import annotations

import asyncio
import hashlib
import logging
import random
import time
from dataclasses import dataclass

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from src.controllers import ChannelManager, ConfigManager, RelaySettingsManager
from src.orm import SimpleORM


@dataclass(frozen=True)
class RelayJob:
    source_chat_id: int
    destination_chat_id: int
    message_id: int


class NPVTRelayService:
    def __init__(
        self,
        client: TelegramClient,
        orm: SimpleORM,
        log: logging.Logger,
    ) -> None:
        self.client = client
        self.log = log
        self.channel_manager = ChannelManager(orm)
        self.config_manager = ConfigManager(orm)
        self.settings_manager = RelaySettingsManager(orm)

        self.caption = RelaySettingsManager.DEFAULT_CAPTION
        self.send_interval_seconds = RelaySettingsManager.DEFAULT_SEND_INTERVAL_SECONDS
        self.source_cache_seconds = RelaySettingsManager.DEFAULT_SOURCE_CACHE_SECONDS
        self.file_prefix = RelaySettingsManager.DEFAULT_FILENAME_PREFIX
        self.relay_enabled = RelaySettingsManager.DEFAULT_RELAY_ENABLED
        self.dedup_enabled = RelaySettingsManager.DEFAULT_DEDUP_ENABLED

        self._queue: asyncio.Queue[RelayJob] = asyncio.Queue()
        self._source_map: dict[int, int] = {}
        self._map_updated_at = 0.0
        self._map_lock = asyncio.Lock()
        self._settings_lock = asyncio.Lock()
        self._settings_last_refresh = 0.0
        self._settings_refresh_seconds = 15.0
        self._worker_task: asyncio.Task | None = None

    def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._run_worker(), name="npvt-relay-worker")
            self._worker_task.add_done_callback(self._on_worker_done)

        self.client.add_event_handler(self._on_new_message, events.NewMessage(incoming=True))
        self.log.info(
            "NPVT relay enabled (caption=%s, rate_limit=%.1fs, file_prefix=%s, relay_enabled=%s, dedup_enabled=%s, queue=unbounded)",
            self.caption,
            self.send_interval_seconds,
            self.file_prefix,
            self.relay_enabled,
            self.dedup_enabled,
        )

    def _on_worker_done(self, task: asyncio.Task) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            self.log.info("NPVT relay worker stopped")
        except Exception:
            self.log.exception("NPVT relay worker crashed")

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if event.chat_id is None or event.message is None:
            return

        await self._refresh_runtime_settings_if_needed()
        if not self.relay_enabled:
            return

        source_chat_id = int(event.chat_id)
        if source_chat_id >= 0 or not str(source_chat_id).startswith("-100"):
            return

        destination_chat_id = await self._resolve_destination(source_chat_id)
        if destination_chat_id is None:
            return

        if not self._is_npvt_file(event.message):
            return

        job = RelayJob(
            source_chat_id=source_chat_id,
            destination_chat_id=destination_chat_id,
            message_id=event.message.id,
        )

        await self._queue.put(job)

        self.log.info(
            "NPVT queued: source=%s destination=%s message=%s queue_size=%s",
            source_chat_id,
            destination_chat_id,
            event.message.id,
            self._queue.qsize(),
        )

    async def _refresh_runtime_settings_if_needed(self, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._settings_last_refresh < self._settings_refresh_seconds:
            return

        async with self._settings_lock:
            now = time.monotonic()
            if not force and now - self._settings_last_refresh < self._settings_refresh_seconds:
                return

            settings = await asyncio.to_thread(self.settings_manager.get_runtime_settings)

            self.caption = str(settings["caption"])
            self.file_prefix = str(settings["filename_prefix"])
            self.send_interval_seconds = max(1.0, float(settings["send_interval_seconds"]))
            self.source_cache_seconds = max(5, int(settings["source_cache_seconds"]))
            self.relay_enabled = bool(settings["relay_enabled"])
            self.dedup_enabled = bool(settings["dedup_enabled"])
            self._settings_last_refresh = time.monotonic()

    async def _resolve_destination(self, source_chat_id: int) -> int | None:
        now = time.monotonic()
        if source_chat_id not in self._source_map or now - self._map_updated_at >= self.source_cache_seconds:
            await self._refresh_source_map()
        return self._source_map.get(source_chat_id)

    async def _refresh_source_map(self) -> None:
        async with self._map_lock:
            now = time.monotonic()
            if self._source_map and now - self._map_updated_at < self.source_cache_seconds:
                return

            rows = await asyncio.to_thread(self.channel_manager.get_all_channels)
            source_map: dict[int, int] = {}

            for row in rows:
                try:
                    source_id = int(row["source_channel_id"])
                    destination_id = int(row["destination_channel_id"])
                except (KeyError, TypeError, ValueError):
                    continue

                if str(source_id).startswith("-100") and str(destination_id).startswith("-100"):
                    source_map[source_id] = destination_id

            self._source_map = source_map
            self._map_updated_at = time.monotonic()

    async def _run_worker(self) -> None:
        await self._refresh_runtime_settings_if_needed(force=True)
        while True:
            job = await self._queue.get()
            should_requeue = False

            try:
                await self._refresh_runtime_settings_if_needed()
                if not self.relay_enabled:
                    await self._queue.put(job)
                    await asyncio.sleep(2.0)
                    continue
                message = await self.client.get_messages(job.source_chat_id, ids=job.message_id)
                if not message or not self._is_npvt_file(message):
                    continue

                source_file_id = "not_set"
                if message.file is not None and getattr(message.file, "id", None) is not None:
                    source_file_id = str(message.file.id)

                if self.dedup_enabled and source_file_id != "not_set":
                    exists_by_id = await asyncio.to_thread(self.config_manager.exists_file_id, source_file_id)
                    if exists_by_id:
                        self.log.info(
                            "Duplicate skipped by file_id: source=%s message=%s file_id=%s",
                            job.source_chat_id,
                            job.message_id,
                            source_file_id,
                        )
                        continue

                file_bytes = await message.download_media(file=bytes)
                if file_bytes is None:
                    self.log.warning("Could not download .npvt message %s from %s", job.message_id, job.source_chat_id)
                    continue

                file_hash = hashlib.sha256(file_bytes).hexdigest()
                if self.dedup_enabled:
                    exists_by_hash = await asyncio.to_thread(self.config_manager.exists_file_hash, file_hash)
                    if exists_by_hash:
                        self.log.info(
                            "Duplicate skipped by file_hash: source=%s message=%s hash=%s",
                            job.source_chat_id,
                            job.message_id,
                            file_hash[:12],
                        )
                        continue

                next_index = await asyncio.to_thread(self.config_manager.next_npvt_index)
                file_name = f"{self.file_prefix} ({next_index}).npvt"
                uploaded = await self.client.upload_file(file_bytes, file_name=file_name)

                sent_message = await self.client.send_file(
                    job.destination_chat_id,
                    uploaded,
                    caption=self.caption,
                    force_document=True,
                )

                await asyncio.to_thread(
                    self.config_manager.log_transfer,
                    file_id=source_file_id,
                    file_hash=file_hash,
                    name=file_name,
                    from_chat=str(job.source_chat_id),
                    to_chat=str(job.destination_chat_id),
                    from_message_id=str(job.message_id),
                    to_message_id=str(sent_message.id),
                )

                self.log.info(
                    "NPVT sent: source=%s destination=%s message=%s as %s",
                    job.source_chat_id,
                    job.destination_chat_id,
                    job.message_id,
                    file_name,
                )
            except FloodWaitError as error:
                should_requeue = True
                wait_seconds = max(float(error.seconds), self.send_interval_seconds)
                self.log.warning(
                    "FloodWait %ss while sending from source %s. Requeueing message %s",
                    error.seconds,
                    job.source_chat_id,
                    job.message_id,
                )
                await asyncio.sleep(wait_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.log.exception(
                    "Failed to relay NPVT message %s from source %s",
                    job.message_id,
                    job.source_chat_id,
                )
            finally:
                self._queue.task_done()

            if should_requeue:
                await self._queue.put(job)
                continue

            pause_seconds = self.send_interval_seconds + random.uniform(0.4, 1.2)
            await asyncio.sleep(pause_seconds)

    @staticmethod
    def _is_npvt_file(message) -> bool:
        file_obj = getattr(message, "file", None)
        if file_obj is None:
            return False

        name = (getattr(file_obj, "name", "") or "").lower()
        ext = (getattr(file_obj, "ext", "") or "").lower()

        return name.endswith(".npvt") or ext == ".npvt"


def start_npvt_relay(client: TelegramClient, orm: SimpleORM, log: logging.Logger) -> NPVTRelayService:
    relay = NPVTRelayService(client=client, orm=orm, log=log)
    relay.start()
    return relay
