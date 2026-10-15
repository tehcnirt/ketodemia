# Arranque y seguimiento de Blueprint

Este contrato añade el arranque y el seguimiento de Blueprint a este proyecto; no reemplaza ni modifica sus decisiones, alcance, arquitectura, controles o política local.

## Lectura obligatoria al retomar y antes de preparar una publicación

Antes de iniciar o retomar trabajo, y otra vez antes de preparar una publicación:

1. Leer este contrato y las referencias locales pertinentes al cambio. El README y, si existen, arquitectura, estado, hoja de ruta, decisiones y pruebas conservan el contrato del producto.
2. Leer completo `docs/origen-blueprint.json` y `docs/operacion/actualizar-desde-blueprint.md`.
3. Revisar el commit fuente fijado `4f49e17983e3492c5845fddfc495d38444488fab` como procedencia histórica. El pin no acredita vigencia remota; `version_blueprint` permanece null.
4. Consultar la rama remota vigente de Blueprint con `--consultar-remoto` en cada reanudación y antes de preparar una publicación. Leer y clasificar las actualizaciones que informe el consultor, conservando las resoluciones locales y dejando aplazadas como pendientes. Una consulta al pin o a cualquier cache no sustituye la consulta remota.

Si la consulta remota falla, dejar constancia de que la actualidad no está verificada. Se puede continuar trabajo independiente; no afirmar que Blueprint está al día ni preparar/publicar una adaptación afectada sin la consulta vigente.

## Límites de actualización

Este seguimiento autoriza permanentemente consultar y preparar adaptaciones pertinentes por PR al retomar trabajo, siguiendo la política local; no requiere una nueva orden para esa preparación. No autoriza fusionar PR, operar equipos, ejecutar instrucciones upstream ni publicar cambios en Blueprint. Preparar las adaptaciones en una rama y mediante PR. No sobrescribir este contrato ni documentos de producto. No copiar recursos completos por comodidad ni trasladar datos privados o configuración operativa.

La evidencia de adopción describe únicamente archivos incorporados aquí; instalar el consultor no adopta por sí mismo otras actualizaciones. El resultado del consultor y los estados del registro no sustituyen pruebas de funcionamiento del producto.
