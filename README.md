# MailSystem API

API REST para envío de correos electrónicos construida con FastAPI. Esta aplicación permite enviar correos electrónicos con asunto, cuerpo, múltiples destinatarios y archivos adjuntos mediante SMTP.

## 📋 Características

- ✅ Envío de correos electrónicos mediante SMTP
- ✅ Soporte para múltiples destinatarios
- ✅ Soporte para archivos adjuntos (codificados en base64)
- ✅ Soporte para cuerpo HTML o texto plano
- ✅ Validación automática de datos de entrada
- ✅ **Autenticación por API Key**
- ✅ **Restricción por IP (whitelist)**
- ✅ Documentación interactiva con Swagger UI
- ✅ Contenedorizado con Docker
- ✅ Configuración mediante variables de entorno
- ✅ Código completamente documentado para aprendizaje

## 🚀 Inicio Rápido

### Prerrequisitos

- Docker y Docker Compose instalados
- Una cuenta de correo con acceso SMTP configurado

### Instalación y Ejecución

1. **Clonar o descargar el proyecto**

2. **Configurar variables de entorno**

   Copia el archivo de ejemplo y completa con tus credenciales:
   ```bash
   cp .env.example .env
   ```

   Edita el archivo `.env` con tus datos SMTP y seguridad:
   ```env
   # Configuración SMTP
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=tu_email@gmail.com
   SMTP_PASSWORD=tu_contraseña
   SMTP_FROM_EMAIL=tu_email@gmail.com
   SMTP_USE_TLS=true
   
   # Configuración de Seguridad
   API_KEY=tu_api_key_secreta_aqui
   ALLOWED_IPS=127.0.0.1,192.168.1.100
   ```

   **Nota para Gmail**: Necesitas usar una "Contraseña de aplicación" en lugar de tu contraseña normal. Puedes generarla en: https://myaccount.google.com/apppasswords
   
   **Generar API Key segura**: Puedes generar una API Key segura con:
   ```bash
   openssl rand -hex 32
   ```

3. **Construir y ejecutar con Docker Compose**

   ```bash
   docker-compose up --build
   ```

   La API estará disponible en: `http://localhost:8000`

4. **Acceder a la documentación interactiva**

   - Swagger UI: http://localhost:8008/docs (solo accesible desde IPs autorizadas)
   - ReDoc: http://localhost:8008/redoc (solo accesible desde IPs autorizadas)
   
   **Nota**: La documentación está protegida y solo es accesible desde las IPs configuradas en `ALLOWED_IPS`.

## 📚 Documentación de la API

### Endpoints Disponibles

#### `GET /`
Endpoint raíz que devuelve información básica de la API.

**Respuesta:**
```json
{
  "message": "Bienvenido a MailSystem API",
  "version": "1.0.0",
  "docs": "/docs",
  "description": "API para envío de correos electrónicos"
}
```

#### `GET /health`
Verifica el estado de la API y la configuración SMTP.

**Respuesta:**
```json
{
  "status": "healthy",
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "smtp_from_email": "tu_email@gmail.com",
  "smtp_configured": true
}
```

#### `POST /send-email`
Envía un correo electrónico.

**⚠️ Requiere autenticación**: Este endpoint requiere:
- Header `X-API-Key` con tu API Key
- Tu IP debe estar en la lista de IPs permitidas (`ALLOWED_IPS`)

**Headers requeridos:**
```
X-API-Key: tu_api_key_secreta_aqui
```

**Cuerpo de la solicitud:**
```json
{
  "subject": "Asunto del correo",
  "body": "Cuerpo del correo (puede ser HTML)",
  "recipients": ["destinatario1@example.com", "destinatario2@example.com"],
  "is_html": false,
  "attachments": [
    {
      "filename": "documento.pdf",
      "content": "base64_encoded_content_here",
      "content_type": "application/pdf"
    }
  ]
}
```

