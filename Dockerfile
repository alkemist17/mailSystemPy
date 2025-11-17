# Dockerfile para la aplicación MailSystem API
# Dockerfile define cómo construir una imagen Docker para la aplicación

# Usar imagen base de Python 3.11 (slim para reducir tamaño)
FROM python:3.11-slim

# Establecer directorio de trabajo dentro del contenedor
# Todos los comandos siguientes se ejecutarán en este directorio
WORKDIR /app

# Instalar dependencias del sistema si son necesarias
# (por ahora no necesitamos ninguna, pero dejamos el espacio por si acaso)
# RUN apt-get update && apt-get install -y <paquete> && rm -rf /var/lib/apt/lists/*

# Copiar el archivo de dependencias
# Esto se hace antes de copiar el código para aprovechar la caché de Docker
# Si solo cambia el código pero no las dependencias, Docker reutilizará la capa
COPY requirements.txt .

# Instalar dependencias de Python
# --no-cache-dir reduce el tamaño de la imagen
# --upgrade asegura que se instalen las versiones más recientes
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copiar el código de la aplicación
COPY main.py .

# Exponer el puerto 8000 (puerto por defecto de FastAPI/uvicorn)
EXPOSE 8000

# Variable de entorno para Python
# PYTHONUNBUFFERED=1 asegura que los logs de Python se muestren inmediatamente
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar la aplicación
# uvicorn es el servidor ASGI que ejecuta FastAPI
# --host 0.0.0.0 permite acceso desde fuera del contenedor
# --port 8000 especifica el puerto
# main:app se refiere al objeto 'app' en el archivo 'main.py'
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

