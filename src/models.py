"""Application model configuration for the ORM."""

from src.orm import Column, SimpleORM


def setup(orm: SimpleORM) -> None:
    orm.create_table(
        'users',
        [
            Column("id", "BIGINT(85)", primary_key=True, nullable=False, auto_increment=True),
            Column("status", "VARCHAR(255)", nullable=False, default="none"),
            Column("data", "LONGTEXT", nullable=True)
        ],
    )
    orm.create_table(
        'configs',
        [
            Column("file_id", "VARCHAR(255)", nullable=False, default="not_set"),
            Column("name", "VARCHAR(255)", nullable=False, default="not_set"),
            Column("from_chat", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("to_chat", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("from_messsage_id", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("to_messsage_id", "VARCHAR(45)", nullable=False, default="not_set"),
            Column("date", "VARCHAR(255)", nullable=False, default="not_set"),
        ],
    )
