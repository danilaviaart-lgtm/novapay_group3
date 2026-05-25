import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# MODELO BASE
class UsuarioBase(SQLModel):
    nombre: str = Field(max_length=30)
    apellido: str = Field(max_length=30)
    dni: str = Field(max_length=20)
    email: str = Field(max_length=150) 
    email_verificado: bool = Field(default=False)
    dias_antiguedad_cuenta: int
<<<<<<< HEAD
    pais_emision: str = Field(max_length=2)
=======
    pais_emision: str = Field(max_length=2)  # <--- Corregido: una sola 's'
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
    paso_3d_secure: bool = Field(default=False)
    bloqueado: bool = Field(default=False)
    intentos: int = Field(default=0)
    intentos_expires_at: Optional[datetime] = Field(default=None)
    ultima_actualizacion: Optional[datetime] = Field(default=None)


# MODELO BASE TABLA (con ID y configuración de tabla)
class Usuario(UsuarioBase, table=True):
    __tablename__ = "clientes" 
    
    __table_args__ = {"extend_existing": True}
    
    Clienteid: uuid.UUID = Field(
        sa_column=Column(
            "id_usuario",          
            PG_UUID(as_uuid=True), 
            primary_key=True, 
            default=uuid.uuid4
        )
    )


# RESPUESTA (sin campos de auditoría ni intentos)
class UsuarioResponse(SQLModel):
    Clienteid: uuid.UUID
    nombre: str
    apellido: str
    dni: str
    email: str
    email_verificado: bool
    dias_antiguedad_cuenta: int
<<<<<<< HEAD
    pais_emision: str                       
=======
    pais_emision: str                        # <--- Corregido: una sola 's'
>>>>>>> c70af591b624600266f2a9549b6bccb72c2f5d5a
    paso_3d_secure: bool
    bloqueado: bool
    ultima_actualizacion: Optional[datetime] = None


# EDICIÓN UPDATE
class UsuarioUpdate(SQLModel):
    nombre: Optional[str] = Field(default=None, max_length=30)
    apellido: Optional[str] = Field(default=None, max_length=30)
    dni: Optional[str] = Field(default=None, max_length=20)
    email: Optional[str] = Field(default=None, max_length=150)
    pais_emision: Optional[str] = Field(default=None, max_length=2)
    paso_3d_secure: Optional[bool] = Field(default=None)
    bloqueado: Optional[bool] = Field(default=None)