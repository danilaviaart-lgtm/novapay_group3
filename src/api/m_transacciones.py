import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# MODELO BASE
class TransaccionBase(SQLModel):
    id_usuario: uuid.UUID
    fecha: Optional[datetime] = Field(default=None)
    hora: int
    dias_antiguedad_cuenta: int
    email_verificado: bool
    pais_emision: str = Field(max_length=2)
    categoria: str = Field(max_length=100)
    
    importe: Decimal = Field(sa_column=Column(Numeric(12, 2)))
    
    es_online: bool
    pais_pago: str = Field(max_length=2)
    tipo_tarjeta: str = Field(max_length=50)
    mismo_envio_facturacion: bool
    tipo_dispositivo: str = Field(max_length=50)
    uso_vpn_proxy: bool
    paso_3d_secure: bool
    minutos_desde_ultima_tx: int
    es_fraude: bool
    revisar: bool
    revisado: Optional[str] = Field(default=None, max_length=30)
    tipo_fraude: Optional[str] = Field(default=None, max_length=50)
    

    f_score: Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(5, 2)))
    auditor_fraude: Optional[bool] = Field(default=None)
    shap_reasons: Optional[List[Dict[str, Any]]] = Field(default=None, sa_column=Column(JSON))

# MODELO DE TABLA (Base de Datos)
class Transaccion(TransaccionBase, table=True):
    __tablename__ = "transacciones"  # <--- Nombre exacto en tu BD
    
    __table_args__ = {"extend_existing": True}
    
    id_transaccion: uuid.UUID = Field(
        sa_column=Column(
            "id_transaccion",
            PG_UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4
        )
    )
    analista: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=Column("analista", PG_UUID(as_uuid=True), nullable=True)
    )

# MODELO RESPUESTA
class TransaccionResponse(SQLModel):
    id_transaccion: uuid.UUID
    id_usuario: uuid.UUID
    fecha: Optional[datetime]
    hora: int
    importe: Decimal
    categoria: Optional[str] = None
    es_online: Optional[bool] = None
    tipo_tarjeta: Optional[str] = None
    es_fraude: Optional[bool] = None
    revisar: Optional[bool] = None
    revisado: Optional[str] = None
    f_score: Optional[Decimal] = None
    analista: Optional[uuid.UUID] = None
    auditor_fraude: Optional[bool] = None
    shap_reasons: Optional[List[Dict[str, Any]]] = None
    pais_pago: Optional[str] = None
    pais_emision: Optional[str] = None
    dias_antiguedad_cuenta: Optional[int] = None
    email_verificado: Optional[bool] = None
    minutos_desde_ultima_tx: Optional[int] = None
    mismo_envio_facturacion: Optional[bool] = None
    tipo_dispositivo: Optional[str] = None
    uso_vpn_proxy: Optional[bool] = None
    paso_3d_secure: Optional[bool] = None


# MODELO UPDATE (para ediciones parciales)
class TransaccionUpdate(SQLModel):
    revisado: Optional[str] = Field(default=None, max_length=30)
    tipo_fraude: Optional[str] = Field(default=None, max_length=50)
    es_fraude: Optional[bool] = Field(default=None)
    analista: Optional[uuid.UUID] = Field(default=None,)
    auditor_fraude: Optional[bool] = Field(default=None)