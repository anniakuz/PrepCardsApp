Despliegue de PrepCards en Google Cloud con el crédito gratis

Esta guía usa el crédito de bienvenida de Google Cloud, 300 dólares durante 90 días para cuentas nuevas. Se despliega todo con Docker Compose en una sola máquina virtual, igual que en las otras guías. Cambia solo la creación de la máquina.

Archivos que usa el despliegue
docker-compose.prod.yml, frontend/Dockerfile.prod, frontend/Caddyfile, backend/entrypoint.prod.sh y .env.prod.example.

Antes de empezar
Necesitas una cuenta de Google y una tarjeta para verificar la identidad. Solo cuentas nuevas en Google Cloud pueden usar la prueba. No uses la máquina siempre gratis e2-micro, solo tiene 1 GB de RAM y no basta.
Al terminar los 90 días, si no pasas a una cuenta de pago, los recursos se borran. Haz copia de la base de datos antes.

1. Activar la prueba gratis
Entra en cloud.google.com/free y pulsa Empezar gratis. Inicia sesión con tu cuenta de Google, acepta las condiciones y añade la tarjeta. No se cobra nada mientras dure el crédito y no pases a cuenta de pago.
Cuando termine, entra en console.cloud.google.com. Se crea un proyecto llamado My First Project, puedes usarlo.

2. Activar Compute Engine
Menú de hamburguesa, Compute Engine, VM instances. La primera vez pide activar la API, pulsa Enable y espera un minuto.

3. Crear la máquina virtual
Pulsa Create instance.
Nombre prepcards.
Región europe-southwest1 (Madrid) o europe-west1 (Bélgica). Zona la que venga por defecto.
Tipo de máquina, pestaña General purpose, serie E2, e2-medium (2 vCPU y 4 GB de memoria).
Disco de arranque, pulsa Change. Sistema operativo Ubuntu, versión Ubuntu 24.04 LTS, tipo x86/64. Tamaño 30 GB. Pulsa Select.
Cortafuegos, marca Allow HTTP traffic y Allow HTTPS traffic.
Pulsa Create.

4. IP fija
Menú, VPC network, IP addresses. Busca la IP externa de tu máquina y en la columna Type cámbiala de Ephemeral a Static, ponle un nombre. Así no cambia si reinicias. Su coste pequeño sale del crédito.

5. Conectar sin claves
En la lista de VM instances pulsa el botón SSH de tu máquina. Se abre una terminal en el navegador. No necesitas claves ni PowerShell.

6. Instalar Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
Cierra la ventana SSH y vuelve a abrirla con el botón SSH para que se aplique el grupo.

Memoria extra de seguridad, recomendado
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

7. Subir el proyecto
En la ventana SSH pulsa el icono del engranaje arriba a la derecha, Upload file, y elige prepcards.zip. Se guarda en tu carpeta personal. Después.
sudo apt-get install -y unzip
unzip prepcards.zip
cd interview-prep

8. Configurar el .env
cp .env.prod.example .env
nano .env
Rellena como mínimo DJANGO_SECRET_KEY, POSTGRES_PASSWORD, GEMINI_API_KEY y los datos de dominio. Para generar la clave secreta.
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
Para guardar en nano pulsa Ctrl+O, Enter y Ctrl+X. Nunca subas el .env a GitHub.
Tu IP pública está en la columna External IP de VM instances.

Sin dominio, solo para probar
DJANGO_ALLOWED_HOSTS=TU_IP_PUBLICA
DJANGO_CSRF_TRUSTED_ORIGINS=http://TU_IP_PUBLICA
FRONTEND_URL=http://TU_IP_PUBLICA
DJANGO_HTTPS=0
SITE_ADDRESS=:80
Se sirve por HTTP, así que las contraseñas viajan sin cifrar. Úsalo solo para una prueba corta.

Con dominio gratis y HTTPS, recomendado
Entra en duckdns.org con tu cuenta de Google o GitHub, crea un subdominio, por ejemplo prepcards, y pon como IP la pública de tu máquina. Tendrás prepcards.duckdns.org. Después en el .env
DJANGO_ALLOWED_HOSTS=prepcards.duckdns.org
DJANGO_CSRF_TRUSTED_ORIGINS=https://prepcards.duckdns.org
FRONTEND_URL=https://prepcards.duckdns.org
DJANGO_HTTPS=1
SITE_ADDRESS=prepcards.duckdns.org
Caddy pide y renueva el certificado de Let's Encrypt automáticamente. El subdominio debe apuntar ya a la IP.

9. Arrancar
docker compose -f docker-compose.prod.yml up -d --build
La primera vez tarda unos minutos. Para ver el estado y los registros.
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
Al arrancar se aplican las migraciones y se cargan las preguntas oficiales.

10. Crear el administrador
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
El panel está en /admin/ y la documentación de la API en /api/docs/.

Usuarios de demostración, opcional para la presentación
Pon DEMO_PASSWORD en el .env, reinicia con docker compose -f docker-compose.prod.yml up -d --force-recreate backend y ejecuta
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_demo
Bórralos después de la presentación.

11. Control del gasto
Menú, Billing, Budgets & alerts, Create budget. Pon, por ejemplo, 20 dólares con avisos al 50% y al 90%. Mientras haya crédito no se cobra, pero la alerta te avisa de cualquier sorpresa.
Si no usas la máquina unos días, puedes pararla con el botón Stop en VM instances. Parada no consume crédito de cómputo, el disco y la IP sí consumen un poco.

12. Copias de seguridad
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U prepcards prepcards > copia_$(date +%F).sql
Para bajarla a tu ordenador, en la ventana SSH pulsa el engranaje, Download file, y escribe la ruta, por ejemplo interview-prep/copia_2026-11-24.sql.

13. Actualizar la aplicación
Sube el zip nuevo, descomprímelo sobre la carpeta y ejecuta de nuevo
docker compose -f docker-compose.prod.yml up -d --build
Los datos se conservan en el volumen pgdata. No uses down -v en producción, borraría la base de datos.

14. Al terminar el curso
Antes de que acabe la prueba haz la copia de seguridad. Después puedes borrar la máquina y la IP estática para no generar cobros si pasas a cuenta de pago.
La clave de Gemini tiene un límite diario de uso. Mira el panel de AI Studio.
Si algo falla, mira primero docker compose -f docker-compose.prod.yml logs backend worker web.
