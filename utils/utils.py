import pandas as pd


def feature_engineering(df_in, paises_alto_riesgo=None, categorias_alto_riesgo=None):
    if not isinstance(df_in, pd.DataFrame):
        raise TypeError(
            f"feature_engineering espera pd.DataFrame, recibió {type(df_in).__name__}"
        )

    df = df_in.copy()

    # Idempotencia: si el FE ya fue aplicado, devolver tal cual
    if {'dia_semana', 'pais_alto_riesgo'}.issubset(df.columns):
        return df

    required = {
        'fecha', 'pais_pago', 'pais_emision', 'hora',
        'categoria', 'es_online', 'paso_3d_secure',
    }
    faltantes = required - set(df.columns)
    if faltantes:
        raise KeyError(
            f"feature_engineering: columnas faltantes {sorted(faltantes)}"
        )

    paises_alto_riesgo = tuple(paises_alto_riesgo) if paises_alto_riesgo else ()
    categorias_alto_riesgo = tuple(categorias_alto_riesgo) if categorias_alto_riesgo else ()

    # Fecha
    df['fecha'] = pd.to_datetime(df['fecha'])
    df['dia_semana'] = df['fecha'].dt.dayofweek
    df['es_fin_de_semana'] = (df['dia_semana'] >= 5).astype(int)
    df['mes'] = df['fecha'].dt.month
    df = df.drop(columns=['fecha'])

    # País — listas derivadas en el notebook desde y_train (no hardcoded)
    df['pais_alto_riesgo'] = df['pais_pago'].isin(paises_alto_riesgo).astype(int)
    df['pais_distinto'] = (df['pais_emision'] != df['pais_pago']).astype(int)

    # Hora
    df['hora_madrugada'] = df['hora'].between(0, 5).astype(int)

    # Categoría
    df['categoria_alto_riesgo'] = df['categoria'].isin(categorias_alto_riesgo).astype(int)

    # Combinaciones
    df['online_sin_3ds'] = ((df['es_online'] == 1) & (df['paso_3d_secure'] == 0)).astype(int)

    return df
