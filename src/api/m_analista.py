import uuid
<<<<<<< HEAD
import enum
=======
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
<<<<<<< HEAD
from sqlalchemy import Enum as SA_Enum  # Importamos el Enum de SQLAlchemy

# 1. Definimos el Enum en Python con los mismos valores exactos de tu BD
class RolUsuario(str, enum.Enum):
    Admin = "Admin"
    Analyst = "Analyst"

# MODELO BASE
=======

#MODELO BASE
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
class UsuarioPlataformaBase(SQLModel):
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=150)
    nombre: str = Field(max_length=50)
<<<<<<< HEAD
    
    # 2. Modificamos el campo 'rol' para que use el Enum
    # sa_type le indica a SQLAlchemy el tipo de dato nativo de la BD
    rol: RolUsuario = Field(
        default=RolUsuario.Analyst,
        sa_type=SA_Enum(RolUsuario, name="enum_usuarios_rol", create_type=False)
    )
    activo: bool = Field(default=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)

# MODELO TABLA ANALISTA
class UsuarioPlataforma(UsuarioPlataformaBase, table=True):
    __tablename__ = "analistas"
=======
    rol: str = Field(default="analista", max_length=20)
    activo: bool = Field(default=True)
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
# MODELO TABLA ANALISTA
class UsuarioPlataforma(UsuarioPlataformaBase, table=True):
    __tablename__ = "analistas"  # <--- Forzamos el nombre exacto que usa tu BD
    
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
    __table_args__ = {"extend_existing": True}
    
    id: uuid.UUID = Field(
        sa_column=Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        )
    )
    password_hash: str = Field(max_length=255)