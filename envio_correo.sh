#!/bin/bash

###############################################################################
# Script para enviar correos electrónicos usando la API MailSystem
#
# Uso:
#   ./envio_correo.sh -m destinatario@email.com -s "Asunto" -b "Cuerpo"
#   ./envio_correo.sh -m email1@test.com,email2@test.com -s "Asunto" -b "Cuerpo" -a archivo.pdf
#
# Parámetros:
#   -m, --mail      Destinatario(s) - puede ser uno o varios separados por comas (requerido)
#   -s, --subject   Asunto del correo (requerido)
#   -b, --body      Cuerpo del correo (requerido)
#   -a, --attach    Archivo adjunto (opcional)
#   -h, --html      Si se especifica, el cuerpo se trata como HTML (opcional)
#   -u, --url       URL de la API (opcional, por defecto: http://localhost:8008)
#   --help          Muestra esta ayuda
#
# Ejemplos:
#   ./envio_correo.sh -m user@example.com -s "Prueba" -b "Hola mundo"
#   ./envio_correo.sh -m user@example.com -s "Reporte" -b "<h1>Reporte</h1>" -h
#   ./envio_correo.sh -m user@example.com -s "Documento" -b "Adjunto" -a documento.pdf
###############################################################################

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Obtener el directorio del script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Intentar cargar la API Key desde el archivo .env si existe
if [ -f "$SCRIPT_DIR/.env" ]; then
    # Extraer API_KEY del archivo .env (ignorar comentarios y espacios)
    ENV_API_KEY=$(grep -E "^API_KEY=" "$SCRIPT_DIR/.env" | cut -d '=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -d '"' | tr -d "'")
    if [ -n "$ENV_API_KEY" ] && [ "$ENV_API_KEY" != "tu_api_key_secreta_aqui" ]; then
        API_KEY="$ENV_API_KEY"
    fi
fi

# API Key - Si no se cargó del .env, puedes configurarla aquí directamente
# Puedes obtenerla del archivo .env o generarla con: openssl rand -hex 32
API_KEY="${API_KEY:-tu_api_key_secreta_aqui}"

# URL de la API (por defecto)
# También se puede configurar en el .env como API_URL
if [ -f "$SCRIPT_DIR/.env" ]; then
    ENV_API_URL=$(grep -E "^API_URL=" "$SCRIPT_DIR/.env" | cut -d '=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr -d '"' | tr -d "'")
    if [ -n "$ENV_API_URL" ]; then
        API_URL="$ENV_API_URL"
    fi
fi
API_URL="${API_URL:-http://localhost:8008}"

# Colores para output (opcional, se desactivan si no hay soporte)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

# Función para mostrar ayuda
show_help() {
    cat << EOF
${BLUE}Script para enviar correos electrónicos usando la API MailSystem${NC}

${GREEN}Uso:${NC}
    $0 [OPCIONES]

${GREEN}Opciones requeridas:${NC}
    -m, --mail DESTINATARIO(S)    Dirección(es) de correo destinataria(s)
                                   Puede ser una o varias separadas por comas
                                   Ejemplo: user@example.com o user1@test.com,user2@test.com

    -s, --subject ASUNTO          Asunto del correo
                                   Ejemplo: "Prueba de correo"

    -b, --body CUERPO             Cuerpo del correo
                                   Ejemplo: "Este es el cuerpo del mensaje"

${GREEN}Opciones opcionales:${NC}
    -a, --attach ARCHIVO          Archivo adjunto
                                   Ejemplo: documento.pdf

    -h, --html                    Indica que el cuerpo es HTML
                                   Sin esta opción, el cuerpo se trata como texto plano

    -u, --url URL                 URL de la API
                                   Por defecto: http://localhost:8008

    --help                        Muestra esta ayuda

${GREEN}Ejemplos:${NC}
    # Correo simple
    $0 -m user@example.com -s "Prueba" -b "Hola mundo"

    # Correo con HTML
    $0 -m user@example.com -s "Reporte" -b "<h1>Reporte</h1>" --html

    # Correo con adjunto
    $0 -m user@example.com -s "Documento" -b "Adjunto" -a documento.pdf

    # Correo a múltiples destinatarios
    $0 -m user1@test.com,user2@test.com -s "Notificación" -b "Mensaje"

    # Correo con adjunto y HTML
    $0 -m user@example.com -s "Reporte" -b "<p>Reporte adjunto</p>" -a reporte.xlsx --html

${YELLOW}Nota:${NC} Asegúrate de configurar la API_KEY en el script antes de usarlo.
EOF
    exit 0
}

# Función para mostrar mensajes de error
error() {
    echo -e "${RED}❌ Error:${NC} $1" >&2
    exit 1
}

# Función para mostrar mensajes de éxito
success() {
    echo -e "${GREEN}✅${NC} $1"
}

# Función para mostrar información
info() {
    echo -e "${BLUE}ℹ️${NC} $1"
}

# Función para mostrar advertencias
warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

# Función para codificar archivo en base64
encode_file() {
    local file="$1"
    
    if [ ! -f "$file" ]; then
        error "El archivo '$file' no existe o no es un archivo válido"
    fi
    
    if [ ! -r "$file" ]; then
        error "No se puede leer el archivo '$file' (permisos insuficientes)"
    fi
    
    # Codificar en base64
    # Usar base64 si está disponible, si no, intentar con openssl
    if command -v base64 &> /dev/null; then
        base64 -i "$file" 2>/dev/null || base64 "$file"
    elif command -v openssl &> /dev/null; then
        openssl base64 -in "$file" -A
    else
        error "No se encontró 'base64' ni 'openssl' para codificar el archivo"
    fi
}

# Función para obtener el tipo MIME de un archivo
get_mime_type() {
    local file="$1"
    local extension="${file##*.}"
    extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')
    
    case "$extension" in
        pdf) echo "application/pdf" ;;
        doc) echo "application/msword" ;;
        docx) echo "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ;;
        xls) echo "application/vnd.ms-excel" ;;
        xlsx) echo "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" ;;
        txt) echo "text/plain" ;;
        html|htm) echo "text/html" ;;
        jpg|jpeg) echo "image/jpeg" ;;
        png) echo "image/png" ;;
        gif) echo "image/gif" ;;
        zip) echo "application/zip" ;;
        json) echo "application/json" ;;
        xml) echo "application/xml" ;;
        csv) echo "text/csv" ;;
        *) echo "application/octet-stream" ;;
    esac
}

