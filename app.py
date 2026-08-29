"""
Cardinal Shalom - Aplicación Flask principal.
Todo el routing, auth, RBAC, y vistas se encuentran aquí para la beta.
Para producción, se puede refactorizar a blueprints/modules.
"""
import os, uuid, json, logging
from datetime import datetime, timedelta

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, send_from_directory, abort,
)

from database import (
    init_db, get_db, User, Grade, Section, Subject, LearningOutcome,
    Task, Submission, PortfolioEvidence, Activity, Book, Course,
    ChatbotKnowledge, GradeRenewal, StudentScore, Setting,
    login_required, role_required, sanitize_html, now, today,
    _get_user, clear_user_cache, joinedload,
)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cardinal-shalom-beta-secret-2026")
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cardinal-shalom")

init_db()

# =================== Auto-seed de producción ===================
# Si la BD está vacía al iniciar (prime deploy con PostgreSQL), ejecutar seed automático.
from database import SessionLocal
db = SessionLocal()
try:
    has_users = db.query(User).count() > 0
finally:
    db.close()

if not has_users:
    logger.warning("BD vacía detectada — ejecutando seed de producción...")
    from seed import seed
    seed()

# =================== Auth ===================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not email or not password:
        flash("Completa email y contraseña.", "warning")
        return render_template("auth/login.html")

    db = next(get_db())
    user = db.query(User).filter(User.email == email).first()

    if not user or user.status != "approved":
        if user and user.status == "pending":
            flash("Tu cuenta está pendiente de aprobación por el administrador académico.", "info")
        else:
            flash("Email o contraseña incorrectos.", "danger")
        db.close()
        return render_template("auth/login.html")

    from database import check_password
    if not check_password(password, user.password_hash):
        flash("Email o contraseña incorrectos.", "danger")
        db.close()
        return render_template("auth/login.html")

    session["user_id"] = user.id
    session["role"] = user.role
    clear_user_cache(user.id)
    logger.info(f"Login: {user.email} ({user.role})")

    next_page = request.args.get("next") or url_for("dashboard")
    db.close()
    return redirect(next_page)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        db = next(get_db())
        grades = db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).all()
        db.close()
        return render_template("auth/register.html", grades=grades)

    if session.get("user_id"):
        flash("Ya iniciaste sesión.", "info")
        return redirect(url_for("dashboard"))

    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    grade_id = request.form.get("grade_id", type=int)
    accept_terms = request.form.get("accept_terms") == "on"

    if not all([full_name, email, password]):
        flash("Completa todos los campos.", "warning")
        return redirect(url_for("register"))

    if not accept_terms:
        flash("Debes aceptar los términos.", "warning")
        return redirect(url_for("register"))

    if len(password) < 6:
        flash("La contraseña debe tener al menos 6 caracteres.", "warning")
        return redirect(url_for("register"))

    db = next(get_db())
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        db.close()
        flash("Ese email ya está registrado.", "danger")
        return redirect(url_for("register"))

    grade = db.query(Grade).get(grade_id) if grade_id else None
    if not grade or not grade.is_active:
        db.close()
        flash("Grado no válido.", "danger")
        return redirect(url_for("register"))

    default_section = db.query(Section).filter(Section.grade_id == grade.id).first()

    from database import hash_password
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role="student",
        status="pending",
        grade_id=grade.id,
        section_id=default_section.id if default_section else None,
        is_teacher=False,
        completivo_mode=False,
    )
    db.add(user)
    db.commit()
    db.close()

    logger.info(f"Registro pendiente: {email} -> grade {grade.name}")
    flash(f"Registro exitoso! Tu cuenta '{email}' está pendiente de aprobación. Pronto podrás iniciar sesión.", "success")
    return redirect(url_for("login"))


@app.route("/logout")
@login_required
def logout():
    user_id = session.get("user_id")
    session.clear()
    if user_id:
        clear_user_cache(user_id)
    flash("Sesión terminada.", "info")
    return redirect(url_for("login"))


# =================== Dashboard ===================

@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    user = _get_user(session["user_id"])
    if not user:
        session.clear()
        flash("Sesión inválida.", "danger")
        return redirect(url_for("login"))

    db = next(get_db())

    sys_mode = db.query(Setting).filter(Setting.key == "system_mode").first()
    mode = sys_mode.value if sys_mode else "normal"

    data = {"user": user, "mode": mode}

    if user.role == "super_admin":
        total_students = db.query(User).filter(User.role == "student", User.status == "approved").count()
        total_pending = db.query(User).filter(User.role == "student", User.status == "pending").count()
        total_teachers = db.query(User).filter(User.role == "teacher", User.status == "approved").count()
        total_activities = db.query(Activity).filter(Activity.is_active).count()
        data.update({
            "total_students": total_students,
            "total_pending": total_pending,
            "total_teachers": total_teachers,
            "total_activities": total_activities,
        })

    elif user.role == "academic_admin":
        data["pending_students"] = db.query(User).filter(User.role == "student", User.status == "pending").count()
        data["pending_renewals"] = db.query(GradeRenewal).filter(GradeRenewal.status == "pending").count()
        data["total_students"] = db.query(User).filter(User.role == "student", User.status == "approved").count()

    elif user.role == "activity_admin":
        data["activities_count"] = db.query(Activity).filter(Activity.is_active).count()
        data["recent_activities"] = [
            a.to_dict() for a in db.query(Activity)
            .filter(Activity.is_active)
            .order_by(Activity.published_at.desc())
            .limit(5)
            .all()
        ]

    elif user.role == "teacher":
        teacher_sections = db.query(Section).filter(Section.id == user.section_id).all() if user.section_id else []
        teacher_grades = [s.grade for s in teacher_sections]
        teacher_subjects = db.query(Subject).filter(
            Subject.grade_id.in_([g.id for g in teacher_grades]),
            Subject.is_active,
        ).all() if teacher_grades else []

        teacher_subject_ids = [s.id for s in teacher_subjects]
        teacher_ras = db.query(LearningOutcome).filter(
            LearningOutcome.subject_id.in_(teacher_subject_ids),
            LearningOutcome.is_closed == False,
        ).all()
        data["teacher_sections"] = teacher_sections
        data["teacher_subjects"] = teacher_subjects
        data["teacher_ras"] = teacher_ras
        data["pending_submissions"] = db.query(Submission).join(Task).filter(
            Task.ra_id.in_([r.id for r in teacher_ras]),
            Task.teacher_id == user.id,
            Submission.score.is_(None),
        ).count()
        # grade para o template (primeira sección do docente)
        if teacher_sections:
            data["grade"] = teacher_sections[0].grade
        else:
            data["grade"] = None
        # tareas publicadas do docente
        data["tasks"] = (
            db.query(Task)
            .filter(Task.teacher_id == user.id, Task.is_published)
            .order_by(Task.due_date.asc())
            .limit(8)
            .all()
        )
    elif user.role == "student":
        user_grade = db.query(Grade).get(user.grade_id) if user.grade_id else None
        user_section = db.query(Section).get(user.section_id) if user.section_id else None
        data["my_grade_name"] = user_grade.name if user_grade else "Sin grado"
        data["my_section_name"] = user_section.name if user_section else "Sin sección"

        if mode == "vacations":
            data["vacations_mode"] = True
            data["prep_resources"] = _get_vacation_resources(db, user_grade)
        else:
            data["my_tasks"] = _get_student_tasks(db, user)
            data["my_grades_preview"] = _get_student_grades_preview(db, user)
            data["my_portfolio_stats"] = _get_portfolio_stats(db, user)
            data["pending_renewal"] = db.query(GradeRenewal).filter(
                GradeRenewal.student_id == user.id,
                GradeRenewal.status == "pending",
            ).first()

    db.close()
    return render_template("dashboard.html", **data)

