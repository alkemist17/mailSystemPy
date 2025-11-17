"""
API de Envío de Correos Electrónicos con FastAPI

Esta aplicación proporciona una API REST para enviar correos electrónicos
utilizando SMTP. Está construida con FastAPI, un framework moderno y rápido
para construir APIs con Python.

Autor: MailSystem API
Versión: 1.0.0
"""

from fastapi import FastAPI, HTTPException, status, Depends, Security, Request
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64
from datetime import datetime
import logging
from dotenv import load_dotenv
import ipaddress

# Cargar variables de entorno desde el archivo .env
# Esto es útil para desarrollo local
# En Docker, las variables se cargan automáticamente desde docker-compose.yml
load_dotenv()

# Configuración de logging para depuración
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# ============================================================================

# API Key Header - El cliente debe enviar la API Key en el header X-API-Key
# FastAPI Security proporciona una forma estándar de manejar autenticación
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_allowed_ips():
    """
    Obtiene la lista de IPs permitidas desde las variables de entorno.
    
    La variable ALLOWED_IPS debe contener IPs separadas por comas.
    Ejemplo: "127.0.0.1,192.168.1.100,10.0.0.5"
    
    También soporta rangos CIDR, ej: "192.168.1.0/24"
    
    Returns:
        list: Lista de IPs o rangos permitidos
    """
    allowed_ips_str = os.getenv('ALLOWED_IPS', '')
    if not allowed_ips_str:
        return []
    
    # Separar por comas y limpiar espacios
    ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()]
    return ips


def get_api_key():
    """
    Obtiene la API Key desde las variables de entorno.
    
    Returns:
        str: API Key configurada, o None si no está configurada
    """
    return os.getenv('API_KEY')


