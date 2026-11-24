PrepCards

Plataforma para preparar entrevistas técnicas de programación. Proyecto final del curso IFCD0112.
Practica con preguntas tipo test que se adaptan a tu nivel, mentores con chat en tiempo real,
chatbot con IA y cuestionarios a medida a partir de ofertas de trabajo.

El nombre PrepCards es provisional.


Contenido

1. Qué hace la aplicación
2. Tecnologías
3. Arquitectura
4. Instalación con Docker
5. Variables de entorno
6. Datos de ejemplo y usuarios de demostración
7. Pruebas
8. App móvil
9. Despliegue en un servidor
10. Seguridad y limitaciones
11. Estructura del repositorio
12. Autoría


1. Qué hace la aplicación

Estudiante
- Se registra como estudiante y practica por rondas de 20 preguntas. Cinco aciertos seguidos suben de nivel
  y tres fallos seguidos bajan. Hay cinco niveles: inicial, básico, intermedio, avanzado y experto.
- Elige el nivel de partida la primera vez. Después el nivel solo cambia respondiendo.
- Guarda preguntas, consulta sus estadísticas y la evolución de su nivel en cada tema.
- Pregunta dudas a un chatbot con IA en cada pregunta (10 mensajes al día y 30 a la semana).
- Crea sus propios cuestionarios subiendo un JSON con al menos 20 preguntas. Pueden ser privados o públicos.
  Para publicar uno, la IA lo verifica antes y solo se publica si todas las preguntas son correctas.
- Pega una oferta de trabajo y la IA extrae los requisitos. Se genera un cuestionario de 20 o 40 preguntas,
  se calcula la compatibilidad con la oferta (90% obligatorios y 10% valorables) y se recomiendan temas oficiales.
- Pide un mentor, chatea con él en tiempo real y decide con una casilla si puede ver sus estadísticas y respuestas.
- Modo noche, diseño adaptable a móvil y tablet, descarga de sus datos y borrado de cuenta.

Mentor
- Se registra como mentor con una descripción de 20 a 100 caracteres.
- Recibe solicitudes, las acepta o rechaza y puede marcarse como no disponible.
- Crea cuestionarios, envía temas privados a sus alumnos y ve las estadísticas de sus cuestionarios
  y de los alumnos que le han dado permiso.
- No practica temas ni hace cuestionarios de oferta.

Administrador
- Gestiona temas oficiales, usuarios y roles desde el admin de Django.


2. Tecnologías

Backend       Python 3.12, Django 5, Django REST Framework, SimpleJWT, drf-spectacular
Tiempo real   Django Channels y Daphne (ASGI)
Asíncrono     Celery con Celery Beat
Datos         PostgreSQL 16 y Redis 7
IA            API de Gemini (capa gratuita) o API de Claude
Web           React 18, Vite, React Router, Tailwind, Recharts
Móvil         React Native con Expo
DevOps        Docker Compose, Caddy, GitHub Actions
Tests         pytest, pytest-django, pytest-asyncio


3. Arquitectura

    Navegador (React) ----\
                           >---- Caddy ---- Django con Daphne (API REST y WebSocket)
    App móvil (Expo) -----/                        |
                                                   +---- PostgreSQL
                                                   +---- Redis ---- Celery worker ---- API de IA
                                                                    Celery beat

Aplicaciones de Django
- accounts. Registro, login, perfil, roles y recuperación de contraseña.
- quiz. Temas, preguntas, niveles, rondas, estadísticas, chatbot, importación y verificación.
- offers. Ofertas de trabajo, requisitos y cuestionarios a medida.
- mentoring. Solicitudes, chat por WebSocket, permisos y estadísticas de alumnos.

Redis se usa como broker de Celery, para los canales del chat, para la caché de estadísticas
y para limitar peticiones en los endpoints de autenticación.


4. Instalación con Docker

Solo hace falta Docker Desktop y Git.

    git clone https://github.com/anniakuz/NOMBRE-DEL-REPOSITORIO.git
    cd NOMBRE-DEL-REPOSITORIO
    cp .env.example .env
    docker compose up --build