def _get_student_tasks(db, user):
    """Tasks pending for a student, with submission status."""
    student_tasks = (
        db.query(Task)
        .join(LearningOutcome, LearningOutcome.id == Task.ra_id)
        .join(Subject, Subject.id == LearningOutcome.subject_id)
        .join(Grade, Grade.id == Subject.grade_id)
        .filter(
            Grade.id == user.grade_id,
            Task.is_published == True,
            Task.due_date > now(),
        )
        .order_by(Task.due_date.asc())
        .all()
    )

    result = []
    for task in student_tasks:
        submission = (
            db.query(Submission)
            .filter(Submission.task_id == task.id, Submission.student_id == user.id)
            .first()
        )
        due_date_str = task.due_date.strftime("%Y-%m-%dT%H:%M") if task.due_date else ""
        result.append({
            "task": task,
            "submission": submission.to_dict() if submission else None,
            "is_late": submission.is_late if submission else False,
            "completed": submission is not None and submission.score is not None,
            "graded": submission is not None and submission.score is not None,
            "score": submission.score if submission else None,
            "student_can_submit": not submission or submission.score is None or submission.score == 0,
            "due_date_str": due_date_str,
        })
    return result


def _get_student_grades_preview(db, user):
    submissions = (
        db.query(Submission)
        .join(Task, Task.id == Submission.task_id)
        .join(LearningOutcome, LearningOutcome.id == Task.ra_id)
        .join(Subject, Subject.id == LearningOutcome.subject_id)
        .filter(
            Submission.student_id == user.id,
            Submission.score.isnot(None),
        )
        .all()
    )

    by_subject = {}
    for sub in submissions:
        subj = sub.task.learning_outcome.subject
        key = subj.code
        if key not in by_subject:
            by_subject[key] = {"name": subj.name, "scores": [], "count": 0}
        by_subject[key]["scores"].append(sub.score)
        by_subject[key]["count"] += 1

    result = []
    for code, info in by_subject.items():
        avg = sum(info["scores"]) / len(info["scores"]) if info["scores"] else 0
        result.append({
            "subject_code": code,
            "subject_name": info["name"],
            "average": round(avg, 1),
            "count": info["count"],
        })
    result.sort(key=lambda x: x["average"], reverse=True)
    return result


def _get_portfolio_stats(db, user):
    ev_count = db.query(PortfolioEvidence).filter(PortfolioEvidence.student_id == user.id).count()
    sub_count = (
        db.query(Submission)
        .filter(Submission.student_id == user.id, Submission.score.isnot(None))
        .count()
    )
    ra_count = db.query(PortfolioEvidence).filter(
        PortfolioEvidence.student_id == user.id
    ).distinct(PortfolioEvidence.ra_id).count()
    return {"evidences": ev_count, "tasks_delivered": sub_count, "completed_ras": ra_count}


def _get_vacation_resources(db, grade):
    books = [b.to_dict() for b in db.query(Book).filter(Book.grade_id == grade.id, Book.is_active).all()]
    courses = [c.to_dict() for c in db.query(Course).filter(Course.grade_id == grade.id, Course.is_active).all()]
    return {"books": books, "courses": courses}


# =================== System Mode ===================

@app.route("/settings/system-mode", methods=["GET", "POST"])
@role_required(["super_admin"])
def system_mode():
    db = next(get_db())
    if request.method == "GET":
        setting = db.query(Setting).filter(Setting.key == "system_mode").first()
        return jsonify({"system_mode": setting.value if setting else "normal"})
    new_mode = request.form.get("system_mode", "normal")
    if new_mode not in ("normal", "vacations"):
        db.close()
        return jsonify({"error": "Modo inválido"}), 400
    setting = db.query(Setting).filter(Setting.key == "system_mode").first()
    if not setting:
        setting = Setting(key="system_mode", value=new_mode)
        db.add(setting)
    else:
        setting.value = new_mode
    db.commit()
    db.close()
    return jsonify({"system_mode": new_mode})


# =================== Admin: no-code CRUD ===================

@app.route("/admin/no-code")
@role_required(["super_admin"])
def admin_no_code():
    db = next(get_db())
    grades = db.query(Grade).order_by(Grade.seq).all()
    sections = db.query(Section).options(joinedload(Section.grade)).all()
    subjects = db.query(Subject).options(joinedload(Subject.grade)).all()
    grades_by_id = {g.id: g for g in grades}
    db.close()
    return render_template("admin/no_code.html",
                           grades=grades, sections=sections, subjects=subjects,
                           grades_by_id=grades_by_id)

