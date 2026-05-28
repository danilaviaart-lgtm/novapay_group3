"""
REENTRENAMIENTO DEL MODELO DE FRAUDE

Contexto:
- El modelo v1 está en producción.
- Los analistas están revisando transacciones con probabilidad entre ~0.30 y 0.50.
- De esa revisión salen dos archivos normalmente pequeños pero de muy alta calidad:
    - fraudes_confirmados.csv   (156 filas)
    - legitimas_confirmadas.csv (199 filas)
- Estos datos son "correcciones humanas" en los casos más difíciles del modelo.

Problema principal:
- Solo tenemos ~355 filas nuevas frente a 100.000 originales.
- No podemos tratar estos datos como "más datos normales".
- Si los mezclamos mal, podemos romper lo que ya funciona bien.

Estrategia que usamos aquí (simple pero correcta):

1. Damos a los datos de analistas un peso moderado (8x).
   - Suficiente para que el modelo "escuche" las correcciones.
   - No tan alto como para que 355 filas dominen a 100k.

2. Reutilizamos todo lo que ya teníamos en producción:
   - Listas de países y categorías de alto riesgo (del modelo v1)
   - Hiperparámetros del XGBoost anterior (estabilidad)
   - La misma función feature_engineering
   - La misma estructura del pipeline

3. Evaluación honesta (lo más importante):
   - Evaluamos el modelo viejo y el nuevo en DOS sitios distintos:
     a) Un conjunto de test limpio sacado de los datos originales (performance general).
     b) Los propios datos de los analistas (¿mejoramos en los casos difíciles que están revisando?).
   - Usamos las métricas que importan al negocio:
     - Recall a threshold 0.35 (prioridad máxima recall)
     - PR-AUC
     - Coste de negocio (150€ por fraude perdido, 25€ por falsa alarma)

4. Decisión conservadora:
   - Solo recomendamos desplegar si el nuevo modelo es claramente mejor
     en las métricas que le importan al negocio.
   - Nunca sobreescribimos el modelo v1. Siempre generamos v2 + metadata.

Este script está pensado para que lo entiendas fácilmente.
Cada sección grande tiene comentarios explicando el "por qué".
"""

import warnings
warnings.filterwarnings('ignore')

import os
import json
from datetime import datetime
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder, FunctionTransformer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    classification_report, average_precision_score, roc_auc_score,
    precision_score, recall_score, f1_score
)
from xgboost import XGBClassifier
import joblib

from utils.utils import feature_engineering


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN (ajusta aquí si hace falta)
# ═══════════════════════════════════════════════════════════════════════════════

RANDOM_STATE = 42

# Peso que le damos a cada fila confirmada por analista.
# 8.0 significa "esta fila vale como si tuviéramos 8 copias de ella".
# Es un valor moderado y razonable cuando los datos nuevos son pocos pero muy buenos.
PESO_ANALISTAS = 8.0

# Umbral de decisión que usa el negocio para operar (prioridad = máximo recall)
THRESHOLD_OPERACION = 0.35

# Costes de negocio (los mismos que definimos en el notebook)
COSTE_FRAUDE_PERDIDO = 150   # € por fraude que se escapa
COSTE_FALSA_ALARMA   = 25    # € por cliente legítimo bloqueado

# Archivos
RUTA_MODELO_V1      = 'models/modelo_fraude_v1.pkl'
RUTA_MODELO_V2      = 'models/modelo_fraude_v2.pkl'
RUTA_METADATA_V2    = 'models/modelo_fraude_v2_metadata.json'

# Columnas
TARGET = 'es_fraude'


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("REENTRENAMIENTO DEL MODELO DE FRAUDE")
print("=" * 70)
print()

print("Cargando datos...")
df_original  = pd.read_csv('data/raw/novapay_transacciones.csv')
df_fraudes   = pd.read_csv('data/raw/fraudes_confirmados.csv')
df_legitimas = pd.read_csv('data/raw/legitimas_confirmadas.csv')

print(f"  Original (sintético grande) : {len(df_original):>6,} filas | fraude: {df_original['es_fraude'].mean()*100:.2f}%")
print(f"  Fraudes confirmados por humanos : {len(df_fraudes):>4,} filas")
print(f"  Legítimas confirmadas por humanos : {len(df_legitimas):>4,} filas")
print()

