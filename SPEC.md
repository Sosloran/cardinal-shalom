# Cardinal Shalom — Especificación Técnica y de Diseño
# v1.0 | Beta: 5to de Secundaria — Politécnico Comercio y Marketing Digital

## 1. IDENTIDAD VISUAL

### Paleta
| Role | Color | Hex |
|---|---|---|
| Azul principal | Navy | `#1e3a5f` |
| Azul secundario | Steel Blue | `#2d6da8` |
| Azul claro (fondos sección) | Powder | `#e8f0f8` |
| Blanco | — | `#ffffff` |
| Texto secundario | Slate | `#64748b` |
| Acento gamificación | Dorado | `#f5b342` |
| Éxito / aprobado | Verde | `#22c55e` |
| Alerta / riesgo | Naranja | `#f97316` |

### Tipografía
- **Heading:** `Outfit` (Google Fonts) — moderna, geometrica, escolar
- **Body/UI:** `Inter` (solo si Outfit no carga; fallback) — legible en tablas

### Animaciones de fondo (no distractivas)
- **Onda sutil:** SVG wave deformada por CSS animation, opacity 0.08, movimiento lento 8s ease-in-out alternate
- **Partículas:** Canvas de 30-50 dots blancos con opacity 0.15, movimiento brownian very-slow; se desactiva en `prefers-reduced-motion`
- Se aplican solo al hero del dashboard y al login — no en tablas ni formularios

### Componentes UI
- **Cards:** `border-radius: 16px`, sombra suave `box-shadow: 0 4px 24px rgba(30,58,95,0.08)` + border `1px solid rgba(30,58,95,0.06)`
- **Botones primarios:** azul navy `#1e3a5f` → hover `#2d6da8`, radius 10px, padding 12px 24px, transición 150ms
- **Tablas:** header con fondo `#e8f0f8`, rows alternados, hover row highlight
- **Badge de rol:** color según rol — Super Admin (violeta), Admin Académico (azul), Profesor (verde), Estudiante (gris)
- **Chatbot:** bubble flotante bottom-right, expande a panel lateral izquierdo

## 2. ARCHITECTURE

```
cardinal-shalom/
app.py                 # Single-file Flask app (routing + auth + API + views)
database.py            # SQLite + SQLAlchemy ORM models
seed.py                # Seed: roles, grados, materias beta, admin demo
requirements.txt
static/
│   ├── css/
│   │   └── style.css      # Animaciones onda/partículas + componentes UI
│   └── js/
│       ├── websocket.js  # Ranking live + chatbot
│       └── globals.js    # Tipos, utils, navbar state
├── templates/
│   ├── base.html          # Layout: navbar + footer + chatbot + CSS
│   ├── auth/
│   │   ├── login.html
│   │   └── register.html
│   ├── dashboard.html     # Dashboard genérico por rol
│   ├── admin/
│   │   ├── no_code.html           # CRUD grados/secciones/materias
│   │   └── approval.html          # Aprobación registros estudiantes
│   ├── academic/
│   │   ├── grades_overview.html   # Sistema global de calificaciones
│   │   └── ra_config.html         # Configuración RA por materia
│   ├── teacher/
│   │   ├── my_classes.html        # Secciones + materias del docente
│   │   ├── ra_detail.html         # RA → lista tareas + estudiantes entregados
│   │   ├── task_form.html         # Crear tarea con editor rich
│   │   ├── grade_student.html     # Calificar en tiempo real
│   │   ├── completivo_mode.html   # Activar Modo Completivo por alumno
│   │   └── library_manager.html   # Gestión biblioteca tutoriales
│   ├── student/
│   │   ├── my_grades.html         # Mis notas en tiempo real
│   │   ├── my_tasks.html          # Tareas pendientes + entregar
│   │   ├── submit_task.html       # Formulario entrega (file + text + image)
│   │   ├── portfolio.html         # Portafolio auto + evidencias manuales
│   │   ├── library.html           # Libros MINERD + cursos por grado
│   │   ├── ranking.html           # Ranking general / por materia
│   │   └── renewal_request.html   # Solicitar renovación de grado
│   └── shared/
│       └── chatbot_panel.html     # Panel del asistente virtual
└── uploads/               # Task submissions + portfolio evidences (gitignored)
```

