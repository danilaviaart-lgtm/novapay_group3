import pandas as pd
from fastapi import APIRouter, HTTPException, Request, status, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from database import get_db  
from models import Cliente, Transaccion
from helpers import preparar_para_postgres
from routers.schemas import PredictionInput

# IMPORTAMOS LA FUNCIÓN DE INFERENCIA Y EXPLICACIÓN DE TU SHAP_EXPLAINER
from utils.shap_explainer import predict_and_explain

router = APIRouter()

@router.post("/")
async def get_prediction(
    request: Request, 
    data: PredictionInput, 
    db: AsyncSession = Depends(get_db)
):
    try:
        pipeline = request.app.state.model
        explainer = request.app.state.shap_explainer
        
        # 1. CONTROL TRANSACCIÓN DUPLICADOS
        stmt_tx = select(Transaccion).where(Transaccion.id_transaccion == data.id_transaccion)
        result_tx = await db.execute(stmt_tx)
        tx_existente = result_tx.scalars().first()
        
        if tx_existente:
            return {
                "id_usuario": tx_existente.id_usuario,
                "id_transaccion": tx_existente.id_transaccion,
                "prediction": int(1 if tx_existente.es_fraude else 0),
                "fraud_probability": "Ya calculada (Duplicado)",
                "total_attempts": "N/A",
                "blocked": True if tx_existente.es_fraude else False, 
                "fecha_registro": tx_existente.fecha.strftime("%Y-%m-%d %H:%M:%S"),
                "status_interno": "Omitido por duplicidad (Ya existía en la base de datos)",
                "shap_reasons": []
            }
            
        # 2. CONTROL USUARIO INTENTOS E ID
        statement = select(Cliente).where(Cliente.id_usuario == data.id_usuario)
        result = await db.execute(statement)
        cliente = result.scalars().first()
        
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El id_usuario {data.id_usuario} no existe en la base de datos."
            )
        
        if cliente.bloqueado is True:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acceso denegado. Este usuario se encuentra bloqueado."
            )
        
        ahora_naive = datetime.now()
        
        # Ventana de tiempo para reiniciar intentos (10 minutos)
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
            cliente.bloqueado = True
            db.add(cliente)
            await db.commit()  
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario ha sido bloqueado tras alcanzar el límite de 3 intentos."
            )
        
        db.add(cliente)

        # 3. FEATURES PARA MODEL ML API + BD
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
            
            "dias_antiguedad_cuenta": int(cliente.dias_antiguedad_cuenta or 0),
            "email_verificado": int(1 if cliente.email_verificado else 0),
            "pais_emision": str(cliente.pais_emision or "ES"),
            "paso_3d_secure": int(1 if cliente.paso_3d_secure else 0)
        }

        # 4. INFERENCIA Y CÁLCULO DE SHAP A TRAVÉS DE TU MÓDULO UNIFICADO
        resultado_ml = predict_and_explain(pipeline, explainer, features_totales, threshold=0.50)

        # 5. REUNIÓN DATOS PARA BD (Incluyendo la columna nativa shap_reasons)
        datos_transaccion = {
            "id_transaccion": data.id_transaccion,
            "id_usuario": data.id_usuario,
            "fecha": ahora_naive,
            "hora": int(ahora_naive.hour), 
            "minutos_desde_ultima_tx": data.minutos_desde_ultima_tx,
            "importe": data.importe,
            "categoria": data.categoria,
            "es_online": bool(data.es_online),
            "pais_pago": data.pais_pago,
            "tipo_tarjeta": data.tipo_tarjeta,
            "mismo_envio_facturacion": bool(data.mismo_envio_facturacion),
            "tipo_dispositivo": data.tipo_dispositivo,
            "uso_vpn_proxy": bool(data.uso_vpn_proxy),
            "dias_antiguedad_cuenta": cliente.dias_antiguedad_cuenta,
            "email_verificado": bool(cliente.email_verificado),
            "pais_emision": cliente.pais_emision,
            "paso_3d_secure": bool(cliente.paso_3d_secure),
            "es_fraude": resultado_ml['es_fraude'],
            "f_score": resultado_ml['probabilidad_fraude'],  
            "revisar": True if 0.30 <= resultado_ml['probabilidad_fraude'] <= 0.50 else False,
            "revisado": "Pendiente" if (0.30 <= resultado_ml['probabilidad_fraude'] <= 0.50) else "No requerido",
            
            # Unimos las razones positivas (incrementa riesgo) y negativas (reduce riesgo) en una sola lista JSON
            "shap_reasons": resultado_ml['razones_fraude'] + resultado_ml['razones_legitima']
        }
        
        # 6. VARIABLE LIMPIA DATOS NUMPY PREDICT Y PERSISTENCIA REAL
        datos_sanitizados = preparar_para_postgres(datos_transaccion)
        
        nueva_transaccion = Transaccion(**datos_sanitizados)
        
        db.add(nueva_transaccion)
        await db.commit()  
        
        porcentaje_formateado = f"{datos_sanitizados['f_score'] * 100:.1f}%"

        # 7. RETORNO DE LA RESPUESTA
        return {
            "id_usuario": data.id_usuario,
            "id_transaccion": data.id_transaccion,
            "prediction": int(1 if resultado_ml['es_fraude'] else 0),
            "fraud_probability": porcentaje_formateado,
            "total_attempts": cliente.intentos,
            "blocked": cliente.bloqueado, 
            "fecha_registro": fecha_string_ml,
            "shap_reasons": nueva_transaccion.shap_reasons  
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