# Aseguramos que los nuevos datos tengan la columna es_fraude bien puesta
df_fraudes   = df_fraudes.copy()
df_legitimas = df_legitimas.copy()
df_fraudes['es_fraude']   = 1
df_legitimas['es_fraude'] = 0


# ═══════════════════════════════════════════════════════════════════════════════
# 2. COMBINAR DATOS + MARCAR ORIGEN (para poder dar pesos diferentes)
# ═══════════════════════════════════════════════════════════════════════════════

# Marcamos el origen de cada fila
df_original['source']  = 'original'
df_fraudes['source']   = 'analyst'
df_legitimas['source'] = 'analyst'

# Unimos todo. Los datos de analistas van primero para que, si hay duplicados,
# se queden los de analistas (son más confiables).
df_all = pd.concat([df_fraudes, df_legitimas, df_original], ignore_index=True)

# Eliminamos duplicados por id_transaccion (si una transacción fue revisada por humanos, nos quedamos con esa versión)
filas_antes = len(df_all)
df_all = df_all.drop_duplicates(subset='id_transaccion', keep='first').reset_index(drop=True)
filas_despues = len(df_all)

print(f"Después de unir y quitar duplicados: {filas_despues:,} filas")
print(f"  - De datos originales : {(df_all.source == 'original').sum():,}")
print(f"  - Confirmadas por humanos : {(df_all.source == 'analyst').sum():,}")
print()