## 3. SCHEMA — Ecto-style (fuente de verdad)

### Tablas principales

**users**
```
id            : integer, PK
email         : string, unique, indexed
password_hash : string
full_name     : string
role          : enum('super_admin','academic_admin','activity_admin','teacher','student')
status        : enum('pending','approved','suspended')
section_id    : ref sections (nullable — solo student/teacher)
grade_id      : ref grades (nullable — solo student)
created_at    : datetime
updated_at    : datetime
```

**grades** (grados)
```
id            : integer, PK
name          : string       (ej. "5to de Secundaria")
code          : string       (ej. "5TO-SEC")
school_year   : string        (ej. "2026-2027")
is_active     : boolean, default true
seq           : integer      (orden de visualización)
```

**sections** (secciones dentro de un grado)
```
id            : integer, PK
grade_id      : ref grades
name          : string       (ej. "A", "B", "C")
capacity      : integer, default 40
```

**subjects** (materias)
```
id            : integer, PK
name          : string       (ej. "Matemáticas", "Marketing Digital")
code          : string       (ej. "MAT-5TO", "MKT-DIG")
type          : enum('general','technical')
grade_id      : ref grades
is_active     : boolean, default true
```

**learning_outcomes (RAs)** — Resultados de Aprendizaje
```
id            : integer, PK
subject_id    : ref subjects
title         : string       (ej. "Calcula porcentajes en contextos comerciales")
description   : text
start_date    : date
end_date      : date
duration_weeks: integer
is_closed     : boolean, default false  (cierre manual/automático por docente)
closed_at     : datetime, nullable
```

**tasks**
```
id            : integer, PK
ra_id         : ref learning_outcomes
teacher_id    : ref users (profesor creador)
title         : string
description   : text (editor rich: HTML sanitizado)
due_date      : datetime
attachment_url: string, nullable  (adjunto del docente: instrucciones PDF imagen)
max_score     : integer, default 100
is_published  : boolean, default true
```

**submissions** (entregas de tareas)
```
id            : integer, PK
task_id       : ref tasks
student_id    : ref users
content_type  : enum('text','file','image','link')
content       : text         (HTML para text, URL para file/link, base64-data-url para image)
score         : integer, nullable  (calificación del docente)
score_comment : text, nullable
submitted_at  : datetime
graded_at     : datetime, nullable
is_late       : boolean, default false
```

**portfolio_evidences** (evidencias manuales del portafolio, aparte de entregas de tareas)
```
id            : integer, PK
student_id    : ref users
ra_id         : ref learning_outcomes (RA que evidencia)
title         : string
description   : text, nullable
file_url      : string       (ruta relativa a uploads/)
uploaded_at   : datetime
```

**activities** (noticias, circulares, eventos — Admin de Actividades)
```
id            : integer, PK
title         : string
body          : text (HTML)
category      : enum('news','circular','event','gallery')
image_url     : string, nullable
author_id     : ref users (activity_admin)
published_at  : datetime
is_active     : boolean, default true
```

**chatbot_knowledge** (base de conocimiento del chatbot asistente)
```
id            : integer, PK
question      : string       (keyword/trigger)
answer        : text (HTML)
section       : string       (ej. "library", "ranking", "portfolio", "tasks")
intent        : string
```

**grade_renewals** (solicitudes de renovación de grado)
```
id            : integer, PK
student_id    : ref users
current_grade_id : ref grades
requested_grade_id : ref grades
status        : enum('pending','approved','rejected')
requested_at  : datetime
reviewed_at   : datetime, nullable
comment       : text, nullable
```

## 4. RBAC — Permisos por rol

