import joblib
import os
import warnings
warnings.filterwarnings('ignore')
os.system('clear')

from shap_explainer import get_explainer, predict_and_explain

pipeline  = joblib.load('models/modelo_fraude_v1.pkl')
explainer = get_explainer(pipeline)

transaccion = {
    'id_transaccion':          '00000000-0000-0000-0000-000000000001',
    'id_usuario':              '11111111-1111-1111-1111-111111111111',
    'fecha':                   '2026-01-12 14:30:00',
    'dias_antiguedad_cuenta':  365,
    'email_verificado':        1,
    'pais_emision':            'ES',
    'categoria':               'Electrónica',
    'importe':                 10.02,
    'es_online':               1,
    'pais_pago':               'ES',
    'tipo_tarjeta':            'Crédito',
    'mismo_envio_facturacion': 1,
    'tipo_dispositivo':        'Móvil',
    'uso_vpn_proxy':           0,
    'paso_3d_secure':          1,
}

resultado = predict_and_explain(pipeline, explainer, transaccion)

print(f'Probabilidad legítima: {resultado["probabilidad_legitima"]:.4f}')
print(f'Probabilidad fraude:   {resultado["probabilidad_fraude"]:.4f}')
print(f'Threshold:             {resultado["threshold"]}')
print(f'Decisión:              {"FRAUDE" if resultado["es_fraude"] else "LEGÍTIMA"}')
print(f'Nivel de riesgo:       {resultado["nivel_riesgo"]}')

print(f'\nRazones fraude:')
for i, f in enumerate(resultado['razones_fraude'], 1):
    print(f"  {i}. {f['feature']:<35} +{f['impacto']:.3f}")

print(f'\nRazones legítima:')
for i, f in enumerate(resultado['razones_legitima'], 1):
    print(f"  {i}. {f['feature']:<35} {f['impacto']:.3f}")