# Creamos la columna de pesos
# - Filas normales (original) → peso 1.0
# - Filas de analistas → peso PESO_ANALISTAS
df_all['sample_weight'] = np.where(df_all['source'] == 'analyst', PESO_ANALISTAS, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CREAR CONJUNTOS DE EVALUACIÓN HONESTOS
# ═══════════════════════════════════════════════════════════════════════════════
"""
Esta es la parte más importante y donde más se equivoca la gente.

NO podemos hacer un split aleatorio normal sobre todos los datos juntos.
Si lo hacemos, el test contendrá datos de analistas y la comparación no será justa.

Estrategia que usamos (simple pero correcta):

- Conjunto A (Test Original): Una porción de los datos originales que NO usamos para entrenar.
  Sirve para medir si el modelo sigue funcionando bien en el mundo "normal".

- Conjunto B (Test Analistas): Todos los datos que confirmaron los humanos.
  Sirve para medir si mejoramos precisamente en los casos difíciles que los analistas están revisando ahora.

Evaluamos el modelo viejo y el nuevo en AMBOS conjuntos.
"""

print("Preparando conjuntos de evaluación...")

# Separamos los datos originales de los de analistas
df_orig_only = df_all[df_all['source'] == 'original'].copy()
df_analyst   = df_all[df_all['source'] == 'analyst'].copy()

# Del original, separamos un 15% como test limpio (nunca lo veremos en entrenamiento).
# Usamos una forma más robusta: añadimos una columna temporal para marcar el split.
df_orig_only['_is_test'] = False
_, test_idx = train_test_split(
    df_orig_only.index,
    test_size=0.15,
    stratify=df_orig_only[TARGET],
    random_state=RANDOM_STATE
)
df_orig_only.loc[test_idx, '_is_test'] = True

df_test_orig = df_orig_only[df_orig_only['_is_test']].copy()
df_train_orig = df_orig_only[~df_orig_only['_is_test']].copy()

# Limpiamos la columna temporal
for d in [df_train_orig, df_test_orig, df_orig_only]:
    d.drop(columns='_is_test', inplace=True, errors='ignore')

# Pool de entrenamiento = originales de train + TODOS los datos de analistas
df_train_pool = pd.concat([df_train_orig, df_analyst], ignore_index=True)

print(f"  Train pool     : {len(df_train_pool):,} filas (originales + analistas con peso)")
print(f"  Test Original  : {len(df_test_orig):,} filas (solo datos originales, limpio)")
print(f"  Test Analistas : {len(df_analyst):,} filas (los casos que revisaron los humanos)")
print()


# ═══════════════════════════════════════════════════════════════════════════════
# 4. CARGAR MODELO V1 Y REUTILIZAR SU CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════════
"""
Muy importante para no romper nada:

- Reutilizamos las listas de "alto riesgo" que ya tenía el modelo en producción.
- Reutilizamos los hiperparámetros que ya estaban tuneados.
- Solo cambiamos los datos y los pesos.

Esto hace que el reentrenamiento sea estable y rápido.
"""

print("Cargando modelo v1 para reutilizar su configuración...")
model_v1 = joblib.load(RUTA_MODELO_V1)

# Listas de alto riesgo (las que ya estaban en producción)
fe_kw = model_v1.named_steps['fe'].kw_args
paises_alto_riesgo     = fe_kw['paises_alto_riesgo']
categorias_alto_riesgo = fe_kw['categorias_alto_riesgo']

print(f"  Países alto riesgo    : {paises_alto_riesgo}")
print(f"  Categorías alto riesgo: {categorias_alto_riesgo}")

# Hiperparámetros del XGBoost anterior (para mantener estabilidad)
params_v1 = model_v1.named_steps['clf'].get_params()
hyperparams_a_reutilizar = [
    'n_estimators', 'max_depth', 'learning_rate', 'subsample',
    'colsample_bytree', 'min_child_weight', 'gamma', 'reg_lambda'
]
xgb_params = {k: params_v1[k] for k in hyperparams_a_reutilizar}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. PREPARAR DATOS DE ENTRENAMIENTO + PESOS
# ═══════════════════════════════════════════════════════════════════════════════

# Quitamos columnas que no son features
cols_a_quitar = ['id_transaccion', 'id_usuario', 'source', 'sample_weight']

X_train = df_train_pool.drop(columns=[TARGET] + cols_a_quitar, errors='ignore')
y_train = df_train_pool[TARGET]
w_train = df_train_pool['sample_weight'].values

# También preparamos los dos test sets limpios
X_test_orig = df_test_orig.drop(columns=[TARGET] + cols_a_quitar, errors='ignore')
y_test_orig = df_test_orig[TARGET]

X_test_analyst = df_analyst.drop(columns=[TARGET] + cols_a_quitar, errors='ignore')
y_test_analyst = df_analyst[TARGET]

print(f"\nDatos de entrenamiento listos:")
print(f"  Filas train : {len(X_train):,}")
print(f"  Peso total  : {w_train.sum():,.0f} (efecto de los pesos de analistas)")
print()


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CALCULAR scale_pos_weight PONDERADO
# ═══════════════════════════════════════════════════════════════════════════════
"""
Como ahora tenemos pesos en las filas, el scale_pos_weight también debe calcularse
teniendo en cuenta esos pesos (no solo contando filas).
"""

neg_w = w_train[y_train == 0].sum()
pos_w = w_train[y_train == 1].sum()
scale_pos_weight = neg_w / pos_w

print(f"scale_pos_weight ponderado = {scale_pos_weight:.2f}")
print()

xgb_params.update({
    'scale_pos_weight': scale_pos_weight,
    'random_state'    : RANDOM_STATE,
    'eval_metric'     : 'aucpr',
    'n_jobs'          : -1,
})


# ═══════════════════════════════════════════════════════════════════════════════
# 7. CONSTRUIR PIPELINE (IDÉNTICO AL DE PRODUCCIÓN)
# ═══════════════════════════════════════════════════════════════════════════════

num_cols = ['hora', 'dias_antiguedad_cuenta', 'importe']
cat_cols = ['pais_emision', 'pais_pago', 'categoria', 'tipo_tarjeta', 'tipo_dispositivo']

preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), num_cols),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cat_cols)
    ],
    remainder='passthrough'
)

pipeline_new = Pipeline(steps=[
    ('fe', FunctionTransformer(
        feature_engineering,
        validate=False,
        kw_args={
            'paises_alto_riesgo': paises_alto_riesgo,
            'categorias_alto_riesgo': categorias_alto_riesgo,
        },
    )),
    ('preprocessor', preprocessor),
    ('clf', XGBClassifier(**xgb_params)),
])


# ═══════════════════════════════════════════════════════════════════════════════
# 8. ENTRENAR EL NUEVO MODELO
# ═══════════════════════════════════════════════════════════════════════════════

print("Entrenando nuevo modelo (con pesos)...")
pipeline_new.fit(X_train, y_train, clf__sample_weight=w_train)
print("Entrenamiento terminado.\n")


# ═══════════════════════════════════════════════════════════════════════════════
# 9. EVALUACIÓN COMPLETA (MODELO VIEJO vs NUEVO)
# ═══════════════════════════════════════════════════════════════════════════════
"""
Aquí está el corazón de la decisión.

Evaluamos los dos modelos en los dos conjuntos de test.
"""

