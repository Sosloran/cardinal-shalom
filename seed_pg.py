import os
from datetime import datetime, date

import pg8000
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from database import init_db, SessionLocal, User, Grade, Section, Subject, \
    LearningOutcome, Task, Book, Course, ChatbotKnowledge, Setting, \
    StudentScore, hash_password, today, now, _cache

USERS = [
    ("super_admin@cardinalshalom.edu.do", "Super Administrador", "super_admin", "approved", False),
    ("academic_admin@cardinalshalom.edu.do", "Admin Academico", "academic_admin", "approved", False),
    ("activity_admin@cardinalshalom.edu.do", "Admin de Actividades", "activity_admin", "approved", False),
    ("profesor@cardinalshalom.edu.do", "Profesor de Marketing Digital y Contabilidad", "teacher", "approved", True),
    ("estudiante@5to-a.cardinalshalom.edu.do", "Estudiante 5to A", "student", "approved", False),
]

GRADES = [
    ("5to de Secundaria", "5TO-SEC", "2026-2027", 1),
]

SECTIONS = [
    ("5to-A", 1, 40),
]

SUBJECTS_GLOBAL = [
    ("Matematicas", "MAT-5TO", "general", 1),
    ("Lengua Espanola", "LEN-5TO", "general", 1),
    ("Ciencias Sociales", "CISO-5TO", "general", 1),
    ("Ciencias de la Naturaleza", "CIEN-5TO", "general", 1),
    ("Educacion Fisica", "EFI-5TO", "general", 1),
    ("Ingles", "ING-5TO", "general", 1),
    ("Educacion Artistica", "ART-5TO", "general", 1),
    ("Formacion Integral Humana y Religiosa", "FIH-5TO", "general", 1),
]

SUBJECTS_TECHNICAL = [
    ("Marketing Digital", "MKT-DIG", "technical", 1),
    ("Contabilidad Basica", "CONT-BAS", "technical", 1),
    ("Tecnicas de Venta", "VTA-TEC", "technical", 1),
    ("Formacion y Orientacion Laboral (FOL)", "FOL-5TO", "technical", 1),
]

BOOKS = [
    ("Matematicas 5to - MINERD", "Matematicas", "https://covers.example/books/math5to.jpg", "https://minerd.gob.do/libros/matematicas5to.pdf"),
    ("Lengua Espanola 5to - MINERD", "Lengua Espanola", "https://covers.example/books/lang5to.jpg", "https://minerd.gob.do/libros/lengua5to.pdf"),
    ("Ciencias Sociales 5to - MINERD", "Ciencias Sociales", "https://covers.example/books/social5to.jpg", "https://minerd.gob.do/libros/cisociales5to.pdf"),
    ("Ciencias de la Naturaleza 5to - MINERD", "Ciencias de la Naturaleza", "https://covers.example/books/nature5to.jpg", "https://minerd.gob.do/libros/cinaturaleza5to.pdf"),
    ("Educacion Fisica 5to - MINERD", "Educacion Fisica", "https://covers.example/books/pe5to.jpg", "https://minerd.gob.do/libros/edufisica5to.pdf"),
    ("Ingles 5to - MINERD", "Ingles", "https://covers.example/books/ingles5to.jpg", "https://minerd.gob.do/libros/ingles5to.pdf"),
    ("Educacion Artistica 5to - MINERD", "Educacion Artistica", "https://covers.example/books/art5to.jpg", "https://minerd.gob.do/libros/educarte5to.pdf"),
    ("Formacion Integral Humana y Religiosa 5to - MINERD", "FIH", "https://covers.example/books/fih5to.jpg", "https://minerd.gob.do/libros/fih5to.pdf"),
    ("Marketing Digital - Modulo Tecnico", "Marketing Digital", "https://covers.example/books/mkt5to.jpg", "https://minerd.gob.do/libros/mktdigital5to.pdf"),
    ("Contabilidad Basica - Modulo Tecnico", "Contabilidad Basica", "https://covers.example/books/cont5to.jpg", "https://minerd.gob.do/libros/contabilidad5to.pdf"),
    ("Tecnicas de Venta - Modulo Tecnico", "Tecnicas de Venta", "https://covers.example/books/vta5to.jpg", "https://minerd.gob.do/libros/tecnicasVenta5to.pdf"),
    ("FOL - Modulo Tecnico", "Formacion y Orientacion Laboral", "https://covers.example/books/fol5to.jpg", "https://minerd.gob.do/libros/fol5to.pdf"),
]