Direcciones
- Web       http://localhost:5173
- API       http://localhost:8000/api/
- Swagger   http://localhost:8000/api/docs/
- Admin     http://localhost:8000/admin/

Parar con docker compose down. Borrar también los datos con docker compose down -v.


5. Variables de entorno

Se copian de .env.example a .env. El archivo .env no se sube al repositorio.

DJANGO_SECRET_KEY        clave secreta de Django
DJANGO_DEBUG             1 en desarrollo, 0 en producción
DJANGO_ALLOWED_HOSTS     dominios permitidos separados por comas
POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
DEMO_PASSWORD            contraseña de los usuarios de demostración
AI_PROVIDER              gemini o anthropic
GEMINI_API_KEY           clave de la API de Gemini
GEMINI_MODEL             modelo de Gemini
ANTHROPIC_API_KEY        clave de la API de Claude, alternativa a Gemini
CHATBOT_DAILY_LIMIT      mensajes al día por usuario
CHATBOT_WEEKLY_LIMIT     mensajes a la semana por usuario

Sin una clave de IA no funcionan el chatbot, las ofertas ni la publicación de cuestionarios.
La clave de Gemini se consigue gratis en Google AI Studio.


6. Datos de ejemplo y usuarios de demostración

Al arrancar se aplican las migraciones y se cargan las preguntas oficiales desde backend/quiz/seed/topics.

    docker compose exec backend python manage.py seed_demo
    docker compose exec backend python manage.py createsuperuser

Con seed_demo se crean estos usuarios con la contraseña de DEMO_PASSWORD

admin, estudiante, mentor, laura_java, david_react, sofia_cloud, carlos_python, nuria_junior

Para añadir preguntas a un tema oficial, edita backend/quiz/seed/topics/<tema>.json y ejecuta
docker compose exec backend python manage.py seed_questions. No duplica las existentes.


7. Pruebas

    docker compose exec backend pytest

Son 100 pruebas que cubren registro, niveles y rondas, estadísticas, importación de JSON, cuestionarios
públicos y privados, chatbot, mentoría, permisos, ofertas, tareas de Celery y chat por WebSocket.
La IA se simula en las pruebas. GitHub Actions las ejecuta en cada push.


8. App móvil

    cd mobile
    npm install
    npx expo start

Antes de arrancar, indica la dirección de la API.

    EXPO_PUBLIC_API_URL=http://192.168.1.50:8000/api

Escanea el código QR con la app Expo Go. El móvil y el ordenador deben estar en la misma wifi.
La app incluye práctica, estadísticas, chatbot y chat con el mentor.


9. Despliegue en un servidor

El archivo docker-compose.prod.yml arranca todo en una sola máquina con Caddy sirviendo la web.

    cp .env.prod.example .env
    docker compose -f docker-compose.prod.yml up -d --build

Hay guías paso a paso en DESPLIEGUE_GOOGLE.md, DESPLIEGUE_AWS.md y DESPLIEGUE_ORACLE.md.


10. Seguridad y limitaciones

Seguridad
- JWT con refresh y lista negra al cerrar sesión.
- Permisos por rol y por recurso en cada endpoint.
- Límite de peticiones en registro, login y recuperación de contraseña.
- El ORM evita la inyección SQL y React escapa el contenido.
- Las claves van en variables de entorno y nunca en el repositorio.
- El texto de las ofertas se trata como dato y no como instrucciones para la IA.

Limitaciones
- Las preguntas oficiales son 440 en 8 temas. Faltan JavaScript y Algoritmos.
- El límite gratuito de Gemini puede impedir verificar cuestionarios. Entonces el estado es No se pudo verificar.
- La app móvil no incluye registro, creación de temas ni ofertas.
- El token del WebSocket viaja en la URL.
- Los textos legales son una plantilla y hay que revisarlos antes de publicar la web.


11. Estructura del repositorio

    backend/             Django, API, Celery y tests
    frontend/            React con Vite y Tailwind
    mobile/              App React Native con Expo
    docker-compose.yml   Entorno de desarrollo
    docker-compose.prod.yml   Entorno de producción
    DESPLIEGUE_*.md      Guías de despliegue


12. Autoría

Proyecto realizado por anniakuz. https://github.com/anniakuz
