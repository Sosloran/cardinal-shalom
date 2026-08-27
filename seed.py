"""
Cardinal Shalom - Seed data for Beta 5to de Secundaria Politécnico.
Run once after init_db:  python seed.py
Passwords: todas 'Demo1234!' (cambiar en produccion).
"""
from datetime import timedelta
from database import (
    init_db, SessionLocal, User, Grade, Section, Subject,
    LearningOutcome, Task, Book, Course, ChatbotKnowledge, Setting,
    StudentScore, hash_password, today, now, _cache,
)
import json

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
    ("5-A", 1, 30),
]

SUBJECTS_GENERAL = [
    ("Matemáticas", "MAT", "general", 1),
    ("Lengua Española", "LEN", "general", 1),
    ("Ciencias Sociales", "CIE-SOC", "general", 1),
    ("Ciencias de la Naturaleza", "CIE-NAT", "general", 1),
    ("Educación Física", "ED-FIS", "general", 1),
    ("Inglés", "ING", "general", 1),
    ("Educación Artística", "ED-ART", "general", 1),
    ("Formación Integral Humana y Religiosa", "FIHR", "general", 1),
]

SUBJECTS_TECNICOS = [
    ("Marketing Digital", "MKT-DIG", "tecnico", 1),
    ("Contabilidad Básica", "CONT", "tecnico", 1),
    ("Técnicas de Venta", "VEN", "tecnico", 1),
    ("Formación y Orientación Laboral (FOL)", "FOL", "tecnico", 1),
]

BOOKS = [
    ("Matemáticas 5to", "Matemáticas", "https://example.com/mate5to.pdf", None, 1),
    ("Lengua Española 5to", "Lengua Española", "https://example.com/lengua5to.pdf", None, 1),
    ("Ciencias Sociales 5to", "Ciencias Sociales", "https://example.com/cs5to.pdf", None, 1),
    ("Ciencias Naturales 5to", "Ciencias Naturales", "https://example.com/cn5to.pdf", None, 1),
    ("Educación Física 5to", "Educación Física", "https://example.com/ef5to.pdf", None, 1),
    ("Inglés 5to", "Inglés", "https://example.com/ing5to.pdf", None, 1),
    ("Educación Artística 5to", "Educación Artística", "https://example.com/art5to.pdf", None, 1),
    ("FIHR 5to", "FIHR", "https://example.com/fihr5to.pdf", None, 1),
    ("Marketing Digital - Guía", "Marketing Digital", "https://example.com/mkt.pdf", None, 1),
    ("Contabilidad Básica - Apuntes", "Contabilidad", "https://example.com/cont.pdf", None, 1),
    ("Técnicas de Venta - Manual", "Técnicas de Venta", "https://example.com/ven.pdf", None, 1),
    ("FOL - Guía Laboral", "FOL", "https://example.com/fol.pdf", None, 1),
]

COURSES = [
    ("Introducción a Canva para Educación", "Aprende a diseñar materiales educativos y publicidad básica con Canva.", "https://example.com/canva-thumb.jpg", "video", "https://www.youtube.com/watch?v=example_canva", 1, None),
    ("Word para Estudiantes", "Uso avanzado de Word: estilos, índices, tablas y formatos académicos.", "https://example.com/word-thumb.jpg", "video", "https://www.youtube.com/watch?v=example_word", 1, 1),
    ("Excel Básico para Comercio", "Planillas, fórmulas simples, gráficos y reportes comerciales.", "https://example.com/excel-thumb.jpg", "video", "https://www.youtube.com/watch?v=example_excel", 1, 7),
    ("PowerPoint Efectivo", "Creación de presentaciones impactantes para proyectos escolares y ventas.", "https://example.com/ppt-thumb.jpg", "video", "https://www.youtube.com/watch?v=example_ppt", 1, None),
]

CHATBOT_KNOWLEDGE = [
    ("¿Dónde están los libros?", "En la sección 'Biblioteca' puedes ver los libros del MINERD organizados por grado.", "student", "biblioteca"),
    ("¿Cómo entrego una tarea?", "Ve a 'Mis Tareas', selecciona la tarea pendiente y presiona 'Entregar'. Puedes escribir texto o subir un archivo.", "student", "tareas"),
    ("¿Cómo veo mi ranking?", "En 'Ranking' encontrarás la tabla de posiciones de tu grado, filtrada por materia si lo deseas.", "student", "ranking"),
    ("¿Qué es un RA?", "Un Resultado de Aprendizaje (RA) es un objetivo de aprendizaje con un tiempo límite. Cada tarea se vincula a un RA y se guarda automáticamente en tu portafolio.", "student", "ra"),
    ("¿Cómo consultar mis notas?", "En 'Mis Notas' ves tus calificaciones en tiempo real. También puedes ver el promedio general en tu dashboard.", "student", "notas"),
    ("¿Qué es el Modo Completivo?", "Es un modo activado por tu profesor para alumnos en riesgo. Te permite entregar tareas de recuperación especiales.", "student", "modos"),
    ("¿Dónde veo las noticias del colegio?", "En la sección 'Actividades' encontrarás eventos, circulars e imágenes publicadas por el admin de actividades.", "student", "actividades"),
    ("¿Cómo solicitar renovación de grado?", "Al finalizar el año, ve a 'Renovar Grado' y selecciona el siguiente grado. El admin académico revisará tu solicitud.", "student", "renovacion"),
]

