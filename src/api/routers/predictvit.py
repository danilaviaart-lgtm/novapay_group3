import pandas as pd
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from database import get_db  
from models import Cliente, Transaccion
from routers.schemas import PredictionInput

router = APIRouter()

@router.post("/predict")
async def get_prediction(
    request: Request, 
    data: PredictionInput, 
    db: AsyncSession = Depends(get_db)
):
    try:
        model = request.app.state.model
        
        # =====================================================================
        # ESCUDO DE SEGURIDAD: COMPROBADOR PREVIO PARA EVITAR DUPLICADOS
        # =====================================================================
        # Buscamos si la transacción entrante ya fue registrada previamente
        stmt_tx = select(Transaccion).where(Transaccion.id_transaccion == data.id_transaccion)
        result_tx = await db.execute(stmt_tx)
        tx_existente = result_tx.scalars().first()
        
        if tx_existente:
            # Si ya existe, calculamos de nuevo el string de probabilidad para mantener el formato
            # Nota: Si en base de datos no guardas la probabilidad exacta sino un bool, puedes adaptarlo.
            # Aquí asumimos que devolvemos un mensaje de éxito indicando que ya estaba procesada.
            return {
                "id_usuario": tx_existente.id_usuario,
                "id_transaccion": tx_existente.id_transaccion,
                "prediction": int(1 if tx_existente.es_fraude else 0),
                "fraud_probability": "Ya calculada (Duplicado)",
                "total_attempts": "N/A",
                "blocked": True if tx_existente.es_fraude else False, # Mapeo lógico simulado
                "fecha_registro": tx_existente.fecha.strftime("%Y-%m-%d %H:%M:%S"),
                "status_interno": "Omitido por duplicidad (Ya existía en la base de datos)"
            }

        # =====================================================================
        # 1. CONTROL DE INTENTOS Y BLOQUEO DE USUARIO (CORREGIDO A BOOLEANO)
        # =====================================================================
        statement = select(Cliente).where(Cliente.id_usuario == data.id_usuario)
        result = await db.execute(statement)
        cliente = result.scalars().first()
        
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El id_usuario {data.id_usuario} no existe en la base de datos."
            )
        
        # CORRECCIÓN: Comprobación estricta con True (Booleano) en lugar de 1
        if cliente.bloqueado is True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado. Este usuario se encuentra bloqueado."
            )
        
        # Estampa local naive para compatibilidad con la columna de la BD
        ahora_naive = datetime.now()
        
        if cliente.ultima_actualizacion:
            if cliente.ultima_actualizacion.tzinfo is not None:
                ultima_act_pure = cliente.ultima_actualizacion.replace(tzinfo=None)
            else:
                ultima_act_pure = cliente.ultima_actualizacion
            
            segundos_transcurridos = (ahora_naive - ultima_act_pure).total_seconds()
            if segundos_transcurridos > 600:
                cliente.intentos = 0
        else:
            cliente.intentos = 0
        
        cliente.intentos += 1
        cliente.ultima_actualizacion = ahora_naive  
        
        if cliente.intentos >= 3:
            # CORRECCIÓN: Asignamos True (Booleano) en lugar de 1 para evitar DatatypeMismatchError
            cliente.bloqueado = True
            db.add(cliente)
            await db.commit()  
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario ha sido bloqueado tras alcanzar el límite de 3 intentos."
            )
        
        db.add(cliente)

        # =====================================================================
        # 2. CONSOLIDACIÓN DE FEATURES PARA EL MODELO DE ML
        # =====================================================================
        fecha_string_ml = ahora_naive.strftime("%Y-%m-%d %H:%M:%S")

        features_totales = {
            "fecha": fecha_string_ml,  
            "importe": float(data.importe),
            "categoria": str(data.categoria),
            "es_online": int(data.es_online),
            "pais_pago": str(data.pais_pago),
            "tipo_tarjeta": str(data.tipo_tarjeta),
            "mismo_envio_facturacion": int(data.mismo_envio_facturacion),
            "tipo_dispositivo": str(data.tipo_dispositivo),
            "uso_vpn_proxy": int(data.uso_vpn_proxy),
            
            # Datos históricos de la base de datos
            "dias_antiguedad_cuenta": int(cliente.dias_antiguedad_cuenta or 0),
            "email_verificado": int(1 if cliente.email_verificado else 0),
            "pais_emision": str(cliente.pais_emision or "ES"),
            "paso_3d_secure": int(1 if cliente.paso_3d_secure else 0)
        }

        # =====================================================================
        # 3. CONSTRUCCIÓN DEL DATAFRAME E INFERENCIA
        # =====================================================================
        df_registro = pd.DataFrame([features_totales])
        
        prediction = model.predict(df_registro)
        probabilidades = model.predict_proba(df_registro)
        probabilidad_fraude = probabilidades[0][1]
        
        es_fraude_bool = bool(prediction[0] == 1)
        requiere_revisar = bool(0.30 <= probabilidad_fraude <= 0.50)

        # =====================================================================
        # 4. INSERCIÓN DEL HISTORIAL EN LA TABLA TRANSACCIONES
        # =====================================================================
        nueva_transaccion = Transaccion(
            id_transaccion=data.id_transaccion,
            id_usuario=data.id_usuario,
            fecha=ahora_naive,
            hora=int(ahora_naive.hour), 
            dias_antiguedad_cuenta=cliente.dias_antiguedad_cuenta,
            email_verificado=bool(cliente.email_verificado),
            pais_emision=cliente.pais_emision,
            categoria=data.categoria,
            importe=data.importe,
            es_online=bool(data.es_online),
            pais_pago=data.pais_pago,
            tipo_tarjeta=data.tipo_tarjeta,
            mismo_envio_facturacion=bool(data.mismo_envio_facturacion),
            tipo_dispositivo=data.tipo_dispositivo,
            uso_vpn_proxy=bool(data.uso_vpn_proxy),
            paso_3d_secure=bool(cliente.paso_3d_secure),
            minutos_desde_ultima_tx=data.minutos_desde_ultima_tx,
            es_fraude=es_fraude_bool,
            f_score=probabilidad_fraude,
            revisar=requiere_revisar,
            revisado="Pendiente" if requiere_revisar else "No requerido"
        )
        
        db.add(nueva_transaccion)
        await db.commit()  
        
        porcentaje_formateado = f"{probabilidad_fraude * 100:.1f}%"

        return {
            "id_usuario": data.id_usuario,
            "id_transaccion": data.id_transaccion,
            "prediction": int(prediction[0]),
            "fraud_probability": porcentaje_formateado,
            "total_attempts": cliente.intentos,
            # CORRECCIÓN: Devolvemos el estado booleano real o mapeado a int si tu frontend lo exige obligatoriamente
            "blocked": cliente.bloqueado, 
            "fecha_registro": fecha_string_ml
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        await db.rollback()  
        import traceback
        traceback.print_exc() 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error en la predicción: {str(e)}"
        )