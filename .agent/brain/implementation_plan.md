# Frontend Migration Implementation Plan

## Goal Description
Migrate the remaining composables (`useAdministracion` and related "Titular" composables) to the Strawchemy architecture. This ensures the entire "Agentes" module uses the new pagination and filtering system.

## Proposed Changes

### [Migrate] useAdministracion
1.  **Verify Queries**: Check `src/modules/agentes/graphql/administracionQueries.strawchemy.js`.
2.  **Refactor Composable**: Rewrite `src/modules/agentes/composables/useAdministracion.js` to import `useAgenteBaseStrawchemy` and the verified queries.
    *   Implement `listarPorAmbito` and `listarPorLocalidad` using Strawchemy filters.
3.  **Cleanup**: Remove `src/modules/agentes/composables/useAdministracion.strawchemy.js` (the duplicate file).

### [Migrate] useAdministracionTitular (and subclasses)
1.  **Create Queries**: Create `src/modules/agentes/graphql/administracionTitularQueries.strawchemy.js`.
2.  **Refactor Composable**: Rewrite `src/modules/agentes/composables/useAdministracionTitular.js` to use `useAgenteBaseStrawchemy` (or similar pattern if it fits).
    *   The `useAgenteBaseStrawchemy` assumes top-level resources mostly, but can be adapted if Titulares are their own entity or nested. Assuming they are accessible via top-level `administracionTitulares` (or similar) query in the new schema.
    *   *Self-Correction*: If the backend treats Titulares as nested relations mainly, we might rely on the parent's query. However, standard pattern suggests a flat endpoint is often available or useful.

## Verification Plan
1.  **Code Review**: Ensure imports reference `.strawchemy.js` files and use `useAgenteBaseStrawchemy`.
2.  **Build Check**: Run `npm run lint` or check for build errors.