def evaluar_modelo(modelo, X, y, nombre_conjunto):
    """Devuelve métricas importantes para el negocio.
    
    IMPORTANTE: Convertimos todo a tipos nativos de Python (int, float)
    para que se puedan guardar sin problemas en JSON después.
    """
    proba = modelo.predict_proba(X)[:, 1]
    pred  = (proba >= THRESHOLD_OPERACION).astype(int)

    pr_auc   = float(average_precision_score(y, proba))
    rec      = float(recall_score(y, pred))
    prec     = float(precision_score(y, pred))
    f1       = float(f1_score(y, pred))

    # Coste de negocio (usamos int() para que sea serializable en JSON)
    fn = int(((y == 1) & (pred == 0)).sum())
    fp = int(((y == 0) & (pred == 1)).sum())
    coste = int(fn * COSTE_FRAUDE_PERDIDO + fp * COSTE_FALSA_ALARMA)

    return {
        'PR-AUC': pr_auc,
        f'Recall@{THRESHOLD_OPERACION}': rec,
        'Precision': prec,
        'F1': f1,
        'Coste negocio': coste,
        'n_fraudes': int(y.sum()),
        'n_fraudes_perdidos': fn,
        'n_falsas_alarmas': fp
    }

print("=" * 70)
print("EVALUACIÓN COMPARATIVA")
print("=" * 70)

# Usamos el modelo_v1 que ya cargamos antes (evitamos recargar y posibles problemas de versión)
print("\nTEST ORIGINAL (datos que el modelo debería conocer bien)")
metrics_v1_orig = evaluar_modelo(model_v1, X_test_orig, y_test_orig, "Test Original")
metrics_v2_orig = evaluar_modelo(pipeline_new, X_test_orig, y_test_orig, "Test Original")

print("\nTEST ANALISTAS (los casos difíciles que están revisando)")
metrics_v1_analyst = evaluar_modelo(model_v1, X_test_analyst, y_test_analyst, "Test Analistas")
metrics_v2_analyst = evaluar_modelo(pipeline_new, X_test_analyst, y_test_analyst, "Test Analistas")


# ═══════════════════════════════════════════════════════════════════════════════
# 10. MOSTRAR COMPARACIÓN CLARA
# ═══════════════════════════════════════════════════════════════════════════════

def imprimir_tabla(titulo, m1, m2):
    print(f"\n{titulo}")
    print("-" * 65)
    print(f"{'Métrica':<25} {'Modelo v1':>12} {'Modelo v2':>12} {'Diferencia':>12}")
    print("-" * 65)
    for k in m1.keys():
        if k in ['n_fraudes', 'n_fraudes_perdidos', 'n_falsas_alarmas']:
            continue
        v1, v2 = m1[k], m2[k]
        diff = v2 - v1
        if isinstance(v1, float):
            print(f"{k:<25} {v1:>12.4f} {v2:>12.4f} {diff:>+12.4f}")
        else:
            print(f"{k:<25} {v1:>12,} {v2:>12,} {diff:>+12,}")
    print("-" * 65)

imprimir_tabla("TEST ORIGINAL (performance general)", metrics_v1_orig, metrics_v2_orig)
imprimir_tabla("TEST ANALISTAS (casos difíciles)",      metrics_v1_analyst, metrics_v2_analyst)


# ═══════════════════════════════════════════════════════════════════════════════
# 11. DECISIÓN DE DESPLIEGUE (lógica conservadora)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("DECISIÓN DE DESPLIEGUE")
print("=" * 70)

# Criterios simples y claros (puedes ajustarlos)
mejora_recall_orig   = metrics_v2_orig[f'Recall@{THRESHOLD_OPERACION}'] - metrics_v1_orig[f'Recall@{THRESHOLD_OPERACION}']
mejora_coste_orig    = metrics_v1_orig['Coste negocio'] - metrics_v2_orig['Coste negocio']   # positivo = mejor
mejora_recall_analyst = metrics_v2_analyst[f'Recall@{THRESHOLD_OPERACION}'] - metrics_v1_analyst[f'Recall@{THRESHOLD_OPERACION}']

print(f"\nDeltas importantes:")
print(f"  Recall en Test Original   : {mejora_recall_orig:+.4f}")
print(f"  Coste negocio (Test Orig) : {mejora_coste_orig:+.0f} € (positivo = ahorramos)")
print(f"  Recall en datos Analistas : {mejora_recall_analyst:+.4f}")

