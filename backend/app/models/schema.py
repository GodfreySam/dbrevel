"""Schema models"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Literal


class ColumnSchema(BaseModel):
    """Database column schema"""
    name: str
    type: str
    nullable: bool
    primary_key: bool = False
    foreign_key: Optional[str] = None


class TableSchema(BaseModel):
    """Database table schema"""
    name: str
    columns: List[ColumnSchema]
    indexes: List[str] = []
    row_count: Optional[int] = None


class DatabaseSchema(BaseModel):
    """Complete database schema"""
    type: Literal["postgres", "mongodb"]
    name: str
    tables: Dict[str, TableSchema] = {}  # For SQL
    collections: Dict[str, Dict[str, Any]] = {}  # For NoSQL
    relationships: List[Dict[str, str]] = []