@app.route("/admin/api/grades", methods=["POST"])
@role_required(["super_admin"])
def api_create_grade():
    db = next(get_db())
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    school_year = request.form.get("school_year", "").strip()
    seq = request.form.get("seq", type=int, default=0)
    if not name or not code or not school_year:
        db.close()
        return jsonify({"error": "Completa nombre, código y año escolar"}), 400
    g = Grade(name=name, code=code, school_year=school_year, seq=seq)
    db.add(g)
    db.commit()
    db.close()
    return jsonify({"id": g.id, "name": g.name, "code": g.code})


@app.route("/admin/api/grades/<int:grade_id>", methods=["PUT"])
@role_required(["super_admin"])
def api_update_grade(grade_id):
    db = next(get_db())
    g = db.query(Grade).get(grade_id)
    if not g:
        db.close()
        return jsonify({"error": "Grado no encontrado"}), 404
    g.name = request.form.get("name", g.name).strip()
    g.code = request.form.get("code", g.code).strip().upper()
    g.school_year = request.form.get("school_year", g.school_year).strip()
    g.seq = request.form.get("seq", g.seq, type=int)
    g.is_active = request.form.get("is_active") == "on"
    db.commit()
    db.close()
    return jsonify(g.to_dict())


@app.route("/admin/api/grades/<int:grade_id>", methods=["DELETE"])
@role_required(["super_admin"])
def api_delete_grade(grade_id):
    db = next(get_db())
    g = db.query(Grade).get(grade_id)
    if not g:
        db.close()
        return jsonify({"error": "Grado no encontrado"}), 404
    db.delete(g)
    db.commit()
    db.close()
    return jsonify({"deleted": True})


@app.route("/admin/api/sections", methods=["POST"])
@role_required(["super_admin"])
def api_create_section():
    db = next(get_db())
    grade_id = request.form.get("grade_id", type=int)
    name = request.form.get("name", "").strip().upper()
    capacity = request.form.get("capacity", 40, type=int)
    if not grade_id or not name:
        db.close()
        return jsonify({"error": "Completa grado y nombre de sección"}), 400
    grade = db.query(Grade).get(grade_id)
    if not grade:
        db.close()
        return jsonify({"error": "Grado no existe"}), 400
    s = Section(grade_id=grade_id, name=name, capacity=capacity)
    db.add(s)
    db.commit()
    db.close()
    return jsonify(s.to_dict())


@app.route("/admin/api/sections/<int:section_id>", methods=["PUT"])
@role_required(["super_admin"])
def api_update_section(section_id):
    db = next(get_db())
    s = db.query(Section).get(section_id)
    if not s:
        db.close()
        return jsonify({"error": "Sección no encontrada"}), 404
    s.name = request.form.get("name", s.name).strip().upper()
    s.capacity = request.form.get("capacity", s.capacity, type=int)
    db.commit()
    db.close()
    return jsonify(s.to_dict())


@app.route("/admin/api/sections/<int:section_id>", methods=["DELETE"])
@role_required(["super_admin"])
def api_delete_section(section_id):
    db = next(get_db())
    s = db.query(Section).get(section_id)
    if not s:
        db.close()
        return jsonify({"error": "Sección no encontrada"}), 404
    db.delete(s)
    db.commit()
    db.close()
    return jsonify({"deleted": True})


@app.route("/admin/api/subjects", methods=["POST"])
@role_required(["super_admin"])
def api_create_subject():
    db = next(get_db())
    name = request.form.get("name", "").strip()
    code = request.form.get("code", "").strip().upper()
    stype = request.form.get("type", "general")
    grade_id = request.form.get("grade_id", type=int)
    if not name or not code or not grade_id:
        db.close()
        return jsonify({"error": "Completa nombre, código, tipo y grado"}), 400
    grade = db.query(Grade).get(grade_id)
    if not grade:
        db.close()
        return jsonify({"error": "Grado no existe"}), 400
    s = Subject(name=name, code=code, type=stype, grade_id=grade_id)
    db.add(s)
    db.commit()
    db.close()
    return jsonify(s.to_dict())


@app.route("/admin/api/subjects/<int:subject_id>", methods=["PUT"])
@role_required(["super_admin"])
def api_update_subject(subject_id):
    db = next(get_db())
    s = db.query(Subject).get(subject_id)
    if not s:
        db.close()
        return jsonify({"error": "Materia no encontrada"}), 404
    s.name = request.form.get("name", s.name).strip()
    s.code = request.form.get("code", s.code).strip().upper()
    s.type = request.form.get("type", s.type)
    s.grade_id = request.form.get("grade_id", s.grade_id, type=int)
    s.is_active = request.form.get("is_active") == "on"
    db.commit()
    db.close()
    return jsonify(s.to_dict())


@app.route("/admin/api/subjects/<int:subject_id>", methods=["DELETE"])
@role_required(["super_admin"])
def api_delete_subject(subject_id):
    db = next(get_db())
    s = db.query(Subject).get(subject_id)
    if not s:
        db.close()
        return jsonify({"error": "Materia no encontrada"}), 404
    db.delete(s)
    db.commit()
    db.close()
    return jsonify({"deleted": True})


# =================== Admin: approvals ===================

@app.route("/admin/approvals")
@role_required(["academic_admin"])
def admin_approvals():
    db = next(get_db())
    pending = (
        db.query(User)
        .filter(User.role == "student", User.status == "pending")
        .order_by(User.created_at.desc())
        .all()
    )
    grades = db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).all()
    sections = db.query(Section).all()
    db.close()
    return render_template("admin/approval.html", pending=pending, grades=grades, sections=sections)