COURSES = [
    ("Comercio y Marketing Digital", "Curso completo de comercio electronico y marketing digital para emprendedores.", "https://images.example/courses/mkt-digital.jpg", "youtube", "https://www.youtube.com/playlist?list=PL_mkt-digital-beta", 1, 6),
    ("Contabilidad Basica para Negocios", "Fundamentos de contabilidad: balances, estado de resultados, flujo de caja.", "https://images.example/courses/contabilidad.jpg", "youtube", "https://www.youtube.com/playlist?list=PL_contabilidad-beta", 1, 7),
    ("Uso de Canva para Proyectos Escolares", "Diseño grafico rapido con Canva: cuadernillos, presentaciones, redes sociales.", "https://images.example/courses/canva.jpg", "uploaded", "/static/courses/canva-intro.mp4", 1, None),
    ("Paquete Office: Word - Procesador de Texto", "Domina Word: formatos, estilos, tablas, imagenes, documentos academicos.", "https://images.example/courses/word.jpg", "youtube", "https://www.youtube.com/playlist?list=PL_office-word-beta", 1, None),
    ("Paquete Office: Excel - Hojas de Calculo", "Excel basico e intermedio: formulas, graficos, tablas dinamicas.", "https://images.example/courses/excel.jpg", "youtube", "https://www.youtube.com/playlist?list=PL_office-excel-beta", 1, None),
    ("Paquete Office: PowerPoint - Presentaciones", "Crea presentaciones impactantes para trabajos escolares y defensas.", "https://images.example/courses/ppt.jpg", "youtube", "https://www.youtube.com/playlist?list=PL_office-ppt-beta", 1, None),
]

CHATBOT_KNOWLEDGE = [
    ("libros", "Los libros de texto del MINERD estan en la seccion 'Biblioteca'. Elige tu grado (5to de Secundaria) y veras todos los libros organizados por materia.", "library", "library"),
    ("biblioteca", "Ve a 'Mi Biblioteca' en el menu del estudiante. Alli encuentras los libros del MINERD y los cursos practicos por grado.", "library", "library"),
    ("tarea", "Para entregar una tarea, ve a 'Mis Tareas' en tu panel de estudiante. Selecciona la tarea pendiente y presiona 'Entregar ahora'.", "tasks", "tasks"),
    ("entregar", "Puedes entregar una tarea escribiendo tu respuesta, subiendo un archivo (PDF o imagen), o compartiendo un link de YouTube o Google Drive.", "tasks", "tasks"),
    ("ranking", "Tu ranking lo ves en 'Ranking / Top Competitivo'. Puedes ver el general por grado o filtrar por materia individual.", "ranking", "ranking"),
    ("notas", "Tus calificaciones en tiempo real estan en 'Mis Notas'. Cada vez que un profesor califica una tarea, tu nota se actualiza automaticamente.", "grades", "grades"),
    ("portafolio", "Tu portafolio se construye automaticamente cada vez que entregas una tarea. Tambien puedes subir evidencias extra manualmente desde 'Mi Portafolio'.", "portfolio", "portfolio"),
    ("ra", "Un RA (Resultado de Aprendizaje) es un objetivo de aprendizaje con fecha de inicio y fin. Cada tarea pertenece a un RA. Cuando entregas, eso queda registrado en tu portafolio para ese RA.", "portfolio", "portfolio"),
    ("renovar", "Al finalizar el ano escolar, puedes solicitar la renovacion de grado desde 'Solicitar Renovacion de Grado'. El administrador academico revisa y aprueba.", "renewal", "renewal"),
    ("completivo", "Si un profesor activa el 'Modo Completivo' para ti, significara que tienes una oportunidad especial de recuperacion. Las tareas apareceran con este badge en tu panel.", "completivo", "completivo"),
    ("vacaciones", "Durante las vacaciones, el sistema entra en 'Modo Vacaciones / Retroalimentacion'. Puedes acceder a recursos de preparacion para el proximo ano en tu panel.", "vacations", "vacations"),
    ("como navegar", "Usa el menu lateral para navegar: Dashboard, Biblioteca, Mis Tareas, Mis Notas, Portafolio, Ranking. El chatbot asistente esta disponible en el boton azul abajo a la derecha.", "general", "navigation"),
    ("ayuda", "Puedo ayudarte con: navegacion por la plataforma, biblioteca de libros, entrega de tareas, ranking, portafolio, notas, renovacion de grado y modo completivo. Di que necesitas.", "general", "help"),
    ("salom", "Cardinal Shalom es una plataforma educativa integral para el Politecnico Comercio y Marketing Digital. Mejoramos el aprendizaje con herramientas digitales, portafolios automaticos y ranking en tiempo real.", "general", "about"),
]