def seed():
    init_db()
    db = SessionLocal()
    try:
        # Roles
        for email, name, role, status, is_teacher in USERS:
            if db.query(User).filter(User.email == email).first():
                continue
            u = User(
                email=email,
                password_hash=hash_password("Demo1234!"),
                full_name=name,
                role=role,
                status=status,
                is_teacher=is_teacher,
                completivo_mode=False,
            )
            db.add(u)

        # Grados
        for name, code, school_year, seq in GRADES:
            if db.query(Grade).filter(Grade.code == code).first():
                continue
            g = Grade(name=name, code=code, school_year=school_year, seq=seq, is_active=True)
            db.add(g)

        # Secciones
        grade_5to = db.query(Grade).filter(Grade.code == "5TO-SEC").first()
        section = None
        for name, grade_id, capacity in SECTIONS:
            if db.query(Section).filter(Section.name == name).first():
                continue
            s = Section(name=name, grade_id=grade_id, capacity=capacity)
            db.add(s)
            section = s

        # Materias Generales
        for name, code, stype, grade_id in SUBJECTS_GENERAL:
            if db.query(Subject).filter(Subject.code == code).first():
                continue
            s = Subject(name=name, code=code, type=stype, grade_id=grade_id, is_active=True)
            db.add(s)

        # Materias Técnicas
        for name, code, stype, grade_id in SUBJECTS_TECNICOS:
            if db.query(Subject).filter(Subject.code == code).first():
                continue
            s = Subject(name=name, code=code, type=stype, grade_id=grade_id, is_active=True)
            db.add(s)

        # Libros
        section_5to = db.query(Section).filter(Section.name == "5-A").first()
        grade_5to_id = db.query(Grade).filter(Grade.code == "5TO-SEC").first().id
        for title, subject, url, cover, _ in BOOKS:
            if db.query(Book).filter(Book.title == title).first():
                continue
            b = Book(title=title, subject=subject, file_url=url, cover_image_url=cover, grade_id=grade_5to_id, is_active=True)
            db.add(b)

        # Cursos
        for title, desc, thumb, ctype, url, grade_id, subject_id in COURSES:
            if db.query(Course).filter(Course.title == title).first():
                continue
            c = Course(title=title, description=desc, thumbnail_url=thumb, type=ctype, url=url, grade_id=grade_id, subject_id=subject_id)
            c.section = section
            db.add(c)

        # Chatbot knowledge
        for q, a, section, category in CHATBOT_KNOWLEDGE:
            if db.query(ChatbotKnowledge).filter(ChatbotKnowledge.question == q).first():
                continue
            ck = ChatbotKnowledge(question=q, answer=a, section=section, category=category)
            db.add(ck)

        # Settings
        if not db.query(Setting).filter(Setting.key == "system_mode").first():
            db.add(Setting(key="system_mode", value="normal"))
        if not db.query(Setting).filter(Setting.key == "site_name").first():
            db.add(Setting(key="site_name", value="Cardinal Shalom"))

        # StudentScore placeholder
        student = db.query(User).filter(User.role == "student").first()
        if student:
            if not db.query(StudentScore).filter(StudentScore.student_id == student.id).first():
                sc = StudentScore(
                    student_id=student.id,
                    grade_id=grade_5to.id,
                    overall_score=0.0,
                    by_subject=json.dumps({}),
                    updated_at=now(),
                )
                db.add(sc)

        db.commit()
        print("Seed: completado exitosamente.")
        print(f"  Usuarios creados: {len(USERS)}")
        print(f"  Grado creado: {grade_5to.name}")
        print(f"  Materias globales: {len(SUBJECTS_GENERAL)}")
        print(f"  Materias tecnicas: {len(SUBJECTS_TECNICOS)}")
        print(f"  Libros MINERD: {len(BOOKS)}")
        print(f"  Cursos practicos: {len(COURSES)}")
    except Exception as e:
        db.rollback()
        print(f"Seed ERROR: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
