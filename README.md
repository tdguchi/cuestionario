# Sistema de Cuestionarios

## Requisitos (Docker o Entorno de Ejecución)

### Opción 1: Docker
- Docker instalado en el sistema
- Docker Compose (incluido en Docker Desktop para Windows/Mac)

### Opción 2: Entorno Python
- Python 3.9 o superior
- pip (gestor de paquetes de Python)
- Paquetes requeridos:
  - Flask
  - requests

## Ejecución

### Usando Docker
1. Construir y ejecutar el contenedor:
```bash
docker-compose up --build
```
2. Acceder a la aplicación en: `http://localhost:5000`

### Usando Python directamente
1. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
venv\Scripts\activate     # En Windows
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Ejecutar la aplicación:
```bash
python app.py
```

4. Acceder a la aplicación en: `http://localhost:5000`

## Configuración

### Estructura del archivo JSON
Los archivos JSON para cargar preguntas deben seguir la siguiente estructura:

```json
{
    "asignatura": "Nombre de la Asignatura",
    "questions": [
        {
            "question": "¿Pregunta 1?",
            "answers": [
                "Respuesta 1",
                "Respuesta 2",
                "Respuesta 3",
                "Respuesta 4"
            ],
            "correct_answer": "Respuesta correcta"
        },
        {
            // Más preguntas...
        }
    ]
}
```

#### Campos Requeridos:
- `asignatura`: Nombre de la asignatura o tema del cuestionario
- `questions`: Array de objetos de preguntas
  - `question`: Texto de la pregunta
  - `answers`: Array de posibles respuestas (2-4 respuestas)
  - `correct_answer`: La respuesta correcta (debe coincidir exactamente con una de las respuestas en el array `answers`)

### Discord Webhook
La aplicación incluye integración con Discord para notificar cuando se cargan nuevos archivos de preguntas.

#### Configuración del Webhook:
1. El webhook está configurado en la constante `DISCORD_WEBHOOK_URL` en `app.py`
2. Cuando se carga un nuevo archivo de preguntas, se envía:
   - Mensaje de notificación con:
     - Nombre de la asignatura
     - Fecha y hora de la carga
   - Archivo JSON adjunto con las preguntas

#### Estado de las Preguntas:
Las preguntas en la base de datos tienen tres estados posibles:
- `0`: Pregunta fallada
- `1`: Pregunta acertada
- `2`: Pregunta nueva (no contestada)

Esto permite filtrar preguntas usando las opciones "solo nuevas" y "solo falladas" en la interfaz.
