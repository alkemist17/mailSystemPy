"""
Ejemplo de uso de la API MailSystem

Este script muestra cómo usar la API para enviar correos electrónicos
desde Python usando la biblioteca requests.
"""

import requests
import base64
import json
import os

# URL base de la API
API_URL = "http://localhost:8000"

# API Key - Cargar desde variable de entorno o usar directamente
# En producción, usa variables de entorno: os.getenv('API_KEY')
API_KEY = os.getenv('API_KEY', 'tu_api_key_secreta_aqui')

# Headers con autenticación
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

def ejemplo_correo_simple():
    """Ejemplo 1: Enviar un correo simple con texto plano"""
    print("📧 Enviando correo simple...")
    
    response = requests.post(
        f"{API_URL}/send-email",
        headers=HEADERS,
        json={
            "subject": "Prueba de correo simple",
            "body": "Este es un correo de prueba desde la API MailSystem.",
            "recipients": ["destinatario@example.com"]
        }
    )
    
    print(f"Estado: {response.status_code}")
    print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
    print()


def ejemplo_correo_html():
    """Ejemplo 2: Enviar un correo con formato HTML"""
    print("📧 Enviando correo HTML...")
    
    html_body = """
    <html>
        <body>
            <h1 style="color: #4CAF50;">¡Hola!</h1>
            <p>Este es un correo con <strong>formato HTML</strong>.</p>
            <ul>
                <li>Elemento 1</li>
                <li>Elemento 2</li>
                <li>Elemento 3</li>
            </ul>
            <p>Saludos,<br>MailSystem API</p>
        </body>
    </html>
    """
    
    response = requests.post(
        f"{API_URL}/send-email",
        headers=HEADERS,
        json={
            "subject": "Correo con formato HTML",
            "body": html_body,
            "recipients": ["destinatario@example.com"],
            "is_html": True
        }
    )
    
    print(f"Estado: {response.status_code}")
    print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
    print()


def ejemplo_correo_con_adjunto():
    """Ejemplo 3: Enviar un correo con archivo adjunto"""
    print("📧 Enviando correo con adjunto...")
    
    # Crear un archivo de ejemplo en memoria (texto)
    # En un caso real, leerías un archivo del sistema de archivos
    contenido_archivo = "Este es el contenido de un archivo de ejemplo.\nPuede contener cualquier texto."
    contenido_base64 = base64.b64encode(contenido_archivo.encode('utf-8')).decode('utf-8')
    
    response = requests.post(
        f"{API_URL}/send-email",
        headers=HEADERS,
        json={
            "subject": "Correo con archivo adjunto",
            "body": "Por favor encuentra adjunto el archivo de ejemplo.",
            "recipients": ["destinatario@example.com"],
            "attachments": [
                {
                    "filename": "ejemplo.txt",
                    "content": contenido_base64,
                    "content_type": "text/plain"
                }
            ]
        }
    )
    
    print(f"Estado: {response.status_code}")
    print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
    print()


def ejemplo_correo_multiple_destinatarios():
    """Ejemplo 4: Enviar correo a múltiples destinatarios"""
    print("📧 Enviando correo a múltiples destinatarios...")
    
    response = requests.post(
        f"{API_URL}/send-email",
        headers=HEADERS,
        json={
            "subject": "Correo a múltiples destinatarios",
            "body": "Este correo se enviará a todos los destinatarios en la lista.",
            "recipients": [
                "destinatario1@example.com",
                "destinatario2@example.com",
                "destinatario3@example.com"
            ]
        }
    )
    
    print(f"Estado: {response.status_code}")
    print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
    print()


def ejemplo_adjunto_desde_archivo(ruta_archivo: str):
    """
    Ejemplo 5: Enviar correo con adjunto desde un archivo del sistema
    
    Args:
        ruta_archivo: Ruta al archivo que se desea adjuntar
    """
    print(f"📧 Enviando correo con adjunto desde archivo: {ruta_archivo}")
    
    try:
        # Leer el archivo y codificarlo en base64
        with open(ruta_archivo, "rb") as f:
            contenido = f.read()
            contenido_base64 = base64.b64encode(contenido).decode('utf-8')
        
        # Determinar el tipo MIME basado en la extensión
        extension = ruta_archivo.split('.')[-1].lower()
        tipos_mime = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        }
        content_type = tipos_mime.get(extension, 'application/octet-stream')
        
        # Obtener solo el nombre del archivo (sin la ruta)
        nombre_archivo = ruta_archivo.split('/')[-1]
        
        response = requests.post(
            f"{API_URL}/send-email",
            headers=HEADERS,
            json={
                "subject": f"Correo con adjunto: {nombre_archivo}",
                "body": f"Por favor encuentra adjunto el archivo {nombre_archivo}.",
                "recipients": ["destinatario@example.com"],
                "attachments": [
                    {
                        "filename": nombre_archivo,
                        "content": contenido_base64,
                        "content_type": content_type
                    }
                ]
            }
        )
        
        print(f"Estado: {response.status_code}")
        print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
        print()
        
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {ruta_archivo}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")


def verificar_salud_api():
    """Verificar que la API esté funcionando correctamente"""
    print("🏥 Verificando salud de la API...")
    
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"Estado: {response.status_code}")
        print(f"Respuesta: {json.dumps(response.json(), indent=2)}")
        print()
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error al conectar con la API: {str(e)}")
        print("Asegúrate de que la API esté ejecutándose en http://localhost:8000")
        print()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("EJEMPLOS DE USO DE LA API MAILSYSTEM")
    print("=" * 60)
    print()
    
    # Verificar que la API esté funcionando
    if not verificar_salud_api():
        print("⚠️  La API no está disponible. Por favor, inicia la API primero.")
        print("   Ejecuta: docker-compose up")
        exit(1)
    
    # Ejecutar ejemplos
    # Descomenta los ejemplos que quieras probar:
    
    # ejemplo_correo_simple()
    # ejemplo_correo_html()
    # ejemplo_correo_con_adjunto()
    # ejemplo_correo_multiple_destinatarios()
    # ejemplo_adjunto_desde_archivo("ruta/a/tu/archivo.pdf")
    
    print("💡 Descomenta los ejemplos en el código para probarlos.")
    print("⚠️  Recuerda cambiar 'destinatario@example.com' por direcciones reales.")
    print("🔑 Asegúrate de configurar tu API_KEY en el archivo .env o como variable de entorno.")
    print(f"📝 API Key actual: {'Configurada' if API_KEY != 'tu_api_key_secreta_aqui' else 'NO CONFIGURADA (usando valor por defecto)'}")