def verify_ip_address(client_ip: str) -> bool:
    """
    Verifica si la IP del cliente está en la lista de IPs permitidas.
    
    Soporta:
    - IPs individuales: "192.168.1.100"
    - Rangos CIDR: "192.168.1.0/24"
    - IPs locales: "127.0.0.1", "localhost"
    
    Args:
        client_ip: IP del cliente a verificar
        
    Returns:
        bool: True si la IP está permitida, False en caso contrario
    """
    allowed_ips = get_allowed_ips()
    
    # Si no hay IPs configuradas, permitir todas (modo desarrollo)
    if not allowed_ips:
        logger.warning("No hay IPs permitidas configuradas. Permitindo todas las IPs.")
        return True
    
    # Normalizar localhost
    if client_ip in ['127.0.0.1', '::1', 'localhost']:
        client_ip = '127.0.0.1'
    
    # Verificar cada IP o rango permitido
    for allowed_ip in allowed_ips:
        try:
            # Si es un rango CIDR
            if '/' in allowed_ip:
                if ipaddress.ip_address(client_ip) in ipaddress.ip_network(allowed_ip, strict=False):
                    return True
            # Si es una IP individual
            else:
                if client_ip == allowed_ip:
                    return True
        except ValueError:
            # Si hay un error al parsear la IP, continuar con la siguiente
            logger.warning(f"IP o rango inválido en ALLOWED_IPS: {allowed_ip}")
            continue
    
    return False


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Verifica que la API Key proporcionada sea válida.
    
    Esta función se usa como dependencia en FastAPI. Si la API Key
    no es válida, lanza una excepción HTTP 401.
    
    Args:
        api_key: API Key proporcionada en el header X-API-Key
        
    Returns:
        str: API Key válida
        
    Raises:
        HTTPException: Si la API Key no es válida o no se proporcionó
    """
    expected_api_key = get_api_key()
    
    # Si no hay API Key configurada, no requerir autenticación (modo desarrollo)
    if not expected_api_key:
        logger.warning("No hay API_KEY configurada. La autenticación está deshabilitada.")
        return "no-key-required"
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida. Proporciona la API Key en el header X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    if api_key != expected_api_key:
        logger.warning(f"Intento de acceso con API Key inválida desde IP desconocida")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key


def verify_access(request: Request, api_key: str = Depends(verify_api_key)) -> str:
    """
    Verifica tanto la API Key como la IP del cliente.
    
    Esta es la dependencia principal que se usa en los endpoints protegidos.
    Verifica:
    1. Que la API Key sea válida
    2. Que la IP del cliente esté en la whitelist
    
    Args:
        request: Objeto Request de FastAPI (contiene información de la solicitud)
        api_key: API Key validada (proporcionada por verify_api_key)
        
    Returns:
        str: API Key válida
        
    Raises:
        HTTPException: Si la IP no está permitida o la API Key es inválida
    """
    # Obtener la IP del cliente
    # FastAPI puede obtener la IP desde diferentes headers dependiendo del proxy
    client_ip = request.client.host if request.client else "unknown"
    
    # Si hay un proxy (como nginx, cloudflare, etc.), la IP real puede estar en headers
    # X-Forwarded-For contiene la IP original del cliente
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For puede contener múltiples IPs, la primera es la original
        client_ip = forwarded_for.split(",")[0].strip()
    
    # También verificar X-Real-IP (usado por algunos proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        client_ip = real_ip.strip()
    
    # Si la IP es de una red Docker (172.x.x.x, 192.168.x.x comunes en Docker)
    # y 127.0.0.1 está en la whitelist, permitir el acceso
    # Esto permite acceso desde localhost a través de Docker
    allowed_ips = get_allowed_ips()
    if "127.0.0.1" in allowed_ips:
        # Verificar si es una IP de red Docker común
        if (client_ip.startswith("172.") or 
            client_ip.startswith("192.168.") or 
            client_ip.startswith("10.")):
            # Si es una IP de red privada y localhost está permitido, permitir acceso
            logger.info(f"Acceso desde red Docker/privada ({client_ip}) permitido porque localhost está en whitelist")
            return api_key
    
    # Verificar que la IP esté permitida
    if not verify_ip_address(client_ip):
        logger.warning(f"Intento de acceso desde IP no permitida: {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acceso denegado. Tu IP ({client_ip}) no está en la lista de IPs permitidas."
        )
    
    logger.info(f"Acceso autorizado desde IP: {client_ip}")
    return api_key


def get_client_ip(request: Request) -> str:
    """
    Obtiene la IP real del cliente desde la solicitud.
    Considera proxies y headers como X-Forwarded-For y X-Real-IP.
    
    Args:
        request: Objeto Request de FastAPI
        
    Returns:
        str: IP del cliente
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Si hay un proxy, la IP real puede estar en headers
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        client_ip = real_ip.strip()
    
    return client_ip


