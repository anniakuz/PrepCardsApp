Despliegue de PrepCards en AWS

Esta guía despliega todo el proyecto en una sola instancia EC2 con Docker Compose. Incluye la web, la API, el chat en tiempo real, Celery, PostgreSQL y Redis. Caddy sirve el frontend y pide el certificado HTTPS solo si tienes dominio.

Archivos que usa el despliegue
docker-compose.prod.yml, frontend/Dockerfile.prod, frontend/Caddyfile, backend/entrypoint.prod.sh y .env.prod.example.

1. Crear la instancia EC2
En la consola de AWS entra en EC2, Lanzar instancia.
Nombre prepcards. Sistema Ubuntu Server 24.04 LTS. Tipo t3.small (2 GB de RAM). Con t3.micro (1 GB) puede quedarse sin memoria.
Par de claves nuevo, tipo RSA, formato .pem. Guarda el archivo, no se puede descargar otra vez.
Almacenamiento 20 GB gp3.
Grupo de seguridad nuevo con estas reglas de entrada. SSH (22) solo desde Mi IP. HTTP (80) desde cualquier lugar. HTTPS (443) desde cualquier lugar.
Región recomendada eu-south-2 (España) o eu-west-1 (Irlanda).

2. IP fija
EC2, Direcciones IP elásticas, Asignar dirección, Asociar a tu instancia. Así la IP no cambia si reinicias.

3. Conectar por SSH
Desde PowerShell, en la carpeta donde está el .pem.
ssh -i prepcards.pem ubuntu@TU_IP_ELASTICA

4. Instalar Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
Cierra la sesión y vuelve a entrar para que se aplique el grupo.

Memoria extra de seguridad (recomendado)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

5. Subir el proyecto
Desde tu ordenador, en otra terminal.
scp -i prepcards.pem prepcards.zip ubuntu@TU_IP_ELASTICA:~
En el servidor.
sudo apt-get install -y unzip
unzip prepcards.zip
cd interview-prep

6. Configurar el .env
cp .env.prod.example .env
nano .env
Rellena como mínimo DJANGO_SECRET_KEY, POSTGRES_PASSWORD, GEMINI_API_KEY y los datos de dominio. Para generar la clave secreta.
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
Nunca subas el .env a GitHub.

Sin dominio, solo para probar
DJANGO_ALLOWED_HOSTS=TU_IP_ELASTICA
DJANGO_CSRF_TRUSTED_ORIGINS=http://TU_IP_ELASTICA
FRONTEND_URL=http://TU_IP_ELASTICA
DJANGO_HTTPS=0
SITE_ADDRESS=:80
Se sirve por HTTP, así que las contraseñas viajan sin cifrar. Úsalo solo para una prueba corta.

Con dominio, recomendado
Crea un registro A de tu dominio o subdominio que apunte a la IP elástica. Puedes usar Route 53, el proveedor de tu dominio o un subdominio gratis de duckdns.org. Después pon en el .env
DJANGO_ALLOWED_HOSTS=prepcards.midominio.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://prepcards.midominio.com
FRONTEND_URL=https://prepcards.midominio.com
DJANGO_HTTPS=1
SITE_ADDRESS=prepcards.midominio.com
Caddy pide y renueva el certificado de Let's Encrypt automáticamente. El DNS debe estar ya apuntando a la IP y los puertos 80 y 443 abiertos.

7. Arrancar
docker compose -f docker-compose.prod.yml up -d --build
La primera vez tarda unos minutos. Para ver el estado y los registros.
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
Al arrancar se aplican las migraciones y se cargan las preguntas oficiales.

8. Crear el administrador
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
El panel está en /admin/ y la documentación de la API en /api/docs/.

Usuarios de demostración (opcional, para la presentación)
En producción no se crean solos. Si los quieres, pon DEMO_PASSWORD en el .env, reinicia y ejecuta
docker compose -f docker-compose.prod.yml up -d --force-recreate backend
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_demo
Bórralos después de la presentación.

9. Comprobar
Abre la dirección en el navegador, regístrate, practica un tema, prueba el análisis de oferta y el chat con un mentor. Los WebSockets del chat funcionan a través de Caddy sin configuración extra.

10. Copias de seguridad
Copia manual de la base de datos.
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U prepcards prepcards > copia_$(date +%F).sql
Para guardarla en S3 crea un bucket, asigna a la instancia un rol IAM con permiso de escritura a ese bucket y usa aws s3 cp copia.sql s3://TU_BUCKET/.

11. Actualizar la aplicación
Sube el zip nuevo, descomprímelo sobre la carpeta y ejecuta de nuevo
docker compose -f docker-compose.prod.yml up -d --build
Los datos de PostgreSQL se conservan en el volumen pgdata. No uses down -v en producción, borraría la base de datos.

12. Costes y seguridad
Crea una alerta en AWS Budgets, por ejemplo 20 dólares al mes. Una t3.small encendida todo el mes cuesta del orden de 15 a 20 dólares. Si no la usas, paraliza la instancia desde la consola. Una IP elástica sin instancia asociada también se cobra.
La clave de Gemini tiene un límite diario de uso. Mira el panel de AI Studio y, si hace falta, activa la facturación con un tope de gasto.
Mantén el puerto 22 solo para tu IP y actualiza el sistema de vez en cuando con sudo apt-get update y sudo apt-get upgrade.

Mejoras futuras para explicar en la memoria
Base de datos gestionada con RDS, Redis con ElastiCache, imágenes en ECR y contenedores en ECS Fargate, balanceador ALB con HTTPS y certificado de ACM, y frontend en S3 con CloudFront. Para el chat con WebSockets, el balanceador necesita sesiones persistentes.
