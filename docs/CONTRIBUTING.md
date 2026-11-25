# Guía de colaboración

## Flujo de trabajo

1. Tomar un issue de GitHub y asignárselo.
2. Crear una rama corta desde `main` con uno de estos prefijos:
   - `feat/` — nueva funcionalidad (`feat/study-endpoints`)
   - `fix/` — corrección de errores (`fix/missing-doppler-values`)
   - `docs/` — documentación (`docs/local-setup`)
3. Hacer commits pequeños siguiendo la convención de abajo.
4. Abrir un pull request hacia `main` que mencione el issue (`Closes #N`).
5. Fusionar solo con las pruebas en verde y al menos una revisión.

## Convención de commits

```text
feat: add study registration endpoint
fix: handle missing Doppler measurements
test: cover compression calculation
docs: update local setup
chore: update dependencies
```

## Reglas del proyecto

- Cada cambio que afecte los criterios de evaluación debe incluir pruebas y actualizar la documentación de la versión de reglas.
- No subir a Git estudios reales, imágenes de pacientes, nombres, expedientes, credenciales ni el archivo `.env`.
- Los datos de prueba deben ser sintéticos y guardarse en `backend/tests/fixtures/`.
- Un valor no medido se representa como `null`, nunca como `0`.

## Desarrollo local

Ver la sección *Instalación y ejecución* del [README](../README.md).