# Función para validar email (básico)
validate_email() {
    local email="$1"
    if [[ ! "$email" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        return 1
    fi
    return 0
}

# Función para validar emails (puede ser múltiples separados por comas)
validate_emails() {
    local emails="$1"
    IFS=',' read -ra EMAIL_ARRAY <<< "$emails"
    
    for email in "${EMAIL_ARRAY[@]}"; do
        email=$(echo "$email" | xargs) # Trim whitespace
        if ! validate_email "$email"; then
            error "Email inválido: '$email'"
        fi
    done
}

# ============================================================================
# PARSING DE ARGUMENTOS
# ============================================================================

# Variables para almacenar los parámetros
MAIL=""
SUBJECT=""
BODY=""
ATTACHMENT=""
IS_HTML=false

# Parsear argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mail)
            MAIL="$2"
            shift 2
            ;;
        -s|--subject)
            SUBJECT="$2"
            shift 2
            ;;
        -b|--body)
            BODY="$2"
            shift 2
            ;;
        -a|--attach)
            ATTACHMENT="$2"
            shift 2
            ;;
        -h|--html)
            IS_HTML=true
            shift
            ;;
        -u|--url)
            API_URL="$2"
            shift 2
            ;;
        --help)
            show_help
            ;;
        *)
            error "Opción desconocida: $1\nUsa --help para ver la ayuda"
            ;;
    esac
done

# ============================================================================
# VALIDACIÓN DE PARÁMETROS
# ============================================================================

# Verificar que la API Key esté configurada
if [ "$API_KEY" = "tu_api_key_secreta_aqui" ] || [ -z "$API_KEY" ]; then
    error "La API_KEY no está configurada. Por favor, edita el script y configura tu API Key."
fi

# Verificar parámetros requeridos
if [ -z "$MAIL" ]; then
    error "El parámetro -m (destinatario) es requerido. Usa --help para ver la ayuda."
fi

if [ -z "$SUBJECT" ]; then
    error "El parámetro -s (asunto) es requerido. Usa --help para ver la ayuda."
fi

if [ -z "$BODY" ]; then
    error "El parámetro -b (cuerpo) es requerido. Usa --help para ver la ayuda."
fi

# Validar emails
validate_emails "$MAIL"

# Verificar que curl esté disponible
if ! command -v curl &> /dev/null; then
    error "curl no está instalado. Por favor, instálalo para usar este script."
fi

# ============================================================================
# PREPARACIÓN DE DATOS
# ============================================================================

info "Preparando el correo..."

# Convertir emails a array JSON
IFS=',' read -ra EMAIL_ARRAY <<< "$MAIL"
EMAIL_JSON="["
for i in "${!EMAIL_ARRAY[@]}"; do
    email=$(echo "${EMAIL_ARRAY[$i]}" | xargs) # Trim
    if [ $i -gt 0 ]; then
        EMAIL_JSON+=","
    fi
    EMAIL_JSON+="\"$email\""
