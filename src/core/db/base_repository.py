from typing import Any, Literal, TypeVar

from pydantic import BaseModel as BaseSchema
from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, subqueryload

from src.core.db.base_models import BaseModel, SoftDeleteMixin

ModelType = TypeVar("ModelType", bound=BaseModel)
EntityType = TypeVar("EntityType", bound=BaseSchema)
CreateEntityType = TypeVar("CreateEntityType", bound=BaseSchema)
UpdateEntityType = TypeVar("UpdateEntityType", bound=BaseSchema)


class BaseRepository[ModelType, EntityType, CreateEntityType, UpdateEntityType]:
    def __init__(
        self,
        session: AsyncSession,
        model: type[ModelType],
        entity: type[EntityType],
        create_entity: type[CreateEntityType],
        update_entity: type[UpdateEntityType],
    ):
        self._session = session
        self._model = model
        self._entity = entity
        self._create_entity = create_entity
        self._update_entity = update_entity
        self._is_soft_deletable = issubclass(self._model, SoftDeleteMixin)
        self._search_fields = []

    async def get(
        self,
        value: Any,
        field: str = "id",
        relations: dict[Literal["select", "joined", "subquery"], list[str]] | None = None,
        *,
        with_deleted: bool = False,
    ) -> EntityType | None:
        model = await self._get(value, field, relations, with_deleted=with_deleted)
        return self._to_entity(model) if model else None

    async def _get(
        self,
        value: Any,
        field: str = "id",
        relations: dict[Literal["select", "joined", "subquery"], list[str]] | None = None,
        *,
        with_deleted: bool = False,
    ) -> ModelType | None:
        if self._is_soft_deletable and not with_deleted:
            query = self._select_not_deleted().where(getattr(self._model, field) == value)
        else:
            query = select(self._model).where(getattr(self._model, field) == value)

        query = self._load_relations(query=query, relations=relations)
        result = await self._session.execute(query)

        return result.scalars().first()

    async def _get_one_or_none(self, where_clause) -> ModelType | None:
        if self._is_soft_deletable:
            query = self._select_not_deleted().where(where_clause)
        else:
            query = select(self._model).where(where_clause)

        result = await self._session.execute(query)
        return result.scalars().first()

    async def _get_many(self, where_clause) -> list[ModelType]:
        if self._is_soft_deletable:
            query = self._select_not_deleted().where(where_clause)
        else:
            query = select(self._model).where(where_clause)

        result = await self._session.execute(query)

        return list(result.scalars().all())

    async def get_list(
        self,
        filters: dict[str, Any] | None = None,
        sorting: dict[str, str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        relations: dict[Literal["select", "joined", "subquery"], list[str]] | None = None,
        *,
        with_deleted: bool = False,
    ) -> tuple[list[EntityType], int]:
        if self._is_soft_deletable and not with_deleted:
            query = self._select_not_deleted()
        else:
            query = select(self._model)

        if filters:
            query = self._apply_filters(query=query, filters=filters)

        query = self._load_relations(query=query, relations=relations)

        if sorting:
            query = self._apply_sorting(query=query, sorting=sorting)

        query, total = await self._apply_pagination(query=query, limit=limit, offset=offset)

        result = await self._session.execute(query)

        has_joined_loads = bool(relations and "joined" in relations)

        items = result.unique().scalars().all() if has_joined_loads else result.scalars().all()

        items = [self._to_entity(item) for item in items]

        return items, total

    async def create(self, data: CreateEntityType) -> EntityType:
        model = self._model(**data.model_dump(exclude_unset=True, exclude_none=True))  # pyright: ignore[reportAttributeAccessIssue]
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)

        return self._to_entity(model)

    async def update(
        self,
        data: UpdateEntityType,
        value: Any,
        field: str = "id",
    ) -> EntityType | None:
        model = await self._get(value, field=field)

        if not model:
            return None

        update_data = data.model_dump(exclude_unset=True, exclude_none=True)  # pyright: ignore[reportAttributeAccessIssue]
        for key, v in update_data.items():
            if key in model.get_field_names():  # pyright: ignore[reportAttributeAccessIssue]
                setattr(model, key, v)
        self._session.add(model)

        return self._to_entity(model)

    async def delete(self, value: Any, field: str = "id") -> None:
        model = await self._get(value, field=field)

        if not model:
            return

        if self._is_soft_deletable:
            await self._soft_delete(model)
        else:
            await self._session.delete(model)

    async def restore(self, value: Any, field: str = "id") -> EntityType | None:
        model = await self._get(value, field=field, with_deleted=True)

        if not model:
            return None

        model.deleted_at = None  # pyright: ignore[reportAttributeAccessIssue]
        self._session.add(model)

        cascades = getattr(model, "__soft_delete_cascades__", ())
        for cascade_attr in cascades:
            related_objects = getattr(model, cascade_attr)
            if related_objects is None:
                continue

            if (
                isinstance(related_objects, SoftDeleteMixin)
                and related_objects.deleted_at is not None
            ):
                related_objects.deleted_at = None
                self._session.add(related_objects)
            elif hasattr(related_objects, "__iter__") and not isinstance(
                related_objects,
                (str, bytes),
            ):
                for related_obj in related_objects:  # pyright: ignore[reportGeneralTypeIssues]
                    if (
                        isinstance(related_obj, SoftDeleteMixin)
                        and related_obj.deleted_at is not None
                    ):
                        related_obj.deleted_at = None
                        self._session.add(related_obj)

        return self._to_entity(model)

    async def _soft_delete(self, model: ModelType) -> None:
        model.deleted_at = func.now()  # pyright: ignore[reportAttributeAccessIssue]
        self._session.add(model)

        cascades = getattr(model, "__soft_delete_cascades__", ())
        if not cascades:
            return

        for cascade_attr in cascades:
            related_objects = getattr(model, cascade_attr)
            if related_objects is None:
                continue

            if isinstance(related_objects, SoftDeleteMixin):
                related_objects.deleted_at = func.now()
                self._session.add(related_objects)
            elif hasattr(related_objects, "__iter__") and not isinstance(
                related_objects,
                (str, bytes),
            ):
                for related_obj in related_objects:
                    if isinstance(related_obj, SoftDeleteMixin):
                        related_obj.deleted_at = func.now()
                        self._session.add(related_obj)

    async def refresh(self, model: EntityType, attribute_names: list[str]) -> None:
        await self._session.refresh(model, attribute_names=attribute_names)

    async def flush(self) -> None:
        await self._session.flush()

    def _to_entity(self, model: ModelType) -> EntityType:
        return self._entity.model_validate(model)  # pyright: ignore[reportAttributeAccessIssue]

    def _select_not_deleted(self) -> Select:
        return select(self._model).where(self._model.deleted_at.is_(None))  # pyright: ignore[reportAttributeAccessIssue]

    def _apply_filters(self, query: Select, filters: dict[str, Any]) -> Select:
        for field, value in filters.items():
            if value is None:
                continue

            if field.endswith("_from"):
                field_name = field[:-5]
                column = getattr(self._model, field_name)
                query = query.where(column >= value)

            elif field.endswith("_to"):
                field_name = field[:-3]
                column = getattr(self._model, field_name)
                query = query.where(column <= value)

            elif field == "search":
                if not self._search_fields:
                    continue

                search_terms = value.strip().split()

                conditions = [
                    or_(*[search_field.ilike(f"%{term}%") for search_field in self._search_fields])
                    for term in search_terms
                ]
                query = query.where(and_(*conditions))

            else:
                column = getattr(self._model, field)
                if isinstance(value, list):
                    query = query.where(column.in_(value))
                else:
                    query = query.where(column == value)

        return query

    def _apply_sorting(self, query: Select, sorting: dict[str, str]) -> Select:
        sort_by = sorting.get("sort_by")
        if sort_by:
            order_by = sorting.get("order_by", "asc")
            column = getattr(self._model, sort_by)
            query = query.order_by(column.desc() if order_by == "desc" else column.asc())

        return query

    async def _apply_pagination(
        self,
        query: Select,
        limit: int | None = None,
        offset: int | None = None,
    ) -> tuple[Select, int]:
        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        if not total:
            total = 0

        query = query.offset(offset).limit(limit)

        return query, total

    def _load_relations(
        self,
        query: Select,
        relations: dict[Literal["select", "joined", "subquery"], list[str]] | None = None,
    ) -> Select:
        if relations:
            for strategy, rels in relations.items():
                for relation_name in rels:
                    if strategy == "joined":
                        loader = joinedload(getattr(self._model, relation_name))
                    elif strategy == "subquery":
                        loader = subqueryload(getattr(self._model, relation_name))
                    else:
                        loader = selectinload(getattr(self._model, relation_name))

                    query = query.options(loader)

        return query