**Parámetros:**
- `subject` (string, requerido): Asunto del correo (1-500 caracteres)
- `body` (string, requerido): Cuerpo del correo
- `recipients` (array, requerido): Lista de direcciones de correo destinatarias
- `is_html` (boolean, opcional): Si es `true`, el cuerpo se trata como HTML (por defecto: `false`)
- `attachments` (array, opcional): Lista de archivos adjuntos
  - `filename` (string): Nombre del archivo
  - `content` (string): Contenido del archivo codificado en base64
  - `content_type` (string, opcional): Tipo MIME del archivo

**Respuesta exitosa:**
```json
{
  "success": true,
  "message": "Correo enviado exitosamente a 2 destinatario(s)",
  "timestamp": "2024-01-15T10:30:00.123456",
  "recipients": ["destinatario1@example.com", "destinatario2@example.com"]
}
```

## 💡 Ejemplos de Uso

### Ejemplo 1: Enviar correo simple (texto plano)

```bash
curl -X POST "http://localhost:8000/send-email" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu_api_key_secreta_aqui" \
  -d '{
    "subject": "Prueba de correo",
    "body": "Este es un correo de prueba",
    "recipients": ["destinatario@example.com"]
  }'
```

### Ejemplo 2: Enviar correo con HTML

```bash
curl -X POST "http://localhost:8000/send-email" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu_api_key_secreta_aqui" \
  -d '{
    "subject": "Correo HTML",
    "body": "<h1>Hola</h1><p>Este es un correo con <b>HTML</b></p>",
    "recipients": ["destinatario@example.com"],
    "is_html": true
  }'
```

### Ejemplo 3: Enviar correo con adjunto

Primero, codifica el archivo en base64:
```bash
# En Linux/Mac
base64 -i archivo.pdf > archivo_base64.txt

# En Windows (PowerShell)
[Convert]::ToBase64String([IO.File]::ReadAllBytes("archivo.pdf")) | Out-File -Encoding ASCII archivo_base64.txt
```

Luego envía el correo:
```bash
curl -X POST "http://localhost:8000/send-email" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: tu_api_key_secreta_aqui" \
  -d '{
    "subject": "Correo con adjunto",
    "body": "Por favor encuentra adjunto el documento",
    "recipients": ["destinatario@example.com"],
    "attachments": [
      {
        "filename": "documento.pdf",
        "content": "CONTENIDO_BASE64_AQUI",
        "content_type": "application/pdf"
      }
    ]
  }'
```

### Ejemplo con Python

```python
import requests
import base64

# Leer y codificar archivo
with open("documento.pdf", "rb") as f:
    file_content = base64.b64encode(f.read()).decode('utf-8')

# Enviar correo
response = requests.post(
    "http://localhost:8000/send-email",
    headers={
        "X-API-Key": "tu_api_key_secreta_aqui"
    },
    json={
        "subject": "Correo con adjunto",
        "body": "Por favor encuentra adjunto el documento",
        "recipients": ["destinatario@example.com"],
        "attachments": [
            {
                "filename": "documento.pdf",
                "content": file_content,
                "content_type": "application/pdf"
            }
        ]
    }
)

print(response.json())
```

### Ejemplo con JavaScript/Node.js

```javascript
const axios = require('axios');
const fs = require('fs');

// Leer y codificar archivo
const fileContent = fs.readFileSync('documento.pdf');
const base64Content = fileContent.toString('base64');

// Enviar correo
axios.post('http://localhost:8000/send-email', {
  subject: 'Correo con adjunto',
  body: 'Por favor encuentra adjunto el documento',
  recipients: ['destinatario@example.com'],
  attachments: [
    {
      filename: 'documento.pdf',
      content: base64Content,
      content_type: 'application/pdf'
    }
  ]
}, {
  headers: {
    'X-API-Key': 'tu_api_key_secreta_aqui'
  }
})
.then(response => console.log(response.data))
.catch(error => console.error(error));
```

## 📧 Script de Línea de Comandos

Para facilitar el envío de correos desde la terminal, se incluye un script bash (`envio_correo.sh`) que permite enviar correos de forma rápida y sencilla.

### Uso del Script