@app.route("/admin/approve/<int:user_id>", methods=["POST"])
@role_required(["academic_admin"])
def admin_approve_student(user_id):
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user or user.role != "student":
        db.close()
        flash("Usuario no válido.", "danger")
        return redirect(url_for("admin_approvals"))

    user.status = "approved"

    # === CORRECCIÓN: asignar grado si falta ===
    if not user.grade_id:
        # intentar obtener del registro (si tiene section_id, usar su grade)
        if user.section_id:
            sec = db.query(Section).filter(Section.id == user.section_id).first()
            if sec:
                user.grade_id = sec.grade_id
        # fallback: primer grado activo
        if not user.grade_id:
            g = db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).first()
            if g:
                user.grade_id = g.id

    # asignar sección por defecto si falta
    if not user.section_id:
        sec = db.query(Section).filter(Section.grade_id == user.grade_id).first()
        if sec:
            user.section_id = sec.id

    # crear o actualizar StudentScore
    sc = db.query(StudentScore).filter(StudentScore.student_id == user.id).first()
    if not sc:
        sc = StudentScore(
            student_id=user.id,
            grade_id=user.grade_id or 1,
            overall_score=0.0,
            by_subject=json.dumps({}),
        )
        db.add(sc)
    db.commit()
    db.close()
    clear_user_cache(user_id)
    flash(f"Estudiante '{user.full_name}' aprobado.", "success")
    return redirect(url_for("admin_approvals"))


@app.route("/admin/reject/<int:user_id>", methods=["POST"])
@role_required(["academic_admin"])
def admin_reject_student(user_id):
    db = next(get_db())
    user = db.query(User).get(user_id)
    if not user or user.role != "student":
        db.close()
        return redirect(url_for("admin_approvals"))
    db.delete(user)
    db.commit()
    db.close()
    flash(f"Cuenta de '{user.full_name}' rechazada y eliminada.", "info")
    return redirect(url_for("admin_approvals"))


# =================== Admin: grade renewals ===================

@app.route("/admin/grade-renewals")
@role_required(["academic_admin"])
def admin_grade_renewals():
    db = next(get_db())
    renewals = (
        db.query(GradeRenewal)
        .filter(GradeRenewal.status == "pending")
        .order_by(GradeRenewal.requested_at.desc())
        .all()
    )
    students = {u.id: u for u in db.query(User).filter(User.role == "student", User.status == "approved").all()}
    grades = {g.id: g for g in db.query(Grade).filter(Grade.is_active).all()}
    data = []
    for r in renewals:
        data.append({
            "id": r.id,
            "student_name": students.get(r.student_id, {}).get("full_name", "Desconocido"),
            "student_id": r.student_id,
            "current_grade": grades.get(r.current_grade_id, {}).get("name", "N/A"),
            "requested_grade": grades.get(r.requested_grade_id, {}).get("name", "N/A"),
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "current_grade_id": r.current_grade_id,
            "requested_grade_id": r.requested_grade_id,
        })
    db.close()
    return render_template("admin/grade_renewals.html", renewals=data)


@app.route("/admin/renew/<int:renewal_id>/approve", methods=["POST"])
@role_required(["academic_admin"])
def admin_approve_renewal(renewal_id):
    db = next(get_db())
    renewal = db.query(GradeRenewal).get(renewal_id)
    if not renewal:
        db.close()
        abort(404)
    renewal.status = "approved"
    renewal.reviewed_at = now()
    student = db.query(User).get(renewal.student_id)
    if student:
        student.grade_id = renewal.requested_grade_id
        new_section = db.query(Section).filter(Section.grade_id == renewal.requested_grade_id).first()
        if new_section:
            student.section_id = new_section.id
    db.commit()
    db.close()
    clear_user_cache(renewal.student_id)
    flash("Renovación de grado aprobada.", "success")
    return redirect(url_for("admin_grade_renewals"))


@app.route("/admin/renew/<int:renewal_id>/reject", methods=["POST"])
@role_required(["academic_admin"])
def admin_reject_renewal(renewal_id):
    db = next(get_db())
    renewal = db.query(GradeRenewal).get(renewal_id)
    if not renewal:
        db.close()
        abort(404)
    renewal.status = "rejected"
    renewal.reviewed_at = now()
    renewal.comment = "Rechazada por administrador académico."
    db.commit()
    db.close()
    flash("Renovación de grado rechazada.", "info")
    return redirect(url_for("admin_grade_renewals"))


# =================== Academic Admin: grades overview ===================

@app.route("/academic/grades-overview")
@role_required(["academic_admin"])
def academic_grades_overview():
    db = next(get_db())
    students = db.query(User).filter(User.role == "student", User.status == "approved").all()
    data = []
    for student in students:
        sc = db.query(StudentScore).filter(StudentScore.student_id == student.id).first()
        overall = sc.overall_score if sc else 0.0
        data.append({
            "id": student.id,
            "name": student.full_name,
            "email": student.email,
            "grade": student.grade.name if student.grade else "N/A",
            "section": student.section.name if student.section else "N/A",
            "overall": round(overall, 2),
            "completivo": student.completivo_mode,
        })
    data.sort(key=lambda x: x["overall"], reverse=True)
    db.close()
    return render_template("academic/grades_overview.html", students=data)


# =================== Activity Admin ===================

@app.route("/activity/admin")
@role_required(["activity_admin"])
def activity_admin():
    db = next(get_db())
    activities = (
        db.query(Activity)
        .filter(Activity.is_active)
        .order_by(Activity.published_at.desc())
        .all()
    )
    db.close()
    return render_template("activity/admin.html", activities=activities)


@app.route("/activity/new", methods=["GET", "POST"])
@role_required(["activity_admin"])
def activity_new():
    if request.method == "GET":
        return render_template("activity/new.html")

    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    category = request.form.get("category", "news")
    image_url = request.form.get("image_url", "").strip()

    if not title or not body:
        flash("Completa título y contenido.", "warning")
        return redirect(url_for("activity_new"))

    db = next(get_db())
    activity = Activity(
        title=title,
        body=sanitize_html(body),
        category=category,
        image_url=image_url if image_url else None,
        author_id=session["user_id"],
        is_active=True,
    )
    db.add(activity)
    db.commit()
    db.close()
    flash("Actividad publicada.", "success")
    return redirect(url_for("activity_admin"))


@app.route("/activity/delete/<int:activity_id>", methods=["POST"])
@role_required(["activity_admin"])
def activity_delete(activity_id):
    db = next(get_db())
    a = db.query(Activity).get(activity_id)
    if a:
        a.is_active = False
        db.commit()
    db.close()
    flash("Actividad eliminada.", "info")
    return redirect(url_for("activity_admin"))


