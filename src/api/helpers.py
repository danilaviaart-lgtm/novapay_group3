import numpy as np
# FUNCIÓN LIMPIADO NUMPY PARA POSTGRESQL
def preparar_para_postgres(datos: dict) -> dict:
    datos_limpios = {}
    for clave, valor in datos.items():
        if isinstance(valor, (np.floating, float)):
            datos_limpios[clave] = float(valor)
        elif isinstance(valor, (np.integer, int)):
            datos_limpios[clave] = int(valor)
        elif isinstance(valor, np.ndarray):
            datos_limpios[clave] = valor.tolist()
        else:
            datos_limpios[clave] = valor
    return datos_limpios