import uuid
from typing import Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType]):
    """
    Generic asynchronous persistence repository providing transaction-safe CRUD abstractions.
    Enforces Rule 02 by encapsulating all SQLAlchemy query mechanics away from service layers.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: uuid.UUID, for_update: bool = False) -> Optional[ModelType]:
        """Retrieve a single entity by primary key with optional row-level locking."""
        stmt = select(self.model).where(self.model.id == id)
        if for_update:
            stmt = stmt.with_for_update()
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_multi(
        self,
        offset: int = 0,
        limit: int = 100,
        order_by: Optional[Any] = None,
    ) -> Sequence[ModelType]:
        """Retrieve a paginated slice of records."""
        stmt = select(self.model).offset(offset).limit(limit)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Return total record count for the entity table."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def create(self, obj_in: Union[BaseModel, Dict[str, Any], ModelType]) -> ModelType:
        """Persist a new entity instance within the current transaction."""
        if isinstance(obj_in, self.model):
            db_obj = obj_in
        elif isinstance(obj_in, BaseModel):
            obj_data = obj_in.model_dump(exclude_unset=True)
            db_obj = self.model(**obj_data)
        elif isinstance(obj_in, dict):
            db_obj = self.model(**obj_in)
        else:
            raise ValueError(f"Unsupported type for repository create: {type(obj_in)}")

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: Union[BaseModel, Dict[str, Any]],
    ) -> ModelType:
        """Update fields on an existing tracked entity."""
        if isinstance(obj_in, dict):
            update_data = obj_in
        elif isinstance(obj_in, BaseModel):
            update_data = obj_in.model_dump(exclude_unset=True)
        else:
            raise ValueError(f"Unsupported type for repository update: {type(obj_in)}")

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete an entity by primary key. Returns True if deleted, False if not found."""
        db_obj = await self.get(id)
        if db_obj is None:
            return False
        await self.session.delete(db_obj)
        await self.session.flush()
        return True