# =================== Teacher: my classes ===================

@app.route("/teacher/my-classes")
@role_required(["teacher"])
def teacher_my_classes():
    user = _get_user(session["user_id"])
    if not user or not user.section_id:
        flash("No tienes sección asignada.", "warning")
        return redirect(url_for("dashboard"))

    db = next(get_db())
    section = db.query(Section).get(user.section_id)
    grade = section.grade if section else None
    
    # Pre-load subjects con sus relaciones
    subjects = (
        db.query(Subject)
        .options(joinedload(Subject.grade))
        .filter(Subject.grade_id == grade.id, Subject.is_active)
        .order_by(Subject.name)
        .all()
    ) if grade else []

    # Pre-cargar RAs con sus subjects
    teacher_subject_ids = [s.id for s in subjects]
    ras = (
        db.query(LearningOutcome)
        .options(joinedload(LearningOutcome.subject))
        .filter(LearningOutcome.subject_id.in_(teacher_subject_ids))
        .order_by(LearningOutcome.end_date.asc())
        .all()
    )

    # Tareas — sin lazy loading posterior
    task_list = (
        db.query(Task)
        .options(joinedload(Task.learning_outcome))
        .filter(Task.ra_id.in_([r.id for r in ras]), Task.is_published)
        .order_by(Task.due_date.asc())
        .all()
    )

    # Convertir a dicts serializados para evitar DetachedInstanceError en template
    ras_serialized = []
    for ra in ras:
        ra_dict = ra.to_dict()
        ra_dict["subject_name"] = ra.subject.name if ra.subject else "N/A"
        ra_dict["subject_type"] = ra.subject.type if ra.subject else "general"
        ra_dict["task_count"] = len(ra.tasks) if ra.tasks else 0
        ras_serialized.append(ra_dict)

    tasks_serialized = [t.to_dict() for t in task_list]
    db.close()
    return render_template("teacher/my_classes.html",
                           section=section, grade=grade, subjects=subjects,
                           ras=ras_serialized, tasks=tasks_serialized, user=user)


# =================== Teacher: RA detail ===================

@app.route("/teacher/ra/<int:ra_id>")
@role_required(["teacher"])
def teacher_ra_detail(ra_id):
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    ra = db.query(LearningOutcome).options(joinedload(LearningOutcome.subject)).get(ra_id)
    if not ra:
        db.close()
        abort(404)

    allowed = False
    if user.section_id:
        section = db.query(Section).get(user.section_id)
        if section and section.grade_id == ra.subject.grade_id:
            allowed = True
    if not allowed:
        db.close()
        flash("No tienes acceso a este RA.", "danger")
        return redirect(url_for("teacher_my_classes"))

    tasks = db.query(Task).filter(Task.ra_id == ra.id, Task.is_published).order_by(Task.due_date.asc()).all()
    students_in_section = (
        db.query(User)
        .filter(User.role == "student", User.status == "approved", User.section_id == user.section_id)
        .all()
    )

    task_data = []
    for t in tasks:
        submissions = (
            db.query(Submission)
            .options(joinedload(Submission.student))
            .filter(Submission.task_id == t.id, Submission.student_id.in_([s.id for s in students_in_section]))
            .all()
        )
        task_data.append({
            "task": t,
            "submissions": [s.to_dict() for s in submissions],
            "pending_count": sum(1 for s in submissions if s.score is None),
            "due_str": t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else "—",
        })

    db.close()
    return render_template("teacher/ra_detail.html", ra=ra, task_data=task_data, students=students_in_section, user=user)
    return render_template("teacher/ra_detail.html", ra=ra, task_data=task_data, students=students_in_section, user=user)


# =================== Teacher: create task ===================

@app.route("/teacher/task/new", methods=["GET", "POST"])
@role_required(["teacher"])
def teacher_task_new():
    if request.method == "GET":
        db = next(get_db())
        user = _get_user(session["user_id"])
        ras = []
        if user and user.section_id:
            section = db.query(Section).get(user.section_id)
            if section:
                ras = (
                    db.query(LearningOutcome)
                    .filter(LearningOutcome.subject_id.in_(
                        db.query(Subject.id).filter(Subject.grade_id == section.grade_id, Subject.is_active)
                    ))
                    .order_by(LearningOutcome.end_date.asc())
                    .all()
                )
        db.close()
        return render_template("teacher/task_form.html", ras=ras)

    ra_id = request.form.get("ra_id", type=int)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    due_date_str = request.form.get("due_date", "")
    max_score = request.form.get("max_score", 100, type=int)

    if not ra_id or not title or not description or not due_date_str:
        flash("Completa todos los campos de la tarea.", "warning")
        return redirect(url_for("teacher_task_new"))

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%dT%H:%M")
    except Exception:
        flash("Formato de fecha inválido.", "danger")
        return redirect(url_for("teacher_task_new"))

    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    ra = db.query(LearningOutcome).get(ra_id)
    if not ra or ra.subject.grade_id != (db.query(Section).get(user.section_id).grade_id if user.section_id else None):
        db.close()
        flash("RA no válido para tu sección.", "danger")
        return redirect(url_for("teacher_task_new"))

    task = Task(
        ra_id=ra_id,
        teacher_id=user.id,
        title=title,
        description=sanitize_html(description),
        due_date=due_date,
        max_score=max_score,
        is_published=True,
    )
    db.add(task)
    db.commit()
    db.close()
    flash(f"Tarea '{title}' publicada en el RA '{ra.title}'.", "success")
    return redirect(url_for("teacher_ra_detail", ra_id=ra_id))


# =================== Teacher: grade submission ===================

