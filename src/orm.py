from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Generator

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from src.config import MySQLSettings


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class Column:
    name: str
    column_type: str
    primary_key: bool = False
    nullable: bool = True
    auto_increment: bool = False
    unique: bool = False
    default: str | None = None

    def to_sql(self) -> str:
        parts = [f"`{self.name}`", self.column_type]
        if self.primary_key:
            parts.append("PRIMARY KEY")
        if self.auto_increment:
            parts.append("AUTO_INCREMENT")
        if not self.nullable:
            parts.append("NOT NULL")
        if self.unique:
            parts.append("UNIQUE")
        if self.default is not None:
            safe_default = self.default.replace("'", "''")
            parts.append(f"DEFAULT '{safe_default}'")
        return " ".join(parts)


class SimpleORM:
    def __init__(self, host: str, port: int, user: str, password: str, database: str) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database

    @classmethod
    def from_settings(cls, settings: MySQLSettings) -> "SimpleORM":
        return cls(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            database=settings.database,
        )

    @contextmanager
    def _connect(self) -> Generator[Connection, None, None]:
        conn = pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=self.database,
            cursorclass=DictCursor,
            autocommit=False,
        )
        try:
            yield conn
        finally:
            conn.close()

    def _validate_identifier(self, name: str) -> None:
        if not _IDENTIFIER.match(name):
            raise ValueError(f"Invalid SQL identifier: {name}")

    def _quote_identifier(self, name: str) -> str:
        self._validate_identifier(name)
        return f"`{name}`"

    def create_table(self, table: str, columns: list[Column]) -> None:
        table_name = self._quote_identifier(table)
        for col in columns:
            self._validate_identifier(col.name)

        column_sql = ", ".join(col.to_sql() for col in columns)
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_sql})"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
            conn.commit()

    def insert(self, table: str, values: dict[str, Any]) -> int:
        table_name = self._quote_identifier(table)
        keys = list(values.keys())
        for key in keys:
            self._validate_identifier(key)

        placeholders = ", ".join("%s" for _ in keys)
        columns_sql = ", ".join(self._quote_identifier(key) for key in keys)
        sql = f"INSERT INTO {table_name} ({columns_sql}) VALUES ({placeholders})"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, [values[key] for key in keys])
                new_id = int(cursor.lastrowid)
            conn.commit()
        return new_id

    def all(self, table: str) -> list[dict[str, Any]]:
        table_name = self._quote_identifier(table)
        sql = f"SELECT * FROM {table_name} ORDER BY id"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
        return list(rows)

    def find_by_id(self, table: str, row_id: int) -> dict[str, Any] | None:
        table_name = self._quote_identifier(table)
        sql = f"SELECT * FROM {table_name} WHERE id = %s"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, [row_id])
                row = cursor.fetchone()
        return row

    def find_one_by(self, table: str, filters: dict[str, Any]) -> dict[str, Any] | None:
        table_name = self._quote_identifier(table)
    
        if not filters:
            return None
    
        for key in filters.keys():
            self._validate_identifier(key)
    
        where_sql = " AND ".join(f"{self._quote_identifier(k)} = %s" for k in filters.keys())
        sql = f"SELECT * FROM {table_name} WHERE {where_sql} LIMIT 1"
    
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, list(filters.values()))
                row = cursor.fetchone()
    
        return row

    def update_by_id(self, table: str, row_id: int, values: dict[str, Any]) -> bool:
        if not values:
            return False

        table_name = self._quote_identifier(table)
        for key in values.keys():
            self._validate_identifier(key)

        set_sql = ", ".join(f"{self._quote_identifier(key)} = %s" for key in values.keys())
        sql = f"UPDATE {table_name} SET {set_sql} WHERE id = %s"
        params = [values[key] for key in values.keys()] + [row_id]

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                changed = cursor.rowcount > 0
            conn.commit()
        return changed

    def delete_by_id(self, table: str, row_id: int) -> bool:
        table_name = self._quote_identifier(table)
        sql = f"DELETE FROM {table_name} WHERE id = %s"

        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, [row_id])
                changed = cursor.rowcount > 0
            conn.commit()
        return changed
