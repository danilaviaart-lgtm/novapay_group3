from typing import Optional
from datetime import datetime
from pydantic import UUID4
from sqlmodel import SQLModel, Field
from sqlalchemy import Column, String, Integer, Boolean, Numeric
from sqlalchemy.dialects.postgresql import UUID

class Cliente(SQLModel, table=True):
    __tablename__: str = "clientes"

    id_usuario: UUID4 = Field(
        default=None,
        primary_key=True,
        index=True,
        alias="id_usuario"
    )
    intentos: int = Field(default=0)
    bloqueado: bool = Field(default=False)
    ultima_actualizacion: Optional[datetime] = Field(default=None)
    
    # Atributos históricos mapeados
    dias_antiguedad_cuenta: int = Field(default=0)
    email_verificado: bool = Field(default=False)
    pais_emision: str = Field(default="ES")
    paso_3d_secure: bool = Field(default=False)


class Transaccion(SQLModel, table=True):
    __tablename__: str = "transacciones"

    id_transaccion: UUID4 = Field(default=None, primary_key=True, alias="id_transaccion")
    id_usuario: UUID4 = Field(default=None, index=True, alias="id_usuario")
    
    fecha: datetime = Field(nullable=False)
    hora: int = Field(sa_column=Column(Integer, nullable=False))
    
    dias_antiguedad_cuenta: int = Field(default=0)
    email_verificado: bool = Field(default=False)
    pais_emision: str = Field(default="ES")
    categoria: Optional[str] = Field(default=None)
    importe: float = Field(default=0.0)
    es_online: bool = Field(default=False)
    pais_pago: Optional[str] = Field(default=None)
    tipo_tarjeta: Optional[str] = Field(default=None)
    mismo_envio_facturacion: Optional[bool] = Field(default=None)
    tipo_dispositivo: Optional[str] = Field(default=None)
    uso_vpn_proxy: Optional[bool] = Field(default=None)
    paso_3d_secure: bool = Field(default=False)
    minutos_desde_ultima_tx: Optional[float] = Field(default=None)
    
    f_score: Optional[float] = Field(default=None)
    es_fraude: bool = Field(default=False)
    revisar: bool = Field(default=False)
    revisado: Optional[str] = Field(default=None)
    tipo_fraude: Optional[str] = Field(default=None)