@app.route("/teacher/grade/<int:submission_id>", methods=["POST"])
@role_required(["teacher"])
def teacher_grade_submission(submission_id):
    user = _get_user(session["user_id"])
    if not user or not user.section_id:
        abort(403)

    db = next(get_db())
    submission = db.query(Submission).get(submission_id)
    if not submission:
        db.close()
        abort(404)

    task = db.query(Task).get(submission.task_id)
    if not task or task.teacher_id != user.id:
        db.close()
        flash("No puedes calificar esta entrega.", "danger")
        return redirect(url_for("dashboard"))

    score = request.form.get("score", type=int)
    score_comment = request.form.get("score_comment", "").strip()

    if score is None:
        flash("Completa la puntuación.", "warning")
        db.close()
        return redirect(url_for("teacher_ra_detail", ra_id=task.ra_id))

    if score < 0 or score > 100:
        flash("La puntuación debe estar entre 0 y 100.", "danger")
        db.close()
        return redirect(url_for("teacher_ra_detail", ra_id=task.ra_id))

    submission.score = score
    submission.score_comment = sanitize_html(score_comment) if score_comment else None
    submission.graded_at = now()

    _recalculate_student_score(db, submission.student_id, submission.task.learning_outcome.subject_id)

    db.commit()
    db.close()
    clear_user_cache(submission.student_id)
    flash(f"Entrega calificada: {score}/100 para {submission.student.full_name}.", "success")
    return redirect(url_for("teacher_ra_detail", ra_id=task.ra_id))


def _recalculate_student_score(db, student_id, subject_id=None):
    subs = (
        db.query(Submission)
        .filter(Submission.student_id == student_id, Submission.score.isnot(None))
        .all()
    )

    if not subs:
        sc = db.query(StudentScore).filter(StudentScore.student_id == student_id).first()
        if sc:
            sc.overall_score = 0.0
            sc.by_subject = json.dumps({})
            sc.updated_at = now()
        return

    total = 0.0
    count = 0
    by_subject = {}

    for sub in subs:
        subj = sub.task.learning_outcome.subject
        sid = subj.id
        if sid not in by_subject:
            by_subject[sid] = []
        by_subject[sid].append(sub.score)
        total += sub.score
        count += 1

    overall = total / count if count else 0.0
    by_subject_json = {str(k): round(sum(v) / len(v), 2) for k, v in by_subject.items()}

    sc = db.query(StudentScore).filter(StudentScore.student_id == student_id).first()
    if not sc:
        student = db.query(User).get(student_id)
        sc = StudentScore(
            student_id=student_id,
            grade_id=student.grade_id or 1,
            overall_score=overall,
            by_subject=json.dumps(by_subject_json),
        )
        db.add(sc)
    else:
        sc.overall_score = overall
        sc.by_subject = json.dumps(by_subject_json)
        sc.updated_at = now()

    db.flush()


# =================== Teacher: completivo mode ===================

@app.route("/teacher/completivo/<int:student_id>/toggle", methods=["POST"])
@role_required(["teacher"])
def teacher_toggle_completivo(student_id):
    user = _get_user(session["user_id"])
    if not user or not user.section_id:
        abort(403)

    db = next(get_db())
    student = db.query(User).get(student_id)
    if not student or student.role != "student":
        db.close()
        abort(404)

    section = db.query(Section).get(user.section_id)
    if section and student.section_id != user.section_id:
        db.close()
        flash("Solo puedes activar modo completivo para alumnos de tu sección.", "danger")
        return redirect(url_for("teacher_my_classes"))

    student.completivo_mode = not student.completivo_mode
    db.commit()
    db.close()
    clear_user_cache(student_id)

    status = "activado" if student.completivo_mode else "desactivado"
    flash(f"Modo Completivo {status} para {student.full_name}.", "success")
    return redirect(url_for("teacher_ra_detail", ra_id=1))


# =================== Teacher: library manager ===================

@app.route("/teacher/library-manager")
@role_required(["teacher"])
def teacher_library_manager():
    db = next(get_db())
    books = db.query(Book).options(joinedload(Book.grade)).filter(Book.is_active).all()
    courses = db.query(Course).options(joinedload(Course.grade)).filter(Course.is_active).all()
    grades = db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).all()
    grades_by_id = {g.id: g for g in grades}
    db.close()
    return render_template("teacher/library_manager.html", books=books, courses=courses, grades=grades, grades_by_id=grades_by_id)


@app.route("/teacher/library/book/new", methods=["POST"])
@role_required(["teacher"])
def teacher_library_book_new():
    db = next(get_db())
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    grade_id = request.form.get("grade_id", type=int)
    cover_url = request.form.get("cover_url", "").strip()
    file_url = request.form.get("file_url", "").strip()

    if not title:
        db.close()
        flash("Título requerido.", "warning")
        return redirect(url_for("teacher_library_manager"))

    b = Book(
        grade_id=grade_id or 1,
        title=title,
        subject=subject,
        cover_image_url=cover_url or None,
        file_url=file_url or None,
        is_active=True,
    )
    db.add(b)
    db.commit()
    db.close()
    flash("Libro agregado a la biblioteca.", "success")
    return redirect(url_for("teacher_library_manager"))


@app.route("/teacher/library/course/new", methods=["POST"])
@role_required(["teacher"])
def teacher_library_course_new():
    db = next(get_db())
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    thumbnail_url = request.form.get("thumbnail_url", "").strip()
    ctype = request.form.get("type", "youtube")
    url = request.form.get("url", "").strip()
    grade_id = request.form.get("grade_id", type=int)

    if not title or not url:
        db.close()
        flash("Título y URL requeridos.", "warning")
        return redirect(url_for("teacher_library_manager"))

    c = Course(
        title=title,
        description=description,
        thumbnail_url=thumbnail_url or None,
        type=ctype,
        url=url,
        grade_id=grade_id or 1,
        subject_id=None,
        is_active=True,
    )
    db.add(c)
    db.commit()
    db.close()
    flash("Curso agregado a la biblioteca.", "success")
    return redirect(url_for("teacher_library_manager"))


# =================== Student: my grades ===================

@app.route("/student/my-grades")
@role_required(["student"])
def student_my_grades():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    grades = _get_student_grades_preview(db, user)

    sc = db.query(StudentScore).filter(StudentScore.student_id == user.id).first()
    overall = sc.overall_score if sc else 0.0

    db.close()
    return render_template("student/my_grades.html", grades=grades, overall=overall, user=user)


# =================== Student: my tasks ===================