def seed_postgres():
    """Run once. Idempotent: only inserts if DB is empty for key tables.
    Designed for PostgreSQL (Render)."""
    from database import _engine
    init_db()

    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Seed: DB ya tiene datos. Skip.")
            return

        print("Seed: insertando roles, grados, materias, libros, cursos...")

        # --- Users ---
        for email, name, role, status, is_teacher in USERS:
            u = User(
                email=email,
                password_hash=hash_password("Demo1234!"),
                full_name=name,
                role=role,
                status=status,
                is_teacher=is_teacher,
            )
            db.add(u)

        # --- Grades ---
        for name, code, year, seq in GRADES:
            g = Grade(name=name, code=code, school_year=year, seq=seq)
            db.add(g)

        db.flush()
        grade_5to = db.query(Grade).filter(Grade.code == "5TO-SEC").first()

        # --- Sections ---
        for name, grade_id, cap in SECTIONS:
            s = Section(grade_id=grade_5to.id, name=name, capacity=cap)
            db.add(s)

        db.flush()
        seccion_5to_a = db.query(Section).filter(Section.name == "5to-A").first()

        # --- Subjects ---
        db_subjects = {}
        for name, code, stype, grade_id in SUBJECTS_GLOBAL + SUBJECTS_TECHNICAL:
            s = Subject(name=name, code=code, type=stype, grade_id=grade_5to.id)
            db.add(s)
            db_subjects[code] = s

        db.flush()

        # --- Teacher assignment ---
        teacher = db.query(User).filter(User.role == "teacher").first()
        teacher.section_id = seccion_5to_a.id
        teacher.grade_id = grade_5to.id

        # crear RA ejemplo para Marketing Digital
        from datetime import timedelta
        ra_mkt = LearningOutcome(
            subject_id=db_subjects["MKT-DIG"].id,
            title="Calcula porcentajes de mercado y ROI en campanas digitales",
            description="El estudiante calcula el Retorno de Inversion (ROI) de una campana de marketing digital usando datos reales ficticios.",
            start_date=today(),
            end_date=today() + timedelta(days=60),
            duration_weeks=8,
            is_closed=False,
        )
        db.add(ra_mkt)
        db.flush()

        # crear tarea ejemplo
        due_dt = now() + timedelta(days=7, hours=23, minutes=59)
        task_demo = Task(
            ra_id=ra_mkt.id,
            teacher_id=teacher.id,
            title="Calcula el ROI de la campana 'Politecnico Digital 2026'",
            description="""<p>Analiza los siguientes datos y calcula el ROI:</p><ul><li>Inversion total: RD$ 50,000</li><li>Leads generados: 250</li><li>Leads convertidos: 40</li><li>Ingreso promedio por cliente: RD$ 3,000</li></ul><p>Entrega un informe breve con tu calculo y conclusiones.</p>""",
            due_date=due_dt,
            max_score=100,
            is_published=True,
        )
        db.add(task_demo)
        db.flush()

        # --- Books (MINERD) ---
        for title, subject_name, cover, file_url in BOOKS:
            b = Book(
                grade_id=grade_5to.id,
                title=title,
                subject=subject_name,
                cover_image_url=cover,
                file_url=file_url,
                is_active=True,
            )
            db.add(b)

        # --- Courses practicos ---
        for title, desc, thumb, ctype, url, grade_id, subject_id in COURSES:
            c = Course(
                title=title,
                description=desc,
                thumbnail_url=thumb,
                type=ctype,
                url=url,
                grade_id=grade_id,
                subject_id=subject_id,
                is_active=True,
            )
            db.add(c)

        # --- Chatbot knowledge ---
        for q, a, section, intent in CHATBOT_KNOWLEDGE:
            ck = ChatbotKnowledge(question=q, answer=a, section=section, intent=intent)
            db.add(ck)

        # --- Settings ---
        sys_mode = Setting(key="system_mode", value="normal")
        site_name = Setting(key="site_name", value="Cardinal Shalom")
        db.add(sys_mode)
        db.add(site_name)

        db.flush()

        # --- StudentScore (materialized view placeholder) ---
        student = db.query(User).filter(User.role == "student").first()
        sc = StudentScore(
            student_id=student.id,
            grade_id=grade_5to.id,
            overall_score=0.0,
            by_subject= "{}",
            updated_at=now(),
        )
        db.add(sc)

        db.commit()
        print("Seed: completado exitosamente (PostgreSQL).")
        print(f"  Usuarios creados: {len(USERS)}")
        print(f"  Grado creado: {GRADES[0][0]}")
        print(f"  Materias globales: {len(SUBJECTS_GLOBAL)}")
        print(f"  Materias tecnicas: {len(SUBJECTS_TECHNICAL)}")
        print(f"  Libros MINERD: {len(BOOKS)}")
        print(f"  Cursos practicos: {len(COURSES)}")

    except Exception as e:
        db.rollback()
        print(f"Seed ERROR: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_postgres()
