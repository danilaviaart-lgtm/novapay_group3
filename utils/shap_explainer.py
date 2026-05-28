# shap_explainer.py
import numpy as np
import shap
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

TEMPLATES = {
    'hora_madrugada':                'transacción en horario de madrugada (0-5h)',
    'pais_alto_riesgo':              'el país de pago tiene alta tasa de fraude histórica',
    'categoria_alto_riesgo':         'la categoría pertenece a un grupo de alto riesgo',
    'es_fin_de_semana':              'transacción realizada en fin de semana',
    'hora':                          'hora inusual para el perfil del usuario',
    'es_online':                     'transacción realizada online',
    'categoria_Electrónica':         'categoría Electrónica de alto riesgo',
    'categoria_Viajes':              'categoría Viajes de alto riesgo',
    'categoria_Restaurante':         'categoría Restaurante',
    'categoria_Supermercado':        'categoría Supermercado',
    'categoria_Salud':               'categoría Salud',
    'categoria_Suscripciones':       'categoría Suscripciones',
    'pais_pago_RU':                  'pago realizado en Rusia, país de alto riesgo',
    'pais_pago_CN':                  'pago realizado en China, país de alto riesgo',
    'pais_pago_IN':                  'pago realizado en India, país de alto riesgo',
    'pais_pago_MX':                  'pago realizado en México',
    'pais_pago_BR':                  'pago realizado en Brasil',
    'pais_pago_ES':                  'pago realizado en España',
    'pais_pago_FR':                  'pago realizado en Francia',
    'pais_pago_DE':                  'pago realizado en Alemania',
    'pais_pago_GB':                  'pago realizado en Reino Unido',
    'pais_pago_US':                  'pago realizado en Estados Unidos',
    'pais_pago_IT':                  'pago realizado en Italia',
    'pais_pago_PT':                  'pago realizado en Portugal',
    'pais_pago_JP':                  'pago realizado en Japón',
    'tipo_dispositivo_Desktop':      'acceso desde Desktop',
    'tipo_dispositivo_Móvil':        'acceso desde móvil',
    'tipo_dispositivo_Tablet':       'acceso desde tablet',
    'tipo_dispositivo_Físico (TPV)': 'pago en terminal físico',
    'tipo_tarjeta_Prepago':          'tarjeta de prepago',
    'tipo_tarjeta_Crédito':          'tarjeta de crédito',
    'tipo_tarjeta_Débito':           'tarjeta de débito',
    'mes':                           'mes con patrón inusual',
    'dia_semana':                    'día de la semana inusual',
}


def get_template(feature, impacto):
    if feature == 'pais_distinto':
        return 'países de emisión y pago distintos' if impacto > 0 \
               else 'países de emisión y pago coinciden'
    if feature == 'online_sin_3ds':
        return 'compra online sin verificación 3D Secure' if impacto > 0 \
               else 'compra online con 3D Secure activo'
    if feature == 'paso_3d_secure':
        return 'sin verificación 3D Secure' if impacto > 0 \
               else '3D Secure activo'
    if feature == 'uso_vpn_proxy':
        return 'uso de VPN o proxy detectado' if impacto > 0 \
               else 'sin VPN ni proxy'
    if feature == 'mismo_envio_facturacion':
        return 'envío y facturación no coinciden' if impacto > 0 \
               else 'envío y facturación coinciden'
    if feature == 'email_verificado':
        return 'email no verificado' if impacto > 0 \
               else 'email verificado'
    if feature == 'dias_antiguedad_cuenta':
        return 'cuenta con poca antigüedad' if impacto > 0 \
               else 'cuenta con buena antigüedad'
    if feature == 'importe':
        return 'importe inusualmente alto' if impacto > 0 \
               else 'importe dentro de lo habitual'
    if feature.startswith('pais_emision_'):
        return None
    return TEMPLATES.get(feature, feature.replace('_', ' '))


def generar_resumen(razones_fraude, razones_legitima, score):
    nivel = 'ALTO' if score >= 0.7 else 'MEDIO' if score >= 0.5 else 'BAJO'

    return {
        'nivel':            nivel,
        'score':            f"{score*100:.0f}%",
        'razones_fraude':   [
            r['descripcion'] for r in razones_fraude
            if r.get('descripcion') is not None
        ],
        'razones_legitima': [
            r['descripcion'] for r in razones_legitima
            if r.get('descripcion') is not None
        ]
    }


def get_explainer(pipeline):
    return shap.TreeExplainer(pipeline['clf'])


def explain(pipeline, explainer, df):
    df_fe         = pipeline['fe'].transform(df)
    X_transformed = pipeline['preprocessor'].transform(df_fe)
    shap_values   = explainer.shap_values(X_transformed)[0]

    num_cols     = list(pipeline['preprocessor'].transformers_[0][2])
    cat_cols     = list(pipeline['preprocessor'].transformers_[1][2])
    ohe_features = pipeline['preprocessor'].named_transformers_['cat'].get_feature_names_out().tolist()
    passthrough  = [c for c in df_fe.columns if c not in num_cols + cat_cols]
    all_features = num_cols + ohe_features + passthrough

    indices = np.argsort(np.abs(shap_values))[::-1][:5]

    razones_fraude = [
        {
            'feature':     all_features[i],
            'impacto':     round(float(shap_values[i]), 3),
            'descripcion': get_template(all_features[i], shap_values[i])
        }
        for i in indices
        if shap_values[i] > 0 and get_template(all_features[i], shap_values[i]) is not None
    ]

    razones_legitima = [
        {
            'feature':     all_features[i],
            'impacto':     round(float(shap_values[i]), 3),
            'descripcion': get_template(all_features[i], shap_values[i])
        }
        for i in indices
        if shap_values[i] < 0 and get_template(all_features[i], shap_values[i]) is not None
    ]

    return razones_fraude, razones_legitima


def predict_and_explain(pipeline, explainer, transaccion: dict, threshold: float = 0.50):
    df        = pd.DataFrame([transaccion])
    df_fe     = pipeline['fe'].transform(df)
    X_tr      = pipeline['preprocessor'].transform(df_fe)
    proba     = pipeline['clf'].predict_proba(X_tr)[:, 1][0]
    es_fraude = proba >= threshold

    razones_fraude, razones_legitima = explain(pipeline, explainer, df)
    resumen = generar_resumen(razones_fraude, razones_legitima, proba)

    return {
        'probabilidad_fraude':   round(proba, 4),
        'probabilidad_legitima': round(1 - proba, 4),
        'es_fraude':             bool(es_fraude),
        'nivel_riesgo':          'ALTO' if proba >= 0.7 else 'MEDIO' if proba >= threshold else 'BAJO',
        'threshold':             threshold,
        'razones_fraude':        razones_fraude,
        'razones_legitima':      razones_legitima,
        'resumen':               resumen,
    }