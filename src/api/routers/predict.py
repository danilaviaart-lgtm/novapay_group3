import pandas as pd
import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException, Request, status, Depends

# Importaciones absolutas desde la raíz de tu API (src/api/)
from database import get_valkey  
from routers.schemas import PredictionInput


router = APIRouter()

@router.post("/o")
async def get_prediction(
    request: Request, 
    data: PredictionInput, 
    redis_client: aioredis.Redis = Depends(get_valkey)
):
    try:
        # 1. Recuperamos el modelo del estado de la app
        model = request.app.state.model
        
        # 2. Convertimos los datos entrantes a diccionario
        data_dict = data.dict() 
        
        # 3. Extraemos los IDs para la lógica de validación y negocio
        id_usuario = data_dict.pop("id_usuario", None)
        id_transaccion = data_dict.pop("id_transaccion", None)
        print("TIPO DE OBJETO CARGADO:", type(model))

        # === VALIDACIÓN Y CONTROL DE FLUJO CON VALKEY ===
        if id_usuario is not None:
            key_usuario = f"usuario:{str(id_usuario)}"
            key_ttl = f"intentos_ttl:{str(id_usuario)}"  # Clave espejo para controlar el tiempo
            
            # Traemos TODO el perfil del usuario desde Valkey de una sola llamada
            # Si el usuario no existe, hgetall devuelve un diccionario vacío {}
            perfil_usuario = await redis_client.hgetall(key_usuario)
            
            if not perfil_usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El id_usuario {id_usuario} no existe en la base de datos de Valkey."
                )
            
            # --- FILTRO 1: CONTROL DE BLOQUEO ---
            # hgetall nos devuelve strings, comprobamos el flag de bloqueo
            estado_bloqueo = perfil_usuario.get("bloqueado", "0")
            if estado_bloqueo == "1":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acceso denegado. Este usuario se encuentra bloqueado por exceso de intentos."
                )
            
            # --- FILTRO 2: CONTROL DE TIEMPO (VENTANA DESLIZANTE DE 10 MIN) ---
            tiene_temporizador_activo = await redis_client.exists(key_ttl)
            
            if not tiene_temporizador_activo:
                await redis_client.hset(key_usuario, "intentos", "0")
            
            # --- FILTRO 3: INCREMENTAR INTENTOS Y CONFIGURAR TTL ---
            total_intentos = await redis_client.hincrby(key_usuario, "intentos", 1)
            await redis_client.set(key_ttl, "activo", ex=600)
            
            if total_intentos >= 3:
                await redis_client.hset(key_usuario, "bloqueado", "1")
                await redis_client.delete(key_ttl)
                
                print(f"⚠️ [Valkey] ¡Usuario {id_usuario} BLOQUEADO permanentemente por alcanzar {total_intentos} intentos!")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="El usuario ha sido bloqueado tras alcanzar el límite de 3 intentos."
                )
            
            print(f"[Valkey] Usuario {id_usuario} - Intento: {total_intentos}/3. Ventana de 10 min actualizada.")
            
            # ENRIQUECIMIENTO DE DATOS PARA EL MODELO DE ML ===
            data_dict["email_verificado"] = int(perfil_usuario.get("email_verificado", 0))
            data_dict["dias_antiguedad_cuenta"] = int(perfil_usuario.get("dias_antiguedad_cuenta", 0))
            data_dict["pais_emision"] = str(perfil_usuario.get("pais_emision", "ES"))
            data_dict["paso_3d_secure"] = int(perfil_usuario.get("paso_3d_secure", 0))
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El campo id_usuario es obligatorio."
            )

        #Creamos el DataFrame (ahora ya incluye las 4 columnas de Valkey)
        df_registro = pd.DataFrame([data_dict])
        
        # 5. Predicción del modelo
        prediction = model.predict(df_registro)
        probabilidades = model.predict_proba(df_registro)
        probabilidad_fraude = probabilidades[0][1]
        
        porcentaje_formateado = f"{probabilidad_fraude * 100:.1f}%"

        return {
            "id_usuario": id_usuario,
            "id_transaccion": id_transaccion,
            "prediction": int(prediction[0]),
            "fraud_probability": porcentaje_formateado,
            "total_attempts": total_intentos,
            "blocked": 0
        }

    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Error en la predicción: {str(e)}"
        )