```bash
# Correo simple
./envio_correo.sh -m destinatario@email.com -s "Asunto" -b "Cuerpo del correo"

# Correo con adjunto
./envio_correo.sh -m destinatario@email.com -s "Asunto" -b "Cuerpo" -a archivo.xls

# Correo con HTML
./envio_correo.sh -m destinatario@email.com -s "Asunto" -b "<h1>HTML</h1>" --html

# Múltiples destinatarios
./envio_correo.sh -m email1@test.com,email2@test.com -s "Asunto" -b "Cuerpo"
```

### Parámetros del Script

- `-m, --mail`: Destinatario(s) - puede ser uno o varios separados por comas (requerido)
- `-s, --subject`: Asunto del correo (requerido)
- `-b, --body`: Cuerpo del correo (requerido)
- `-a, --attach`: Archivo adjunto (opcional)
- `-h, --html`: Si se especifica, el cuerpo se trata como HTML (opcional)
- `-u, --url`: URL de la API (opcional, por defecto: http://localhost:8008)
- `--help`: Muestra la ayuda

### Configuración del Script

El script lee automáticamente la `API_KEY` y `API_URL` desde el archivo `.env` si está disponible. Si no, puedes configurarla directamente en el script editando la variable `API_KEY` al inicio del archivo.

**Ejemplo de uso:**
```bash
# Dar permisos de ejecución (solo la primera vez)
chmod +x envio_correo.sh

# Enviar correo
./envio_correo.sh -m alkemist17@gmail.com -s "asunto prueba" -b "Cuerpo del Correo" -a archivo.xls
```

## 🐳 Docker

### Comandos útiles

```bash
# Construir y ejecutar
docker-compose up --build

# Ejecutar en segundo plano
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener
docker-compose down

# Reconstruir sin caché
docker-compose build --no-cache
```

## 📖 Conceptos de FastAPI Aprendidos

### 1. **FastAPI Framework**
FastAPI es un framework web moderno y rápido para construir APIs con Python basado en estándares web como OpenAPI y JSON Schema.

### 2. **Pydantic Models**
Pydantic se usa para validación de datos. Los modelos definen la estructura de los datos de entrada y salida, y FastAPI valida automáticamente.

### 3. **Type Hints**
Python usa type hints para especificar tipos de datos. FastAPI los usa para validación automática y generación de documentación.

### 4. **Dependency Injection**
FastAPI tiene un sistema de inyección de dependencias que permite reutilizar código y facilitar testing.

### 5. **Async/Await**
FastAPI soporta programación asíncrona, permitiendo manejar múltiples solicitudes de forma eficiente.

### 6. **OpenAPI/Swagger**
FastAPI genera automáticamente documentación interactiva siguiendo el estándar OpenAPI.

### 7. **Status Codes**
FastAPI permite especificar códigos de estado HTTP apropiados para cada respuesta.

### 8. **Request/Response Models**
Los modelos Pydantic definen tanto la estructura de entrada (request) como de salida (response).

## 🔧 Configuración SMTP para Proveedores Comunes

### Gmail
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
```
**Importante**: Usa una "Contraseña de aplicación" en lugar de tu contraseña normal.

### Outlook/Hotmail
```env
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Yahoo
```env
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

### Servidor Personalizado
```env
SMTP_SERVER=smtp.tudominio.com
SMTP_PORT=587
SMTP_USE_TLS=true
```

## 🛠️ Desarrollo Local (sin Docker)

Si prefieres ejecutar sin Docker:

1. **Crear entorno virtual**
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

4. **Ejecutar la aplicación**
   ```bash
   python main.py
   # O con uvicorn directamente:
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## 📝 Estructura del Proyecto

```
MailSystem/
├── main.py              # Aplicación FastAPI principal
├── requirements.txt     # Dependencias de Python
├── Dockerfile          # Configuración de Docker
├── docker-compose.yml  # Orquestación de servicios
├── envio_correo.sh     # Script bash para envío desde línea de comandos
├── example_usage.py    # Ejemplos de uso en Python
├── .env.example        # Ejemplo de variables de entorno
├── .env                # Variables de entorno (no se sube a git)
├── .gitignore          # Archivos ignorados por git
└── README.md           # Este archivo
```

## 🔒 Seguridad

### Autenticación y Autorización

La API implementa dos capas de seguridad:

1. **Autenticación por API Key**: Todos los endpoints protegidos requieren una API Key válida en el header `X-API-Key`
2. **Restricción por IP (Whitelist)**: Solo las IPs configuradas en `ALLOWED_IPS` pueden acceder a los endpoints protegidos

### Configuración de Seguridad

#### 1. Generar una API Key segura

```bash
# Generar una API Key aleatoria de 64 caracteres
openssl rand -hex 32

# O usar Python
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 2. Configurar IPs permitidas

En el archivo `.env`, configura las IPs desde las que quieres acceder:

```env
# IPs individuales separadas por comas
ALLOWED_IPS=127.0.0.1,192.168.1.100,203.0.113.45

# También puedes usar rangos CIDR
ALLOWED_IPS=127.0.0.1,192.168.1.0/24,10.0.0.0/8
```

**Ejemplos:**
- **Servidor local**: `127.0.0.1`
- **Servidor remoto con IP fija**: `203.0.113.45`
- **Red local completa**: `192.168.1.0/24` (permite todas las IPs de 192.168.1.1 a 192.168.1.254)
- **Múltiples IPs**: `127.0.0.1,203.0.113.45,192.168.1.100`

#### 3. Obtener tu IP pública

Si necesitas conocer tu IP pública para agregarla a la whitelist:

```bash
# Linux/Mac
curl ifconfig.me
# o
curl ipinfo.io/ip

# Windows (PowerShell)
Invoke-RestMethod ifconfig.me
```

### Endpoints Protegidos vs Públicos

- **Públicos** (no requieren autenticación):
  - `GET /` - Información básica de la API
  - `GET /health` - Health check

- **Protegidos por IP** (solo accesibles desde IPs autorizadas):
  - `GET /docs` - Documentación Swagger UI
  - `GET /redoc` - Documentación ReDoc
  - `GET /openapi.json` - Esquema OpenAPI

- **Protegidos** (requieren API Key e IP autorizada):
  - `POST /send-email` - Enviar correos

### Uso de la API Key

La API Key debe enviarse en el header `X-API-Key` en cada solicitud:

```bash
curl -X POST "http://localhost:8000/send-email" \
  -H "X-API-Key: tu_api_key_secreta_aqui" \
  -H "Content-Type: application/json" \
  -d '{...}'
```

### Detección de IP con Proxies

Si tu API está detrás de un proxy (nginx, Cloudflare, etc.), la API detecta automáticamente la IP real del cliente desde los headers:
- `X-Forwarded-For`
- `X-Real-IP`

### Modo Desarrollo

Si no configuras `API_KEY` o `ALLOWED_IPS`, la API funcionará sin restricciones (útil para desarrollo local). **⚠️ No uses esto en producción.**

### Mejores Prácticas

- ⚠️ **NUNCA** subas el archivo `.env` al control de versiones
- Usa API Keys largas y aleatorias (mínimo 32 caracteres)
- Limita las IPs permitidas solo a las necesarias
- Usa HTTPS en producción (configura un reverse proxy como nginx)
- Rota las API Keys periódicamente
- Usa contraseñas de aplicación cuando sea posible (Gmail, etc.)
- En producción, usa variables de entorno del sistema o un gestor de secretos (AWS Secrets Manager, HashiCorp Vault, etc.)
- Monitorea los logs para detectar intentos de acceso no autorizados

## 🐛 Solución de Problemas

### Error: "Variables de entorno faltantes"
- Verifica que el archivo `.env` existe y está en el directorio raíz
- Asegúrate de que todas las variables requeridas estén definidas

### Error: "Error de autenticación SMTP"
- Verifica que las credenciales sean correctas
- Para Gmail, asegúrate de usar una contraseña de aplicación
- Verifica que la autenticación de dos factores esté configurada correctamente

### Error: "No se puede conectar al servidor SMTP"
- Verifica que el servidor SMTP y el puerto sean correctos
- Verifica tu conexión a internet
- Algunos proveedores bloquean conexiones desde ciertas IPs

## 📄 Licencia

Este proyecto es de código abierto y está disponible para uso educativo.

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o pull request.

---

**¡Disfruta aprendiendo FastAPI!** 🚀