class DocsAccessMiddleware(BaseHTTPMiddleware):
    """
    Middleware para restringir el acceso a la documentación (Swagger/ReDoc)
    solo a las IPs permitidas.
    
    Este middleware intercepta las solicitudes a /docs y /redoc y verifica
    que la IP del cliente esté en la whitelist antes de permitir el acceso.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Rutas de documentación que queremos proteger
        docs_paths = ["/docs", "/redoc", "/openapi.json"]
        
        # Verificar si la ruta es de documentación
        if any(request.url.path.startswith(path) for path in docs_paths):
            client_ip = get_client_ip(request)
            
            # Obtener IPs permitidas
            allowed_ips = get_allowed_ips()
            
            # Si no hay IPs configuradas, permitir todas (modo desarrollo)
            if not allowed_ips:
                logger.warning("No hay IPs permitidas configuradas. Permitindo acceso a documentación desde todas las IPs.")
                return await call_next(request)
            
            # Verificar si la IP está permitida
            # Si 127.0.0.1 está permitido, también permitir IPs de red Docker/privada
            ip_allowed = False
            
            if "127.0.0.1" in allowed_ips:
                # Permitir localhost y redes Docker/privadas
                if (client_ip in ['127.0.0.1', '::1', 'localhost'] or
                    client_ip.startswith("172.") or
                    client_ip.startswith("192.168.") or
                    client_ip.startswith("10.")):
                    ip_allowed = True
                    logger.info(f"Acceso a documentación desde red Docker/privada ({client_ip}) permitido porque localhost está en whitelist")
            
            # Si no se permitió por la regla anterior, verificar normalmente
            if not ip_allowed:
                ip_allowed = verify_ip_address(client_ip)
            
            if not ip_allowed:
                logger.warning(f"Intento de acceso a documentación desde IP no permitida: {client_ip}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "detail": f"Acceso denegado. Tu IP ({client_ip}) no está autorizada para acceder a la documentación."
                    }
                )
            
            logger.info(f"Acceso a documentación autorizado desde IP: {client_ip}")
        
        # Continuar con la solicitud
        return await call_next(request)


# Crear instancia de FastAPI
# FastAPI es un framework web moderno y rápido para construir APIs
# con Python basado en estándares web como OpenAPI y JSON Schema
app = FastAPI(
    title="MailSystem API",
    description="""
    API para envío de correos electrónicos mediante SMTP.
    
    ## Características
    
    * Envío de correos con asunto, cuerpo y destinatarios
    * Soporte para múltiples destinatarios
    * Soporte para archivos adjuntos
    * Validación de datos de entrada
    * Documentación automática con Swagger/OpenAPI (acceso restringido por IP)
    """,
    version="1.0.0",
    docs_url="/docs",  # Ruta para la documentación interactiva (Swagger UI)
    redoc_url="/redoc"  # Ruta para la documentación alternativa (ReDoc)
)

# Agregar middleware para restringir acceso a la documentación
# Este middleware debe agregarse después de crear la app pero antes de definir los endpoints
app.add_middleware(DocsAccessMiddleware)


# ============================================================================
# MODELOS DE DATOS (Pydantic)
# ============================================================================
# Pydantic es una biblioteca de validación de datos que FastAPI usa
# para validar automáticamente los datos de entrada y salida

class Attachment(BaseModel):
    """
    Modelo para representar un archivo adjunto.
    
    Attributes:
        filename: Nombre del archivo
        content: Contenido del archivo en base64
        content_type: Tipo MIME del archivo (opcional)
    """
    filename: str = Field(..., description="Nombre del archivo adjunto")
    content: str = Field(..., description="Contenido del archivo en base64")
    content_type: Optional[str] = Field(
        None, 
        description="Tipo MIME del archivo (ej: application/pdf, image/png)"
    )


class EmailRequest(BaseModel):
    """
    Modelo para la solicitud de envío de correo.
    
    Este modelo define la estructura de datos que el cliente debe enviar
    para solicitar el envío de un correo electrónico.
    
    Attributes:
        subject: Asunto del correo
        body: Cuerpo del correo (puede ser texto plano o HTML)
        recipients: Lista de destinatarios (puede ser uno o varios)
        attachments: Lista opcional de archivos adjuntos
        is_html: Indica si el cuerpo es HTML (por defecto False)
    """
    subject: str = Field(
        ..., 
        min_length=1,
        max_length=500,
        description="Asunto del correo electrónico"
    )
    body: str = Field(
        ..., 
        min_length=1,
        description="Cuerpo del correo (texto plano o HTML)"
    )
    recipients: List[EmailStr] = Field(
        ..., 
        min_items=1,
        description="Lista de direcciones de correo destinatarias"
    )
    attachments: Optional[List[Attachment]] = Field(
        None,
        description="Lista opcional de archivos adjuntos"
    )
    is_html: bool = Field(
        False,
        description="Indica si el cuerpo del correo es HTML"
    )

    @validator('recipients')
    def validate_recipients(cls, v):
        """
        Validador personalizado para asegurar que hay al menos un destinatario.
        
        Los validadores en Pydantic permiten agregar lógica de validación
        personalizada a los campos del modelo.
        """
        if not v or len(v) == 0:
            raise ValueError('Debe haber al menos un destinatario')
        return v


class EmailResponse(BaseModel):
    """
    Modelo para la respuesta del envío de correo.
    
    Este modelo define la estructura de la respuesta que se envía
    al cliente después de intentar enviar un correo.
    
    Attributes:
        success: Indica si el envío fue exitoso
        message: Mensaje descriptivo del resultado
        timestamp: Fecha y hora del envío
        recipients: Lista de destinatarios a los que se envió
    """
    success: bool
    message: str
    timestamp: str
    recipients: List[str]


# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_smtp_config():
    """
    Obtiene la configuración SMTP desde variables de entorno.
    
    Las variables de entorno se cargan desde el archivo .env
    usando python-dotenv (se carga automáticamente en el Dockerfile).
    
    Returns:
        dict: Diccionario con la configuración SMTP
        
    Raises:
        ValueError: Si alguna variable de entorno requerida no está definida
    """
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    
    config = {
        'smtp_server': os.getenv('SMTP_SERVER'),
        'smtp_port': smtp_port,
        'smtp_user': os.getenv('SMTP_USER'),
        'smtp_password': os.getenv('SMTP_PASSWORD'),
        'smtp_from_email': os.getenv('SMTP_FROM_EMAIL'),
        'smtp_use_tls': os.getenv('SMTP_USE_TLS', 'true').lower() == 'true',
        # El puerto 465 usa SSL directamente, no TLS con starttls()
        'smtp_use_ssl': smtp_port == 465
    }
    
    # Validar que las variables requeridas estén definidas
    required_vars = ['smtp_server', 'smtp_user', 'smtp_password', 'smtp_from_email']
    missing_vars = [var for var in required_vars if not config[var]]
    
    if missing_vars:
        raise ValueError(
            f"Variables de entorno faltantes: {', '.join(missing_vars)}. "
            "Por favor, configura el archivo .env"
        )
    
    return config


def decode_base64_attachment(attachment: Attachment) -> bytes:
    """
    Decodifica el contenido de un adjunto desde base64.
    
    Los archivos adjuntos se envían codificados en base64 para
    poder transmitirlos como texto en JSON.
    
    Args:
        attachment: Objeto Attachment con el contenido en base64
        
    Returns:
        bytes: Contenido del archivo decodificado
        
    Raises:
        ValueError: Si el contenido base64 no es válido
    """
    try:
        return base64.b64decode(attachment.content)
    except Exception as e:
        raise ValueError(f"Error al decodificar el adjunto {attachment.filename}: {str(e)}")


def send_email(
    subject: str,
    body: str,
    recipients: List[str],
    attachments: Optional[List[Attachment]] = None,
    is_html: bool = False
) -> dict:
    """
    Envía un correo electrónico usando SMTP.
    
    Esta función maneja todo el proceso de envío de correo:
    1. Crea el mensaje MIME
    2. Agrega el asunto, remitente y destinatarios
    3. Agrega el cuerpo (texto o HTML)
    4. Agrega los archivos adjuntos si los hay
    5. Se conecta al servidor SMTP y envía el correo
    
    Args:
        subject: Asunto del correo
        body: Cuerpo del correo
        recipients: Lista de destinatarios
        attachments: Lista opcional de archivos adjuntos
        is_html: Si es True, el cuerpo se trata como HTML
        
    Returns:
        dict: Diccionario con el resultado del envío
        
    Raises:
        Exception: Si ocurre un error durante el envío
    """
    try:
        # Obtener configuración SMTP
        smtp_config = get_smtp_config()
        
        # Crear mensaje MIME multipart
        # MIMEMultipart permite agregar múltiples partes al mensaje
        # (cuerpo de texto, HTML, adjuntos, etc.)
        msg = MIMEMultipart()
        msg['From'] = smtp_config['smtp_from_email']
        msg['To'] = ', '.join(recipients)  # Múltiples destinatarios separados por coma
        msg['Subject'] = subject
        
        # Agregar el cuerpo del mensaje
        # MIMEText crea una parte de texto del mensaje
        # El segundo parámetro indica el subtipo: 'plain' para texto, 'html' para HTML
        msg.attach(MIMEText(body, 'html' if is_html else 'plain', 'utf-8'))
        
        # Agregar archivos adjuntos si los hay
        if attachments:
            for attachment in attachments:
                # Decodificar el contenido del adjunto
                file_content = decode_base64_attachment(attachment)
                
                # Crear parte MIME para el adjunto
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file_content)
                
                # Codificar el adjunto en base64 para el transporte
                encoders.encode_base64(part)
                
                # Agregar headers al adjunto
                # Content-Disposition indica que es un adjunto y su nombre
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment.filename}'
                )
                
                # Si se especificó un content_type, usarlo
                if attachment.content_type:
                    part.set_type(attachment.content_type)
                
                # Adjuntar al mensaje
                msg.attach(part)
        
        # Conectar al servidor SMTP y enviar el correo
        # smtplib es la biblioteca estándar de Python para SMTP
        
        # El puerto 465 usa SSL directamente (SMTP_SSL)
        # Los puertos 587 y otros usan TLS con starttls() (SMTP)
        if smtp_config['smtp_use_ssl']:
            # SMTP_SSL crea una conexión SSL desde el inicio
            # Se usa típicamente con el puerto 465
            with smtplib.SMTP_SSL(
                smtp_config['smtp_server'],
                smtp_config['smtp_port']
            ) as server:
                # Habilitar modo debug (opcional, útil para depuración)
                # server.set_debuglevel(1)
                
                # Autenticarse en el servidor SMTP
                server.login(
                    smtp_config['smtp_user'],
                    smtp_config['smtp_password']
                )
                
                # Enviar el correo
                # send_message envía el mensaje MIME completo
                server.send_message(msg)
        else:
            # SMTP crea una conexión sin encriptar primero
            # Luego se puede usar starttls() para encriptar (puerto 587)
            with smtplib.SMTP(
                smtp_config['smtp_server'],
                smtp_config['smtp_port']
            ) as server:
                # Habilitar modo debug (opcional, útil para depuración)
                # server.set_debuglevel(1)
                
                # Iniciar conexión TLS si está configurado
                # TLS (Transport Layer Security) encripta la conexión
                # Se usa típicamente con el puerto 587
                if smtp_config['smtp_use_tls']:
                    server.starttls()
                
                # Autenticarse en el servidor SMTP
                server.login(
                    smtp_config['smtp_user'],
                    smtp_config['smtp_password']
                )
                
                # Enviar el correo
                # send_message envía el mensaje MIME completo
                server.send_message(msg)
        
        logger.info(f"Correo enviado exitosamente a {recipients}")
        
        return {
            'success': True,
            'message': f'Correo enviado exitosamente a {len(recipients)} destinatario(s)',
            'recipients': recipients
        }
        
    except Exception as e:
        logger.error(f"Error al enviar correo: {str(e)}")
        raise


# ============================================================================
# ENDPOINTS DE LA API
# ============================================================================

@app.get("/")
async def root():
    """
    Endpoint raíz de la API.
    
    Este es un endpoint simple que devuelve información básica
    sobre la API. Es útil para verificar que la API está funcionando.
    Este endpoint NO requiere autenticación.
    
    Returns:
        dict: Mensaje de bienvenida e información de la API
    """
    return {
        "message": "Bienvenido a MailSystem API",
        "version": "1.0.0",
        "docs": "/docs",
        "description": "API para envío de correos electrónicos",
        "note": "Los endpoints protegidos requieren API Key y IP autorizada"
    }


@app.get("/health")
async def health_check():
    """
    Endpoint de verificación de salud (health check).
    
    Este endpoint es útil para monitoreo y verificar que la API
    está funcionando correctamente. También verifica que la
    configuración SMTP esté disponible.
    Este endpoint NO requiere autenticación (útil para monitoreo).
    
    Returns:
        dict: Estado de la API y configuración SMTP (sin exponer contraseñas)
        
    Raises:
        HTTPException: Si la configuración SMTP no está completa
    """
    try:
        smtp_config = get_smtp_config()
        api_key_configured = bool(get_api_key())
        allowed_ips = get_allowed_ips()
        
        return {
            "status": "healthy",
            "smtp_server": smtp_config['smtp_server'],
            "smtp_port": smtp_config['smtp_port'],
            "smtp_from_email": smtp_config['smtp_from_email'],
            "smtp_configured": True,
            "security": {
                "api_key_configured": api_key_configured,
                "ip_whitelist_enabled": len(allowed_ips) > 0,
                "allowed_ips_count": len(allowed_ips)
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@app.post("/send-email", response_model=EmailResponse)
async def send_email_endpoint(
    email_request: EmailRequest,
    api_key: str = Depends(verify_access)
):
    """
    Endpoint principal para enviar correos electrónicos.
    
    Este endpoint recibe una solicitud de envío de correo, valida
    los datos (automáticamente mediante Pydantic), y envía el correo
    usando la función send_email().
    
    **SEGURIDAD**: Este endpoint requiere:
    - API Key válida en el header X-API-Key
    - IP del cliente en la whitelist de IPs permitidas
    
    FastAPI automáticamente:
    - Valida los datos de entrada según el modelo EmailRequest
    - Serializa la respuesta según el modelo EmailResponse
    - Genera documentación OpenAPI/Swagger
    
    Args:
        email_request: Datos del correo a enviar (validados automáticamente)
        api_key: API Key validada (proporcionada por la dependencia verify_access)
        
    Returns:
        EmailResponse: Resultado del envío con detalles
        
    Raises:
        HTTPException: Si ocurre un error durante el envío, autenticación o autorización
    """
    try:
        # Enviar el correo
        result = send_email(
            subject=email_request.subject,
            body=email_request.body,
            recipients=[str(email) for email in email_request.recipients],
            attachments=email_request.attachments,
            is_html=email_request.is_html
        )
        
        # Crear respuesta con timestamp
        response = EmailResponse(
            success=result['success'],
            message=result['message'],
            timestamp=datetime.now().isoformat(),
            recipients=result['recipients']
        )
        
        return response
        
    except ValueError as e:
        # Error de validación (ej: base64 inválido)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except smtplib.SMTPAuthenticationError as e:
        # Error de autenticación SMTP
        logger.error(f"Error de autenticación SMTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Error de autenticación SMTP. Verifica las credenciales."
        )
    except smtplib.SMTPException as e:
        # Otros errores SMTP
        logger.error(f"Error SMTP: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al comunicarse con el servidor SMTP: {str(e)}"
        )
    except Exception as e:
        # Error genérico
        logger.error(f"Error inesperado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
# Este bloque solo se ejecuta si el archivo se ejecuta directamente
# (no cuando se importa como módulo)

if __name__ == "__main__":
    """
    Permite ejecutar la aplicación directamente con: python main.py
    
    uvicorn es el servidor ASGI que FastAPI usa por defecto.
    ASGI (Asynchronous Server Gateway Interface) permite que FastAPI
    maneje múltiples solicitudes de forma asíncrona.
    """
    import uvicorn
    
    # uvicorn.run() inicia el servidor
    # host="0.0.0.0" permite acceso desde cualquier IP
    # port=8000 es el puerto por defecto
    # reload=True habilita recarga automática en desarrollo
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