| Acción | Super Admin | Academic Admin | Activity Admin | Teacher | Student |
|---|---|---|---|---|---|
| CRUD grados/secciones/materias (no-code) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Activar/desactivar Modo Vacaciones global | ✅ | ❌ | ❌ | ❌ | ❌ |
| Aprobar registros estudiantes | ❌ | ✅ | ❌ | ❌ | ❌ |
| Aprobar renovaciones de grado | ❌ | ✅ | ❌ | ❌ | ❌ |
| Ver analíticas globales de calificaciones | ❌ | ✅ | ❌ | ❌ | ❌ |
| Publicar actividades/noticias/circulares | ❌ | ❌ | ✅ | ❌ | ❌ |
| Configurar duración RAs + cerrar RAs | ❌ | ❌ | ❌ | ✅ (por su materia) | ❌ |
| Crear tareas (editor rich + imágenes) | ❌ | ❌ | ❌ | ✅ | ❌ |
| Calificar entregas en tiempo real | ❌ | ❌ | ❌ | ✅ | ❌ |
| Activar Modo Completivo por alumno | ❌ | ❌ | ❌ | ✅ | ❌ |
| Gestionar biblioteca tutoriales | ❌ | ❌ | ❌ | ✅ | ❌ |
| Ver ranking (por grado/materia) | ✅ | ✅ | ✅ | ✅ (su sección) | ✅ (su grado) |
| Ver sus notas en tiempo real | ❌ | ❌ | ❌ | ❌ | ✅ |
| Entregar tareas | ❌ | ❌ | ❌ | ❌ | ✅ |
| Portafolio personal + evidencias manuales | ❌ | ❌ | ❌ | ❌ | ✅ |
| Solicitar renovación de grado | ❌ | ❌ | ❌ | ❌ | ✅ |
| Chatbot asistente (navegación + búsqueda biblioteca) | ✅ | ✅ | ✅ | ✅ | ✅ |

## 5. MODULOS — Flujo funcional

### 5A. Biblioteca de Libros y Cursos Prácticos
- Tabla `books` (libros MINERD): `grade_id, title, subject, file_url, cover_image_url, is_active`
- Tabla `courses` (cursos prácticos): `title, description, thumbnail_url, type (youtube|uploaded), url, grade_id, subject_id, is_active`
- Student view: selector de grado → lista libros + catálogo de cursos. Chatbot puede buscar por título/grado/materia.

### 5B. Asignaciones y Portafolio Auto por RA
- Flujo docente: Crear RA con fechas → Crear tarea dentro del RA → Student ve tarea en "Mis Tareas" → Entrega → Submission guardado → **Automático**: evidenica añadida al portafolio del student en el RA correspondiente
- Student puede subir evidencias extra manualmente desde `portfolio.html` → `portfolio_evidences`
- Portafolio = lista de RAs del student con todas las entregas + evidencias manuales agrupadas

### 5C. Gamificación — Ranking/Top en Tiempo Real
- Score global del student = promedio ponderado de todas las entregas calificadas (se calcula en memoria, se cachea en Redis-style en SQLite como `student_scores.cache` table que se actualiza al calificar)
- Tabla `student_scores` (materialized view-style): `student_id, grade_id, overall_score, updated_at`
- Ranking: LiveView-style con HTTP polling cada 10s o WebSocket
  - "Top Competitivo" por grado: leaderboard con animación de subida/bajada de posición
  - "Mejor Estudiante" del grado: badge dorado + spotlight
  - Filtro: General (todos los grados) / Por materia (score de esa materia solamente)

### 5D. Modos Especiales
**Modo Vacaciones / Retroalimentación (Super Admin)**
- Flag `system_mode` en tabla `settings`: `'normal' | 'vacations'`
- En modo vacations: las tareas regulares no se muestran como "pendientes" para student; se habilita vista "Vacaciones — Preparación" con recursos preparatorios para el próximo año

**Modo Completivo (Docente por alumno)**
- Flag en `users`: `completivo_mode: boolean, default false`
- Cuando un docente lo activa para un alumno: ese alumno puede entregar tareas de "recuperación" con deadline extendido, y el docente recibe notificación en su panel

## 6. API ENDPOINTS (Flask routes)