@app.route("/student/my-tasks")
@role_required(["student"])
def student_my_tasks():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    tasks = _get_student_tasks(db, user)
    db.close()
    return render_template("student/my_tasks.html", tasks=tasks, user=user)


# =================== Student: submit task ===================

@app.route("/student/submit/<int:task_id>", methods=["GET", "POST"])
@role_required(["student"])
def student_submit_task(task_id):
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    task = db.query(Task).get(task_id)
    if not task:
        db.close()
        abort(404)

    existing = (
        db.query(Submission)
        .filter(Submission.task_id == task_id, Submission.student_id == user.id)
        .first()
    )
    if existing and existing.score is not None:
        db.close()
        flash("Esta tarea ya fue calificada. Contacta a tu profesor para una entrega complementiva.", "info")
        return redirect(url_for("student_my_tasks"))

    if existing and existing.score is None:
        flash("Esta tarea ya fue enviada y está pendiente de calificación.", "info")
        return redirect(url_for("student_my_tasks"))

    db.close()

    if request.method == "GET":
        return render_template("student/submit_task.html", task=task)

    content_type = request.form.get("content_type", "text")
    content_text = request.form.get("content", "").strip()
    link_url = request.form.get("link_url", "").strip()

    attached_file = request.files.get("file")
    content = ""
    final_content_type = content_type

    if attached_file and attached_file.filename:
        filename = attached_file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".gif"):
            flash("Solo se permiten archivos PDF, JPG, PNG, GIF.", "danger")
            return redirect(url_for("student_submit_task", task_id=task_id))
        safe_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        attached_file.save(filepath)
        content = f"/uploads/{safe_name}"
        final_content_type = "file" if ext in (".pdf",) else "image"

    if content_type == "link":
        content = link_url if link_url else ""
        final_content_type = "link"

    if content_type == "text":
        content = sanitize_html(content_text)
        final_content_type = "text"

    if not content and content_type != "link":
        flash("Completa el contenido de la entrega.", "warning")
        return redirect(url_for("student_submit_task", task_id=task_id))

    db = next(get_db())

    is_late = now() > task.due_date
    submission = Submission(
        task_id=task_id,
        student_id=user.id,
        content_type=final_content_type,
        content=content,
        is_late=is_late,
    )
    db.add(submission)

    # AUTOMATIC: add to student's portfolio for the RA
    ra = db.query(LearningOutcome).get(task.ra_id)
    if ra:
        evidence = PortfolioEvidence(
            student_id=user.id,
            ra_id=ra.id,
            title=f"Entrega: {task.title}",
            description=f"Entrega automática de tarea '{task.title}'",
            file_url=content if final_content_type in ("file", "image") else "",
            uploaded_at=now(),
        )
        db.add(evidence)

    db.commit()
    db.close()
    clear_user_cache(user.id)

    flash("Tarea entregada con éxito! Se añadió automáticamente a tu portafolio.", "success")
    return redirect(url_for("student_my_tasks"))


# =================== Student: portfolio ===================

@app.route("/student/portfolio")
@role_required(["student"])
def student_portfolio():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    evidences = (
        db.query(PortfolioEvidence)
        .filter(PortfolioEvidence.student_id == user.id)
        .order_by(PortfolioEvidence.uploaded_at.desc())
        .all()
    )

    by_ra = {}
    for ev in evidences:
        ra = db.query(LearningOutcome).get(ev.ra_id)
        ra_title = ra.title if ra else f"RA #{ev.ra_id}"
        if ra_title not in by_ra:
            by_ra[ra_title] = []
        by_ra[ra_title].append(ev.to_dict())

    auto_subs = (
        db.query(Submission)
        .join(Task, Task.id == Submission.task_id)
        .join(LearningOutcome, LearningOutcome.id == Task.ra_id)
        .filter(Submission.student_id == user.id, Submission.score.isnot(None))
        .all()
    )
    auto_evidences = []
    for sub in auto_subs:
        ra = sub.task.learning_outcome
        auto_evidences.append({
            "title": f"Tarea calificada: {sub.task.title}",
            "ra_title": ra.title,
            "score": sub.score,
            "date": sub.graded_at.isoformat() if sub.graded_at else None,
            "content": sub.content,
            "content_type": sub.content_type,
        })

    db.close()
    return render_template("student/portfolio.html",
                           evidences=evidences, by_ra=by_ra,
                           auto_evidences=auto_evidences,
                           user=user)


@app.route("/student/portfolio/evidence", methods=["POST"])
@role_required(["student"])
def student_add_evidence():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    ra_id = request.form.get("ra_id", type=int)
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()

    if not ra_id or not title:
        flash("Completa RA y título de evidencia.", "warning")
        return redirect(url_for("student_portfolio"))

    attached_file = request.files.get("evidence_file")
    file_url = ""
    if attached_file and attached_file.filename:
        filename = attached_file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".doc", ".docx"):
            flash("Formato de archivo no permitido.", "danger")
            return redirect(url_for("student_portfolio"))
        safe_name = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
        attached_file.save(filepath)
        file_url = f"/uploads/{safe_name}"

    db = next(get_db())
    evidence = PortfolioEvidence(
        student_id=user.id,
        ra_id=ra_id,
        title=title,
        description=sanitize_html(description) if description else None,
        file_url=file_url or title,
        uploaded_at=now(),
    )
    db.add(evidence)
    db.commit()
    db.close()
    clear_user_cache(user.id)
    flash("Evidencia añadida al portafolio.", "success")
    return redirect(url_for("student_portfolio"))


# =================== Student: library ===================

@app.route("/student/library")
@role_required(["student"])
def student_library():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    grade_id = user.grade_id
    grade = db.query(Grade).get(grade_id) if grade_id else None
    books = [b.to_dict() for b in db.query(Book).filter(Book.grade_id == grade_id, Book.is_active).all()]
    courses = [c.to_dict() for c in db.query(Course).filter(Course.grade_id == grade_id, Course.is_active).all()]
    subjects = [s.to_dict() for s in db.query(Subject).filter(Subject.grade_id == grade_id, Subject.is_active).all()]
    all_grades = db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).all()
    db.close()
    return render_template("student/library.html",
                           books=books, courses=courses, subjects=subjects,
                           current_grade=grade, all_grades=all_grades,
                           user=user)


