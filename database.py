"""
Cardinal Shalom — Database (SQLAlchemy 2.0, suporta SQLite + PostgreSQL).
Carga la URI desde DATABASE_URL env var. En dev (sin var) usa SQLite local.
"""
import os
import re
import json
from datetime import datetime, date
from functools import wraps

from flask import session, redirect, url_for, flash, request, current_app
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean,
    DateTime, Date, Float, ForeignKey, Enum, JSON, event,
    inspect,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, joinedload

# ============================================================
# Engine setup — soporta Render (PostgreSQL) y dev (SQLite)
# ============================================================
_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///cardinal_shalom.db")
if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql://", 1)

_engine = create_engine(
    _DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=(
        {"check_same_thread": False} if _DATABASE_URL.startswith("sqlite") else {}
    ),
)

if _DATABASE_URL.startswith("postgresql"):
    @event.listens_for(_engine, "before_cursor_execute")
    def set_search_path(dbapi_conn, cursor, statement, parameters, *args):
        cursor.execute("SET search_path TO public")

SessionLocal = sessionmaker(bind=_engine)
Base = declarative_base()

_cache = {}


def hash_password(plain):
    import hashlib
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def check_password(plain, hashed):
    return hash_password(plain) == hashed


def now():
    return datetime.utcnow()


def today():
    return now().date()