done
EMAIL_JSON+="]"

# Preparar el JSON base
# Escapar caracteres especiales para JSON
escape_json() {
    local str="$1"
    # Escapar comillas, backslashes, newlines, tabs, etc.
    str=$(echo "$str" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g' | sed 's/\n/\\n/g' | sed 's/\r/\\r/g' | sed 's/\t/\\t/g')
    echo "$str"
}

SUBJECT_ESCAPED=$(escape_json "$SUBJECT")
BODY_ESCAPED=$(escape_json "$BODY")

# Construir JSON (usar jq si está disponible, si no construir manualmente)
if command -v jq &> /dev/null; then
    JSON_PAYLOAD=$(cat <<EOF | jq -n --arg subject "$SUBJECT" --arg body "$BODY" --argjson recipients "$EMAIL_JSON" --argjson is_html "$IS_HTML" '{subject: $subject, body: $body, recipients: $recipients, is_html: $is_html}'
EOF
)
else
    # Construcción manual del JSON
    JSON_PAYLOAD=$(cat <<EOF
{
  "subject": "$SUBJECT_ESCAPED",
  "body": "$BODY_ESCAPED",
  "recipients": $EMAIL_JSON,
  "is_html": $IS_HTML
}
EOF
)
fi

# Si hay archivo adjunto, agregarlo
if [ -n "$ATTACHMENT" ]; then
    info "Codificando archivo adjunto: $ATTACHMENT"
    
    FILENAME=$(basename "$ATTACHMENT")
    FILE_CONTENT=$(encode_file "$ATTACHMENT")
    MIME_TYPE=$(get_mime_type "$ATTACHMENT")
    
    # Construir el JSON con el adjunto
    # Escapar el contenido del archivo para JSON
    FILE_CONTENT_ESCAPED=$(echo "$FILE_CONTENT" | sed 's/\\/\\\\/g' | sed 's/"/\\"/g')
    FILENAME_ESCAPED=$(escape_json "$FILENAME")
    MIME_TYPE_ESCAPED=$(escape_json "$MIME_TYPE")
    
    # Usar jq si está disponible, si no, construir manualmente
    if command -v jq &> /dev/null; then
        JSON_PAYLOAD=$(echo "$JSON_PAYLOAD" | jq --arg filename "$FILENAME" \
            --arg content "$FILE_CONTENT" \
            --arg mime "$MIME_TYPE" \
            '. + {attachments: [{filename: $filename, content: $content, content_type: $mime}]}')
    else
        # Construcción manual del JSON
        # Remover el último } del JSON base
        JSON_PAYLOAD="${JSON_PAYLOAD%?}"
        # Agregar el attachment
        JSON_PAYLOAD+=$(cat <<EOF
,
  "attachments": [
    {
      "filename": "$FILENAME_ESCAPED",
      "content": "$FILE_CONTENT_ESCAPED",
      "content_type": "$MIME_TYPE_ESCAPED"
    }
  ]
}
EOF
)
    fi
    
    success "Archivo adjunto preparado: $FILENAME ($MIME_TYPE)"
fi

# ============================================================================
# ENVÍO DEL CORREO
# ============================================================================

info "Enviando correo a través de la API..."
info "URL: $API_URL/send-email"
info "Destinatario(s): $MAIL"
info "Asunto: $SUBJECT"

# Realizar la petición
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -d "$JSON_PAYLOAD" \
    "$API_URL/send-email")

# Separar el cuerpo de la respuesta del código HTTP
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '$d')

# Verificar el código de respuesta HTTP
if [ "$HTTP_CODE" -eq 200 ] || [ "$HTTP_CODE" -eq 201 ]; then
    success "Correo enviado exitosamente!"
    
    # Mostrar la respuesta de la API si está disponible
    if command -v jq &> /dev/null && [ -n "$RESPONSE_BODY" ]; then
        echo ""
        echo "$RESPONSE_BODY" | jq .
    elif [ -n "$RESPONSE_BODY" ]; then
        echo ""
        echo "$RESPONSE_BODY"
    fi
    exit 0
else
    # Mostrar el error
    error "Error al enviar el correo (HTTP $HTTP_CODE)"
    echo ""
    if command -v jq &> /dev/null && [ -n "$RESPONSE_BODY" ]; then
        echo "$RESPONSE_BODY" | jq . >&2
    elif [ -n "$RESPONSE_BODY" ]; then
        echo "$RESPONSE_BODY" >&2
    fi
    exit 1
fi