# =================== Student: ranking ===================

@app.route("/student/ranking")
@role_required(["student"])
def student_ranking():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    grade_id = request.args.get("grade_id", type=int) or user.grade_id or 1
    subject_id = request.args.get("subject_id", type=int) or None

    grade = db.query(Grade).get(grade_id)

    students_q = (
        db.query(User, StudentScore)
        .join(StudentScore, User.id == StudentScore.student_id)
        .filter(User.role == "student", User.status == "approved", StudentScore.grade_id == grade_id)
    )

    def get_score(score_record, subj_id):
        if not subj_id:
            return score_record.overall_score
        scores = json.loads(score_record.by_subject) if score_record.by_subject else {}
        return scores.get(str(subj_id), 0.0)

    ranking = []
    for user, score_record in students_q:
        score = get_score(score_record, subject_id)
        ranking.append({
            "id": user.id,
            "name": user.full_name,
            "email": user.email,
            "section": user.section.name if user.section else "N/A",
            "score": round(score, 2),
            "overall": round(score_record.overall_score, 2),
            "is_me": user.id == session["user_id"],
            "is_best": False,
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)

    if ranking:
        ranking[0]["is_best"] = True

    subjects = (
        db.query(Subject)
        .filter(Subject.grade_id == grade_id, Subject.is_active)
        .order_by(Subject.name)
        .all()
    ) if grade else []

    db.close()
    return render_template("student/ranking.html",
                           ranking=ranking, subjects=subjects,
                           grade=grade, current_grade_id=grade_id,
                           subject_id=subject_id, user=user)


# =================== Student: renewal request ===================

@app.route("/student/renewal-request", methods=["GET", "POST"])
@role_required(["student"])
def student_renewal_request():
    user = _get_user(session["user_id"])
    if not user:
        abort(403)

    db = next(get_db())
    grades = db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).all()
    my_grade = db.query(Grade).get(user.grade_id) if user.grade_id else None
    existing = (
        db.query(GradeRenewal)
        .filter(GradeRenewal.student_id == user.id, GradeRenewal.status == "pending")
        .first()
    )
    db.close()

    if request.method == "GET":
        return render_template("student/renewal_request.html",
                               user=user, grades=grades, existing=existing,
                               my_grade=my_grade)

    if existing:
        flash("Ya tienes una solicitud de renovación pendiente.", "info")
        return redirect(url_for("student_renewal_request"))

    requested_grade_id = request.form.get("requested_grade_id", type=int)
    if not requested_grade_id:
        flash("Selecciona el grado al que deseas renovar.", "warning")
        return redirect(url_for("student_renewal_request"))

    db = next(get_db())
    current_grade = db.query(Grade).get(user.grade_id) if user.grade_id else None
    requested_grade = db.query(Grade).get(requested_grade_id)

    if not current_grade or not requested_grade:
        db.close()
        flash("Grados inválidos.", "danger")
        return redirect(url_for("student_renewal_request"))

    if current_grade.id == requested_grade.id:
        flash("Ya estás en ese grado.", "info")
        return redirect(url_for("student_renewal_request"))

    renewal = GradeRenewal(
        student_id=user.id,
        current_grade_id=current_grade.id,
        requested_grade_id=requested_grade.id,
        status="pending",
        requested_at=now(),
    )
    db.add(renewal)
    db.commit()
    db.close()
    clear_user_cache(user.id)
    flash("Solicitud de renovación enviada. El administrador académico la revisará.", "success")
    return redirect(url_for("student_renewal_request"))


# =================== Shared: chatbot ===================

@app.route("/chatbot")
@login_required
def chatbot():
    return render_template("shared/chatbot_panel.html")


@app.route("/api/chatbot/query", methods=["POST"])
@login_required
def chatbot_query():
    query = request.form.get("query", "").strip().lower()
    if not query:
        return jsonify({"response": "Pregunta algo sobre la plataforma.", "actions": []})

    db = next(get_db())
    knowledge = db.query(ChatbotKnowledge).all()
    db.close()

    best_match = None
    best_score = 0
    for k in knowledge:
        words = k.question.lower().split()
        score = sum(1 for w in words if w in query)
        if score > best_score:
            best_score = score
            best_match = k

    if best_match and best_score > 0:
        return jsonify({
            "response": best_match.answer,
            "section": best_match.section,
            "actions": [
                {"label": "Ir a la sección", "url": url_for("library_public", _external=False)}
            ] if best_match.section else []
        })

    return jsonify({
        "response": "No estoy seguro de entender. Pero puedo ayudarte con: navegación por la plataforma, biblioteca de libros, tareas, ranking, portafolio, mis notas, renovación de grado, modo completivo y vacaciones. Di qué necesitas.",
        "actions": [
            {"label": "Biblioteca", "url": url_for("student_library", _external=False)},
            {"label": "Mis Tareas", "url": url_for("student_my_tasks", _external=False)},
            {"label": "Ranking", "url": url_for("student_ranking", _external=False)},
            {"label": "Portafolio", "url": url_for("student_portfolio", _external=False)},
        ]
    })


# =================== Static: library public ===================

@app.route("/library")
def library_public():
    db = next(get_db())
    books = [b.to_dict() for b in db.query(Book).filter(Book.is_active).all()]
    courses = [c.to_dict() for c in db.query(Course).filter(Course.is_active).all()]
    db.close()
    return render_template("shared/library_public.html", books=books, courses=courses)


# =================== Static file serving ===================

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# =================== API helpers ===================

@app.route("/api/grades")
@login_required
def api_grades():
    db = next(get_db())
    grades = [g.to_dict() for g in db.query(Grade).filter(Grade.is_active).order_by(Grade.seq).all()]
    db.close()
    return jsonify(grades=grades)


@app.route("/api/sections/<int:grade_id>")
@login_required
def api_sections(grade_id):
    db = next(get_db())
    sections = [s.to_dict() for s in db.query(Section).filter(Section.grade_id == grade_id).all()]
    db.close()
    return jsonify(sections=sections)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
