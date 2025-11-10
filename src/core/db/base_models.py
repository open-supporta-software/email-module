from datetime import datetime
from typing import Any, ClassVar

from sqlalchemy import JSON, DateTime, MetaData, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class BaseModel(DeclarativeBase):
    __abstract__ = True

    metadata = MetaData(
        naming_convention={
            "pk": "pk_%(table_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "ix": "ix_%(table_name)s_%(column_0_name)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
        },
    )

    repr_cols_num = 3
    repr_cols = ()

    def __repr__(self) -> str:
        column_names = list(self.__table__.columns.keys())
        cols = []

        for idx, col_name in enumerate(column_names):
            if col_name in self.repr_cols or idx < self.repr_cols_num:
                value = getattr(self, col_name)
                cols.append(f"{col_name}={value!r}")

        cols_str = ", ".join(cols)
        return f"<{self.__class__.__name__}({cols_str})>"

    def update(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            if key in self.get_field_names():
                setattr(self, key, value)

    @classmethod
    def get_field_names(cls) -> list[str]:
        return [column.name for column in cls.__table__.columns]


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("timezone('utc', now())"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("timezone('utc', now())"),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    __soft_delete_cascades__: ClassVar[tuple[str, ...]] = ()

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class ABACMixin:
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