def _get_session_user_id():
    return session.get("user_id")


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Inicia sesión para continuar.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                flash("Inicia sesión para continuar.", "warning")
                return redirect(url_for("login"))
            expected_role = session.get("role")
            if expected_role not in roles:
                flash("No tienes permisos para esta acción.", "danger")
                return redirect(url_for("dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator


def sanitize_html(text):
    if not text:
        return ""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#39;")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _get_user(user_id):
    if user_id in _cache:
        return _cache[user_id]
    db = next(get_db())
    try:
        user = db.query(User).get(user_id)
        if user:
            _cache[user_id] = user
        return user
    finally:
        db.close()


def clear_user_cache(user_id):
    _cache.pop(user_id, None)


_db_stack = []


def get_db():
    sess = SessionLocal()
    _db_stack.append(sess)
    try:
        yield sess
    finally:
        sess.close()
        _db_stack.pop()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(64), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)
    section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    is_teacher = Column(Boolean, default=False)
    completivo_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    grade = relationship("Grade", back_populates="students", lazy="select")
    section = relationship("Section", back_populates="students", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "status": self.status,
            "grade_id": self.grade_id,
            "section_id": self.section_id,
            "is_teacher": self.is_teacher,
            "completivo_mode": self.completivo_mode,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    school_year = Column(String(20), nullable=False)
    seq = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

    students = relationship("User", back_populates="grade", lazy="select")
    sections = relationship("Section", back_populates="grade", lazy="select")
    subjects = relationship("Subject", back_populates="grade", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "school_year": self.school_year,
            "seq": self.seq,
            "is_active": self.is_active,
        }


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    name = Column(String(100), nullable=False)
    capacity = Column(Integer, default=40)

    grade = relationship("Grade", back_populates="sections", lazy="select")
    students = relationship("User", back_populates="section", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "grade_id": self.grade_id,
            "name": self.name,
            "capacity": self.capacity,
        }


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    type = Column(String(20), default="general")
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    is_active = Column(Boolean, default=True)

    grade = relationship("Grade", back_populates="subjects", lazy="select")
    learning_outcomes = relationship("LearningOutcome", back_populates="subject", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "type": self.type,
            "grade_id": self.grade_id,
            "is_active": self.is_active,
        }


class LearningOutcome(Base):
    __tablename__ = "learning_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_weeks = Column(Integer, default=4)
    is_closed = Column(Boolean, default=False)

    subject = relationship("Subject", back_populates="learning_outcomes", lazy="select")
    tasks = relationship("Task", back_populates="learning_outcome", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "subject_id": self.subject_id,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "duration_weeks": self.duration_weeks,
            "is_closed": self.is_closed,
        }


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ra_id = Column(Integer, ForeignKey("learning_outcomes.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False)
    max_score = Column(Float, default=100.0)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)

    learning_outcome = relationship("LearningOutcome", back_populates="tasks", lazy="select")
    teacher = relationship("User", lazy="select")
    submissions = relationship("Submission", back_populates="task", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "ra_id": self.ra_id,
            "teacher_id": self.teacher_id,
            "title": self.title,
            "description": self.description,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "due_date_str": self.due_date.strftime("%Y-%m-%d %H:%M") if self.due_date else None,
            "max_score": self.max_score,
            "is_published": self.is_published,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "learning_outcome_title": self.learning_outcome.title if self.learning_outcome else None,
            "learning_outcome_id": self.ra_id,
        }


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content_type = Column(String(20), default="text")
    content = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    score_comment = Column(Text, nullable=True)
    is_late = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=now)
    graded_at = Column(DateTime, nullable=True)

    task = relationship("Task", back_populates="submissions", lazy="select")
    student = relationship("User", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "student_id": self.student_id,
            "content_type": self.content_type,
            "content": self.content,
            "score": self.score,
            "score_comment": self.score_comment,
            "is_late": self.is_late,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submitted_at_str": self.submitted_at.strftime("%Y-%m-%d %H:%M") if self.submitted_at else None,
            "graded_at": self.graded_at.isoformat() if self.graded_at else None,
            "student_name": self.student.full_name if self.student else None,
            "student_full_name": self.student.full_name if self.student else None,
        }


class PortfolioEvidence(Base):
    __tablename__ = "portfolio_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ra_id = Column(Integer, ForeignKey("learning_outcomes.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String(500), nullable=True)
    uploaded_at = Column(DateTime, default=now)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "ra_id": self.ra_id,
            "title": self.title,
            "description": self.description,
            "file_url": self.file_url,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    category = Column(String(50), default="news")
    image_url = Column(String(500), nullable=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, default=now)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "category": self.category,
            "image_url": self.image_url,
            "author_id": self.author_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "is_active": self.is_active,
        }


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, autoincrement=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    title = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=True)
    cover_image_url = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)

    grade = relationship("Grade", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "grade_id": self.grade_id,
            "title": self.title,
            "subject": self.subject,
            "cover_image_url": self.cover_image_url,
            "file_url": self.file_url,
            "is_active": self.is_active,
            "grade_name": self.grade.name if self.grade else None,
        }


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    type = Column(String(20), default="youtube")
    url = Column(String(500), nullable=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    is_active = Column(Boolean, default=True)

    grade = relationship("Grade", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "thumbnail_url": self.thumbnail_url,
            "type": self.type,
            "url": self.url,
            "grade_id": self.grade_id,
            "is_active": self.is_active,
            "grade_name": self.grade.name if self.grade else None,
        }


class ChatbotKnowledge(Base):
    __tablename__ = "chatbot_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question = Column(String(255), nullable=False)
    answer = Column(Text, nullable=False)
    section = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)


class GradeRenewal(Base):
    __tablename__ = "grade_renewals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    requested_grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    status = Column(String(20), default="pending")
    comment = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=now)
    reviewed_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "current_grade_id": self.current_grade_id,
            "requested_grade_id": self.requested_grade_id,
            "status": self.status,
            "comment": self.comment,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
        }


class StudentScore(Base):
    __tablename__ = "student_scores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=False)
    overall_score = Column(Float, default=0.0)
    by_subject = Column(JSON, default=lambda: "{}")
    updated_at = Column(DateTime, default=now, onupdate=now)

    student = relationship("User", lazy="select")

    def to_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "grade_id": self.grade_id,
            "overall_score": self.overall_score,
            "by_subject": self.by_subject,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)


def init_db():
    """Inicializar la base de datos en el envío correcto según la URI configurada."""
    db_path = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "cardinal_shalom.db"))
    if _DATABASE_URL.startswith("sqlite"):
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
    Base.metadata.create_all(_engine)
    return True
