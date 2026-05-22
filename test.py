import joblib
import pandas as pd
from utils.utils import feature_engineering  # necesario para deserializar el FunctionTransformer
import os


# 1) Cargar pipeline entrenado (preprocesado + modelo)
pipeline = joblib.load('models/modelo_fraude_v1.pkl')

THRESHOLD = 0.50

# 2) Transacción a evaluar (estructura raw exacta: 15 campos, sin es_fraude)
transaccion = {
    'nombre': 'Transacción legítima',  # solo display, no entra al modelo
    'id_transaccion': '00000000-0000-0000-0000-000000000001',
    'id_usuario':     '11111111-1111-1111-1111-111111111111',
    'fecha': '2026-01-12 14:30:00',
    'dias_antiguedad_cuenta': 1,
    'email_verificado': 1,
    'pais_emision': 'ES',
    'categoria': 'Electrónica',
    'importe': 1.02,
    'es_online': 1,
    'pais_pago': 'FR',
    'tipo_tarjeta': 'Crédito',
    'mismo_envio_facturacion': 1,
    'tipo_dispositivo': 'Móvil',
    'uso_vpn_proxy': 0,
    'paso_3d_secure': 1,
}

# 3) Convertir a DataFrame (filtra 'nombre', que no es columna del modelo)
df = pd.DataFrame([{k: v for k, v in transaccion.items() if k != 'nombre'}])

# 4) Predecir: el pipeline aplica FE + scaler/OHE + XGB internamente
#    (FE deriva 'hora' de 'fecha' y descarta los ids automáticamente)
proba = pipeline.predict_proba(df)[:, 1][0]
es_fraude = proba >= THRESHOLD

# 5) Resultado
os.system('clear')  # Mac/Linux
print(f'Transacción:           {transaccion["nombre"]}')
print(f'Probabilidad legítima: {1 - proba:.4f}')
print(f'Probabilidad fraude:   {proba:.4f}')
print(f'Threshold:             {THRESHOLD}')
print(f'Decisión:              {"FRAUDE" if es_fraude else "LEGÍTIMA"}')
