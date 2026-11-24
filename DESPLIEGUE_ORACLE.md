Despliegue de PrepCards gratis en Oracle Cloud

Esta guía usa Oracle Cloud Always Free, que ofrece una máquina virtual permanente sin coste. Se despliega todo con Docker Compose en una sola máquina, igual que en DESPLIEGUE_AWS.md. Cambia solo la creación de la máquina y la apertura de puertos.

Archivos que usa el despliegue
docker-compose.prod.yml, frontend/Dockerfile.prod, frontend/Caddyfile, backend/entrypoint.prod.sh y .env.prod.example.

Antes de empezar
Necesitas una tarjeta de crédito o débito solo para verificar la cuenta. Mientras uses recursos Always Free no se cobra. Revisa que cada recurso que crees lleve la etiqueta Always Free Eligible.

1. Crear la cuenta
Entra en oracle.com/cloud/free y pulsa Start for free. Elige como región de origen una cercana, por ejemplo Madrid o Frankfurt. La región de origen no se puede cambiar después, y los recursos gratis solo se crean en ella.

2. Crear la máquina virtual
Menú, Compute, Instances, Create instance.
Nombre prepcards.
Imagen Canonical Ubuntu 24.04. Pulsa Change image si no es la que sale.
Forma. Pulsa Change shape, elige Ampere y VM.Standard.A1.Flex. Pon 2 OCPU y 12 GB de memoria, que sobra para el proyecto. Si no hay hueco, prueba con 1 OCPU y 6 GB.
Red. Deja la red virtual por defecto y marca Assign a public IPv4 address.
Claves SSH. Elige Generate a key pair for me y descarga la clave privada. Guárdala bien, no se puede descargar otra vez.
Volumen de arranque. 50 GB es suficiente.
Pulsa Create.

Si aparece el error Out of capacity para la forma Ampere, es normal. Prueba otra vez en otro momento del día, con menos OCPU o en otro dominio de disponibilidad si la región tiene varios.

3. Abrir los puertos 80 y 443 en Oracle
Instances, entra en tu máquina, abre la subred, abre la Security List por defecto y pulsa Add Ingress Rules. Crea dos reglas.
Source CIDR 0.0.0.0/0, protocolo TCP, puerto de destino 80.
Source CIDR 0.0.0.0/0, protocolo TCP, puerto de destino 443.
El puerto 22 ya viene abierto para SSH.

4. IP pública fija
La IP pública se mantiene mientras la máquina exista, pero si quieres que no cambie nunca, reserva una. Networking, IP management, Reserved public IPs, Reserve public IP address, y asóciala a tu máquina.

5. Conectar por SSH
Desde PowerShell, en la carpeta donde está la clave.
ssh -i ssh-key.key ubuntu@TU_IP_PUBLICA
Si Windows se queja de permisos de la clave, ábrela en Propiedades, Seguridad, Opciones avanzadas, y deja solo tu usuario con acceso.

6. Abrir los puertos en el firewall de Ubuntu
Las imágenes de Oracle traen reglas que bloquean todo menos SSH. Ejecuta en la máquina.
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo apt-get update
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save

7. Instalar Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
Cierra la sesión y vuelve a entrar. Todas las imágenes que usa el proyecto tienen versión para ARM, así que funciona sin cambios.

8. Subir el proyecto
Desde tu ordenador.
scp -i ssh-key.key prepcards.zip ubuntu@TU_IP_PUBLICA:~
En la máquina.
sudo apt-get install -y unzip
unzip prepcards.zip
cd interview-prep

9. Configurar el .env
cp .env.prod.example .env
nano .env
Rellena como mínimo DJANGO_SECRET_KEY, POSTGRES_PASSWORD, GEMINI_API_KEY y los datos de dominio. Para generar la clave secreta.
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
Nunca subas el .env a GitHub.

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
Caddy pide y renueva el certificado de Let's Encrypt automáticamente. El subdominio debe apuntar ya a la IP y los puertos 80 y 443 deben estar abiertos en Oracle y en Ubuntu.

10. Arrancar
docker compose -f docker-compose.prod.yml up -d --build
La primera vez tarda unos minutos. Para ver el estado y los registros.
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend

11. Crear el administrador
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
El panel está en /admin/ y la documentación de la API en /api/docs/.

Usuarios de demostración, opcional para la presentación
Pon DEMO_PASSWORD en el .env, reinicia con docker compose -f docker-compose.prod.yml up -d --force-recreate backend y ejecuta
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_demo
Bórralos después de la presentación.

12. Copias de seguridad
Oracle puede recuperar máquinas gratuitas casi sin uso y tú administras el servidor, así que haz copias de la base de datos.
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U prepcards prepcards > copia_$(date +%F).sql
Descárgala a tu ordenador con scp.
scp -i ssh-key.key ubuntu@TU_IP_PUBLICA:~/interview-prep/copia_2026-11-24.sql .

13. Actualizar la aplicación
Sube el zip nuevo, descomprímelo sobre la carpeta y ejecuta de nuevo
docker compose -f docker-compose.prod.yml up -d --build
Los datos se conservan en el volumen pgdata. No uses down -v en producción, borraría la base de datos.

14. Recomendaciones
Mantén el sistema al día con sudo apt-get update y sudo apt-get upgrade.
La clave de Gemini tiene un límite diario de uso. Mira el panel de AI Studio.
Si algo falla, mira primero docker compose -f docker-compose.prod.yml logs backend worker web.