### Auth
- `GET /login` — login page
- `POST /login` — authenticate
- `POST /logout`
- `GET /register` — registro (student elige grado; sujeto a aprobación)
- `POST /register` — crear cuenta student + poner en `pending` para academic_admin aprobar

### Admin no-code
- `GET /admin/no-code` — panel CRUD
- `POST /grades`, `PUT /grades/<id>`, `DELETE /grades/<id>`
- mismo patrón para `sections`, `subjects`, `ra_config`

### RBAC-protected views (decorator `@role_required(roles)`)
- `GET /dashboard` — dashboard según role
- `GET /admin/approvals` — lista estudiantes pending
- `GET /admin/grade-renewals` — lista solicitudes de renovación
- `GET /academic/grades-overview` — calificaciones globales + analíticas
- `GET /teacher/my-classes` — secciones+materias del docente
- `GET /teacher/ra/<ra_id>` — detalle RA con estudiantes y entregas
- `POST /teacher/tasks` — crear tarea
- `POST /teacher/grade/<submission_id>` — calificar en tiempo real
- `POST /teacher/completivo/<student_id>/toggle` — activar/desactivar modo completivo
- `GET /student/my-grades` — notas en tiempo real
- `GET /student/my-tasks` — tareas pendientes
- `POST /student/submit/<task_id>` — entregar tarea
- `GET /student/portfolio` — portafolio
- `POST /student/portfolio/evidence` — evidencia manual
- `GET /student/library` — biblioteca
- `GET /student/ranking` — ranking (con filtro por materia)
- `POST /student/renewal-request` — solicitar renovación

### Library public (sin auth, para demo)
- `GET /library` — catálogo público de libros + cursos

### Chatbot
- `GET /chatbot` — panel del asistente
- `POST /chatbot/query` — query → responder con knowledge base + routing a secciones

### System mode
- `GET /settings/system-mode` — obtener modo actual
- `POST /settings/system-mode` — cambiar (solo super_admin)

## 7. FRONTEND — Pantallas clave

### Login + Register
- Login: email + password, con enlace "¿Eres nuevo? Regístrate"
- Register (student): nombre, email, password, selector de grado (carga dinámico desde `/api/grades`), checkbox de aceptación términos. Al submit → cuenta en `pending` hasta que academic_admin la apruebe. Email de bienvenida simulado (flash message).
- Si no eres student, registration está deshabilitada (solo admin crea cuentas desde no-code).

### Dashboard por rol
- **Super Admin:** métricas globales + botón "Modo Vacaciones" toggle + acceso rápido a no-code
- **Academic Admin:** contador de estudiantes pending + aprobaciones + analíticas de calificaciones + renovaciones pendientes
- **Activity Admin:** formulario nuevo + lista de actividades/publicaciones
- **Teacher:** lista de sus RAs activos con contador de entregas pendientes + "Crear Tarea" + "Gestionar Biblioteca"
- **Student:** "Mis Tareas" (pendientes vs entregadas con nota) + "Mi Portafolio" + "Biblioteca" + "Ranking" + "Mis Notas"

### Ranking / Top Competitivo
- Tabla interactiva sortable. Cabeza: "🏆 Mejor Estudiante" con avatar+nombre+nota+badge dorado, luego lista numérica.
- Filtro superior: selector "Grado" (default: grado del student logueado) + "Ver por materia" (dropdown de materias del grado, "General" default)
- Animación: al recargar, las filas que suben/bajan hacen transición suave de background (green→normal / orange→normal)

### Tareas — Entrega simplificada
- Vista student `my_tasks.html`: cards de tareas pendientes. Cada card: título, RA, due_date, botón "Entregar ahora"
- `submit_task.html`: editor de texto enriquecido (contenteditable con toolbar básico: negrita, itálica, lista, insertar imagen); upload de archivo (PDF, imagen); campo "link a YouTube/Google Drive". Submit → confirmation + auto-portafolio.

### Calificación en tiempo real (teacher)
- Vista `grade_student.html`: lista de submissions de un RA. Cada row: student name, submitted_at, content preview, score input (0-100), % acumulado automático. Al cambiar score → update in-place (AJAX) + recalculation del ranking. Sin page reload.

