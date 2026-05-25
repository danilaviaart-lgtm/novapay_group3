import numpy as np
import shap
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def get_explainer(pipeline):
    """
    Inicializa el TreeExplainer a partir del clasificador del pipeline.
    Soporta formatos crudos o accesos por clave del Pipeline.
    """
    try:
        # Intentamos extraer el clasificador según la estructura de tu pipeline
        if isinstance(pipeline, dict) and 'clf' in pipeline:
            return shap.TreeExplainer(pipeline['clf'])
        elif hasattr(pipeline, 'named_steps') and 'clf' in pipeline.named_steps:
            return shap.TreeExplainer(pipeline.named_steps['clf'])
        else:
            return shap.TreeExplainer(pipeline)
    except Exception as e:
        print(f"Error al inicializar TreeExplainer nativo: {e}. Activando modo genérico.")
        # Fallback de seguridad agnóstico si falla la optimización de árboles por tipos de C++
        return shap.Explainer(pipeline['clf'].predict_proba)

def explain(pipeline, explainer, df):
    # 1. Aplicamos las transformaciones del pipeline de forma secuencial
    df_fe = pipeline['fe'].transform(df)
    X_transformed = pipeline['preprocessor'].transform(df_fe)
    
    # 2. Calculamos los valores SHAP
    shap_values = explainer.shap_values(X_transformed)[0]

    # 3. Reconstruimos los nombres de las columnas post-procesamiento (Numéricas + Categóricas OHE)
    num_cols = list(pipeline['preprocessor'].transformers_[0][2])
    cat_cols = list(pipeline['preprocessor'].transformers_[1][2])
    ohe_features = pipeline['preprocessor'].named_transformers_['cat'].get_feature_names_out().tolist()
    passthrough = [c for c in df_fe.columns if c not in num_cols + cat_cols]
    all_features = num_cols + ohe_features + passthrough

    # 4. Extraemos el Top 5 de variables con mayor impacto absoluto
    indices = np.argsort(np.abs(shap_values))[::-1][:5]
    
    razones_fraude = [
        {'feature': all_features[i], 'impacto': round(float(shap_values[i]), 3)}
        for i in indices if shap_values[i] > 0
    ]
    razones_legitima = [
        {'feature': all_features[i], 'impacto': round(float(shap_values[i]), 3)}
        for i in indices if shap_values[i] < 0
    ]

    return razones_fraude, razones_legitima

def predict_and_explain(pipeline, explainer, transaccion: dict, threshold: float = 0.50):
    df = pd.DataFrame([transaccion])
    df_fe = pipeline['fe'].transform(df)
    X_tr = pipeline['preprocessor'].transform(df_fe)
    
    proba = pipeline['clf'].predict_proba(X_tr)[:, 1][0]
    es_fraude = proba >= threshold

    # Llamamos a nuestra función de arriba pasándole el df original
    razones_fraude, razones_legitima = explain(pipeline, explainer, df)

    return {
        'probabilidad_fraude': round(float(proba), 4),
        'probabilidad_legitima': round(float(1 - proba), 4),
        'es_fraude': bool(es_fraude),
        'nivel_riesgo': 'ALTO' if proba >= 0.7 else 'MEDIO' if proba >= threshold else 'BAJO',
        'threshold': threshold,
        'razones_fraude': razones_fraude,
        'razones_legitima': razones_legitima,
    }
