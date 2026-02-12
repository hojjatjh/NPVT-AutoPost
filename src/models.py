"""Application model configuration for the ORM."""

from src.orm import Column, SimpleORM


def setup(orm: SimpleORM) -> None:
    orm.create_table(
        "users",
        [
            Column("id", "BIGINT(85)", primary_key=True, nullable=False, auto_increment=True),
            Column("status", "VARCHAR(255)", nullable=False, default="none"),
            Column("step", "VARCHAR(255)", nullable=False, default="none"),
            Column("data", "LONGTEXT", nullable=True),
        ],
    )

    orm.create_table(
        "configs",
        [
            Column("id", "BIGINT(85)", primary_key=True, nullable=False, auto_increment=True),
            Column("file_id", "VARCHAR(255)", nullable=False, default="not_set"),
            Column("file_hash", "VARCHAR(64)", nullable=False, default="not_set"),
            Column("name", "VARCHAR(255)", nullable=False, default="not_set"),
            Column("from_chat", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("to_chat", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("from_messsage_id", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("to_messsage_id", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("date", "VARCHAR(255)", nullable=False, default="not_set"),
        ],
    )

    orm.create_table(
        "channels",
        [
            Column("id", "BIGINT(85)", primary_key=True, nullable=False, auto_increment=True),
            Column("source_channel_id", "BIGINT(85)", nullable=False),
            Column("destination_channel_id", "BIGINT(85)", nullable=False),
            Column("created_at", "VARCHAR(255)", nullable=False, default="now()"),
        ],
    )

    orm.create_table(
        "relay_settings",
        [
            Column("id", "BIGINT(85)", primary_key=True, nullable=False, auto_increment=True),
            Column("setting_key", "VARCHAR(100)", nullable=False, unique=True),
            Column("setting_value", "VARCHAR(1024)", nullable=False),
            Column("updated_at", "VARCHAR(255)", nullable=False, default="now()"),
        ],
    )

    for table_name in ("users", "configs", "channels", "relay_settings"):
        try:
            orm.ensure_table_utf8mb4(table_name)
        except Exception:
            # Best effort: if DB user cannot alter charset, app can still continue.
            pass

    try:
        orm.ensure_column_exists(
            "configs",
            Column("file_hash", "VARCHAR(64)", nullable=False, default="not_set"),
        )
    except Exception:
        pass