### Chatbot Asistente
- Bubble flotante bottom-right → panel lateral izquierdo deslizante (width 360px)
- Input de texto + buttons de "intentas rápidas": "¿Dónde están los libros?", "¿Cómo entrego una tarea?", "¿Cómo veo mi ranking?", "¿Qué es un RA?"
- Respuesta: texto + link a la sección correspondiente (si aplica)
- Knowledge base en tabla `chatbot_knowledge`; fallback: "No entendí, pero puedo ayudarte con: [navegación, biblioteca, tareas, ranking, portafolio]. Di qué necesitas."

### Modo Vacaciones UI
- Cuando `system_mode == 'vacations'`: en el sidebar del student aparece "📚 Preparación Vacaciones" en lugar de "Mis Tareas"; dentro, recursos por grado preparatorios para el próximo año

### Modo Completivo UI (student)
- Si un student tiene `completivo_mode == true`: en su panel de tareas, las tareas del RA aparecen con badge "Modo Completivo — Entrega especial de recuperación" y deadline extendido visible

## 8. SEED DATA — Beta 5to de Secundaria Politécnico Comercio y Marketing Digital

**Grados:**
- 5to de Secundaria (code: "5TO-SEC", school_year: "2026-2027", seq: 1)

**Secciones:**
- 5to-A

**Materias Generales (grade_id=5to):**
- Matemáticas (MAT-5TO, general)
- Lengua Española (LEN-5TO, general)
- Ciencias Sociales (CISO-5TO, general)
- Ciencias de la Naturaleza (CIEN-5TO, general)
- Educación Física (EFI-5TO, general)
- Inglés (ING-5TO, general)
- Educación Artística (ART-5TO, general)
- Formación Integral Humana y Religiosa (FIH-5TO, general)

**Módulos Técnicos (grade_id=5to, type=technical):**
- Marketing Digital (MKT-DIG, technical)
- Contabilidad Básica (CONT-BAS, technical)
- Técnicas de Venta (VTA-TEC, technical)
- Formación y Orientación Laboral — FOL (FOL-5TO, technical)

**Libros MINERD (5to):** 8 libros, uno por materia general + 4 técnicos (covers y file_urls placeholders que se pueden reemplazar con URLs reales luego)

**Cursos prácticos:**
- Comercio y Marketing Digital (YouTube playlist + subido local)
- Contabilidad Básica
- Uso de Canva
- Paquete Office: Word, Excel, PowerPoint

**Demostración de usuarios (seed):**
- super_admin@cardinalshalom.edu.do — Super Admin
- academic_admin@cardinalshalom.edu.do — Academic Admin
- activity_admin@cardinalshalom.edu.do — Activity Admin
- profesor@cardinalshalom.edu.do (asignado a Marketing Digital + Contabilidad) — Teacher
- estudiante@5to-a.cardinalshalom.edu.do — Student (5to-A, aprobado)

**Passwords:** todas `Demo1234!` (en producción se cambiarían)

## 9. SEGURIDAD Y VALIDACIÓN

- Passwords: hash con `werkzeug.security.generate_password_hash` (pbkdf2:sha256)
- Session: Flask session cookie + `@login_required` decorator
- RBAC: `@role_required(['teacher', 'super_admin'])` decorator
- HTML sanitization en submissions: strip de tags peligrosos (JS inline) con regex simple; en producción se usaría bleach
- CSRF básico: token en sesión para POST críticos (registro, calificación, configuración)
- Uploads: renaming de archivo a `uuid.ext` para evitar colisiones; MIME check básico

## 10. DESPLIEGUE

- Desarrollo: `python app.py` → `http://localhost:5000`
- Producción: `gunicorn app:app -b 0.0.0.0:5000` + nginx reverse proxy
- SQLite file-based → sin servidor externo; ideal para despliegue en Render/Railway/Heroku (usar DATABASE_URL env var si se migra a PostgreSQL luego)

---

*Documento generado como fuente de verdad para el desarrollo de Cardinal Shalom Beta.*