# Reglas de decisión (conservadoras)
recomendar_despliegue = False
razones = []

if mejora_recall_orig >= 0.01 and mejora_coste_orig > 200:
    recomendar_despliegue = True
    razones.append("Mejora clara de recall y reducción de coste en datos normales")

if mejora_recall_analyst >= 0.03:
    recomendar_despliegue = True
    razones.append("Mejora significativa en los casos difíciles que revisan los analistas")

if recomendar_despliegue:
    print("\n RECOMENDACIÓN: DESPLEGAR MODELO v2")
    for r in razones:
        print(f"   - {r}")
else:
    print("\n RECOMENDACIÓN: MANTENER MODELO v1 por ahora")
    print("   El nuevo modelo no muestra una mejora suficientemente clara")
    print("   en las métricas que importan al negocio.")

print()


# ═══════════════════════════════════════════════════════════════════════════════
# 12. GUARDAR MODELO v2 (ESTRUCTURA EXACTA COMO EL NOTEBOOK)
# ═══════════════════════════════════════════════════════════════════════════════
"""
¡CRÍTICO PARA PRODUCCIÓN!

El modelo que se guarda aquí DEBE tener exactamente la misma estructura
que el que exporta el notebook 02_modelo_sin_smote.ipynb:

Pipeline con 3 pasos en este orden:
  - 'fe'            → FunctionTransformer (feature_engineering)
  - 'preprocessor'  → ColumnTransformer (StandardScaler + OneHotEncoder)
  - 'clf'           → XGBClassifier

NADA MÁS. No le añadas atributos extra, no uses ImbPipeline, no guardes
nada dentro del pickle.

Los metadatos (versiones, deltas, umbrales, etc.) van SOLO en el JSON.
"""

os.makedirs('models', exist_ok=True)

# Reconstruimos el pipeline de forma explícita (igual que hace el notebook)
export_pipeline = Pipeline([
    ('fe',           pipeline_new.named_steps['fe']),
    ('preprocessor', pipeline_new.named_steps['preprocessor']),
    ('clf',          pipeline_new.named_steps['clf']),
])

joblib.dump(export_pipeline, RUTA_MODELO_V2)
print(f"Modelo v2 guardado en: {RUTA_MODELO_V2}")
print("Estructura: ['fe', 'preprocessor', 'clf']  (idéntica al notebook)")

# Verificación rápida de estructura (para que no se rompa en producción)
steps = list(export_pipeline.named_steps.keys())
if steps != ['fe', 'preprocessor', 'clf']:
    print(f"ALERTA: la estructura del modelo es {steps} en vez de ['fe', 'preprocessor', 'clf']")
else:
    print("Verificación de estructura: OK")

# Guardamos metadata completa para auditoría
# Convertimos todo explícitamente a tipos nativos de Python para evitar
# errores de "int64 is not JSON serializable"
metadata = {
    "model_version": "v2",
    "fecha_entrenamiento": datetime.now().isoformat(),
    "datos_usados": {
        "originales": int(len(df_orig_only)),
        "analistas_fraudes": int(len(df_fraudes)),
        "analistas_legitimas": int(len(df_legitimas)),
        "peso_analistas": float(PESO_ANALISTAS),
    },
    "threshold_operacion": float(THRESHOLD_OPERACION),
    "coste_negocio": {
        "fraude_perdido": int(COSTE_FRAUDE_PERDIDO),
        "falsa_alarma": int(COSTE_FALSA_ALARMA),
    },
    "metricas": {
        "test_original": {
            "v1": metrics_v1_orig,
            "v2": metrics_v2_orig,
        },
        "test_analistas": {
            "v1": metrics_v1_analyst,
            "v2": metrics_v2_analyst,
        }
    },
    "deltas": {
        "recall_test_original": float(mejora_recall_orig),
        "coste_ahorrado_test_original": float(mejora_coste_orig),
        "recall_test_analistas": float(mejora_recall_analyst),
    },
    "recomendacion_despliegue": bool(recomendar_despliegue),
    "razones": razones,
}

with open(RUTA_METADATA_V2, 'w', encoding='utf-8') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"Metadata guardada en   : {RUTA_METADATA_V2}")
print()
print("Script terminado correctamente.")