---
ARCHITECTURE LAYERS — CANONICAL DOCTRINE

1. CAMADA IDE — Plano de Controle
- Cursor is the single control plane.
- All logic, structure, and evolution are defined here.
- Nothing exists unless it is versioned and explainable.

2. CAMADA IA — Assistência Cognitiva
- IA is a copilot, never an authority.
- IA may suggest, explain, review.
- IA never executes, triggers, or mutates state.

3. CAMADA ORQUESTRAÇÃO — Execução
- FastAPI and scripts execute deterministically.
- No reasoning or decision logic lives here.
- Execution does exactly what it is told.

4. CAMADA UI — Interação Humana
- UI triggers actions and displays results.
- UI contains no business logic.
- Shortcuts are buttons, not brains.

Anti-Patterns (Forbidden)
- Logic in Shortcuts
- AI executing commands
- Scripts deciding next steps
- Automations without logs
- Quick fixes outside Cursor

Escalation Rule
- Any automation that violates these layers is a bug, not a feature.
- It must be simplified, moved, or deleted.
---
