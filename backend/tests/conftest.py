import os

# Permite ejecutar las pruebas fuera de Docker sin un .env: la API no se conecta a la
# base de datos al importarse. Dentro de Compose se respeta el DATABASE_URL existente.
os.environ.setdefault("DATABASE_URL", "sqlite://")
