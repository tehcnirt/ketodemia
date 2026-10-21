# Contrato de trabajo

Contrato breve derivado de Blueprint 2.0. El producto, su alcance, decisiones y pruebas están en `README.md` y en la documentación del repo; este archivo no los sustituye.

## Cómo trabajar

- Hacer lo que pide el propietario, sin ampliar alcance ni autorizaciones. Si una parte necesita decisión, preguntar y avanzar con lo independiente.
- Antes de editar, revisar `git status` y conservar cambios ajenos. Leer solo los documentos que afecten a la tarea.
- Trabajar con un solo agente. Un subagente de menor coste puede hacer búsquedas amplias o tareas mecánicas acotadas. Pedir permiso antes de usar un modelo o esfuerzo superior al actual.
- Al terminar, actualizar la documentación afectada y decir qué se hizo, cómo se comprobó y qué falta.
- Commits con prefijo `[claude]`, `[codex]` o `[manual]` y trailer `Origin: claude|codex|human`. `git add -- <rutas>` explícitas; nunca force-push ni `--no-verify`. Fusionar una PR solo con autorización explícita.
- Secretos y datos reales fuera de Git y de los logs.

## Blueprint

No consultar Blueprint al iniciar, retomar, publicar ni cerrar una tarea. Solo por encargo explícito de mantenimiento o para incorporar un recurso; entonces seguir `docs/operacion/actualizar-desde-blueprint.md`. La procedencia está en `docs/origen-blueprint.json`.
