from typing import TypeVar, Generic, Optional, Dict, Any, List, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID
from ..config.database import DatabaseManager
from .metrics_utils import track_metrics
import threading

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Thread-safe base repository implementation with metrics tracking."""
    
    def __init__(self, model_class: type):
        self.model_class = model_class
        self.db = DatabaseManager.get_instance()
        self._session_lock = threading.Lock()
        # Initialize metrics
        from .repository_metrics import RepositoryMetrics
        from .metrics_config import RepositoryMetricsConfig
        self._metrics = RepositoryMetrics(RepositoryMetricsConfig.create_minimal())
    
    def _get_session(self) -> Session:
        """Get a database session in a thread-safe manner."""
        with self._session_lock:
            return self.db.get_session()
    
    @track_metrics(model_class=T)
    async def find_by_uuid(self, uuid: UUID) -> Optional[T]:
        """Find entity by UUID (internal primary key)."""
        try:
            with self._get_session() as session:
                return session.query(self.model_class).filter_by(uuid=uuid).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error in find_by_uuid: {str(e)}") from e
    
    @track_metrics(model_class=T)
    async def find_by_short_id(self, short_id: str) -> Optional[T]:
        """Find entity by short ID (8-char string for UI)."""
        try:
            with self._get_session() as session:
                return session.query(self.model_class).filter_by(id=short_id).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Database error in find_by_short_id: {str(e)}") from e
    
    @track_metrics(model_class=T)
    async def find_by_id(self, id_value: Union[UUID, str]) -> Optional[T]:
        """
        Find entity by either UUID or short ID.
        Auto-detects type and calls appropriate method.
        
        Args:
            id_value: Either a UUID object, UUID string, or 8-character short ID
            
        Returns:
            Optional[T]: The entity if found, None otherwise
        """
        if isinstance(id_value, UUID):
            return await self.find_by_uuid(id_value)
        elif isinstance(id_value, str):
            if len(id_value) == 8:
                # Assume it's a short ID
                return await self.find_by_short_id(id_value)
            else:
                # Try parsing as UUID string
                try:
                    uuid_obj = UUID(id_value)
                    return await self.find_by_uuid(uuid_obj)
                except (ValueError, AttributeError):
                    return None
        else:
            return None
    
    @track_metrics(model_class=T)
    async def find_many(self, criteria: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> List[T]:
        try:
            with self._get_session() as session:
                query = session.query(self.model_class)
                
                # Apply criteria filters
                for key, value in criteria.items():
                    query = query.filter(getattr(self.model_class, key) == value)
                
                # Apply options if provided
                if options:
                    if 'offset' in options:
                        query = query.offset(options['offset'])
                    if 'limit' in options:
                        query = query.limit(options['limit'])
                    if 'order_by' in options:
                        for field, direction in options['order_by'].items():
                            column = getattr(self.model_class, field)
                            if direction == 'DESC':
                                column = column.desc()
                            query = query.order_by(column)
                
                return query.all()
        except SQLAlchemyError as e:
            # Log error
            raise RuntimeError(f"Database error in find_many: {str(e)}") from e
    
    @track_metrics(model_class=T)
    async def create(self, entity: Dict[str, Any]) -> T:
        try:
            with self._get_session() as session:
                db_entity = self.model_class(**entity)
                session.add(db_entity)
                session.commit()
                session.refresh(db_entity)
                return db_entity
        except SQLAlchemyError as e:
            # Log error
            raise RuntimeError(f"Database error in create: {str(e)}") from e
    
    @track_metrics(model_class=T)
    async def update(self, uuid: UUID, entity: Dict[str, Any]) -> Optional[T]:
        """Update entity by UUID."""
        try:
            with self._get_session() as session:
                db_entity = session.query(self.model_class).filter_by(uuid=uuid).first()
                if not db_entity:
                    return None
                
                for key, value in entity.items():
                    setattr(db_entity, key, value)
                
                session.commit()
                session.refresh(db_entity)
                return db_entity
        except SQLAlchemyError as e:
            # Log error
            raise RuntimeError(f"Database error in update: {str(e)}") from e
    
    @track_metrics(model_class=T)
    async def delete(self, uuid: UUID) -> bool:
        """Delete entity by UUID."""
        try:
            with self._get_session() as session:
                entity = session.query(self.model_class).filter_by(uuid=uuid).first()
                if not entity:
                    return False
                session.delete(entity)
                session.commit()
                return True
        except SQLAlchemyError as e:
            # Log error
            raise RuntimeError(f"Database error in delete: {str(e)}") from e
    
    @track_metrics(model_class=T)
    async def transaction(self, operation):
        """Execute operations within a transaction context."""
        try:
            with self._get_session() as session:
                result = await operation(session)
                session.commit()
                return result
        except Exception as e:
            # Log error
            session.rollback()
            raise RuntimeError(f"Transaction error: {str(e)}") from e
    
    def to_dict(self, entity: T, include_uuid: bool = False) -> Dict[str, Any]:
        """
        Serialize entity for API responses.
        Returns short ID by default, optionally includes UUID.
        
        Args:
            entity: The entity to serialize
            include_uuid: Whether to include the full UUID in response
            
        Returns:
            Dict with entity data, using short ID for 'id' field
        """
        result = {
            "id": entity.id,  # 8-char string for UI
        }
        
        if include_uuid:
            result["uuid"] = str(entity.uuid)
            
        # Add other common fields if they exist
        for attr in ['created_at', 'updated_at']:
            if hasattr(entity, attr):
                value = getattr(entity, attr)
                if value:
                    result[attr] = value.isoformat() if hasattr(value, 'isoformat') else value
        
        return result
