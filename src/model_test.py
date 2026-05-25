import joblib
import pandas as pd
from utils.utils import feature_engineering
import random


# Cargar artifact
artifact = joblib.load('models/modelo_fraude_v1.pkl')
pipeline    = artifact['pipeline']
threshold   = artifact['threshold']
paises_riesgo = artifact['paises_alto_riesgo']
categorias_riesgo = artifact['categorias_alto_riesgo']

# Transacción de prueba (datos raw tal como llegarían)
transacciones = [
    {
        'nombre': 'Transacción sospechosa',
        'fecha': '2025-03-15 03:22:00',
        'hora': 3,
        'dias_antiguedad_cuenta': 12,
        'email_verificado': 0,
        'pais_emision': 'ES',
        'categoria': 'Electrónica',
        'importe': 899.99,
        'es_online': 1,
        'pais_pago': 'RU',
        'tipo_tarjeta': 'Prepago',
        'mismo_envio_facturacion': 0,
        'tipo_dispositivo': 'Desktop',
        'uso_vpn_proxy': 1,
        'paso_3d_secure': 0,
        'minutos_desde_ultima_tx': 2.0,
    },
    {
        'nombre': 'Transacción legítima',
        'fecha': '2025-06-10 14:30:00',
        'hora': 14,
        'dias_antiguedad_cuenta': 365,
        'email_verificado': 1,
        'pais_emision': 'ES',
        'categoria': 'Electrónica',
        'importe': 299.99,
        'es_online': 1,
        'pais_pago': 'ES',
        'tipo_tarjeta': 'Crédito',
        'mismo_envio_facturacion': 1,
        'tipo_dispositivo': 'Móvil',
        'uso_vpn_proxy': 0,
        'paso_3d_secure': 1,
        'minutos_desde_ultima_tx': 43200.0,
    }
]

elegida = random.choice(transacciones)
print(f'Transacción elegida: {elegida["nombre"]}')
print()

# Predecir
df = pd.DataFrame([{k: v for k, v in elegida.items() if k != 'nombre'}])
proba = pipeline.predict_proba(df)[:, 1][0]
es_fraude = proba >= threshold

print(f'Probabilidad legítima: {1-proba:.4f}')
print(f'Probabilidad fraude:   {proba:.4f}')
print(f'Threshold:             {threshold}')
print(f'Decisión:              {"🚨 FRAUDE" if es_fraude else "✅ LEGÍTIMA"}')
print(f'Nivel de riesgo:       {"ALTO" if proba >= 0.7 else "MEDIO" if proba >= threshold else "BAJO"}')