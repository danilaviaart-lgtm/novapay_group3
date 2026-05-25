# 1. Usamos una imagen base de Python ligera (versión slim)
FROM python:3.11-slim

# 2. Evitamos que Python genere archivos .pyc y permitimos que los logs salgan directo a la consola
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Establecemos el directorio donde vivirá nuestra app dentro del contenedor
WORKDIR /src/api

# 4. Instalamos dependencias del sistema si fueran necesarias (ej. para bases de datos)
# Si no usas bases de datos complejas, puedes omitir esta línea de RUN
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

# 5. Copiamos el archivo de requerimientos primero
# Esto es un truco: Docker solo reinstalará las librerías si este archivo cambia
COPY requirements.txt .

# 6. Instalamos las librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copiamos todo el contenido de tu carpeta actual al contenedor
COPY . .

# 8. Exponemos el puerto en el que correrá FastAPI (por defecto 80 o 8000)
EXPOSE 8000

# 9. Comando para arrancar la aplicación con Uvicorn
# "app.main:app" asume que tienes un archivo main.py dentro de una carpeta llamada app/
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]