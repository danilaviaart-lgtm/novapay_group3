from pydantic import UUID4, BaseModel

class PredictionInput(BaseModel):
    #campos del modelo
    id_transaccion: UUID4
    id_usuario: UUID4
    #hora: int
    #dias_antiguedad_cuenta: int
    #email_verificado: int
    #pais_emision: str
    categoria: str
    importe: float
    es_online: int
    pais_pago: str
    tipo_tarjeta: str
    mismo_envio_facturacion: int
    tipo_dispositivo: str
    uso_vpn_proxy: int
    #paso_3d_secure: int
    minutos_desde_ultima_tx: float

    model_config = {
        "json_schema_extra": {
            "example": {
            "id_transaccion": "4f3b2a1c-7d6e-4b5a-9f8e-7d6c5b4a3f2e",
            "id_usuario": "c9a8b7c6-d5e4-4f3b-a2b1-c0d9e8f7a6b5",
            "categoria": "Supermercado",
            #"dias_antiguedad_cuenta": 9,
            #"email_verificado": 0,
            "es_online": 1,
            #"hora": 14,
            "importe": 20.5,
            "minutos_desde_ultima_tx": 1,
            "mismo_envio_facturacion": 1,
            #"pais_emision": "ES",
            "pais_pago": "CH",
            #"paso_3d_secure": 0,
            "tipo_dispositivo": "Móvil",
            "tipo_tarjeta": "Crédito",
            "uso_vpn_proxy": 1
            }
        }
    }
