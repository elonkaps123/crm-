from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from .db import Base
import datetime


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # связи
    students = relationship("Student", back_populates="teacher")
    groups = relationship("Group", back_populates="teacher")
    lessons = relationship("Lesson", back_populates="teacher")
    homeworks = relationship("Homework", back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True, nullable=True)
    name = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("Teacher", back_populates="students")
    groups = relationship("GroupStudent", back_populates="student")
    submissions = relationship("HomeworkSubmission", back_populates="student")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("Teacher", back_populates="groups")
    students = relationship("GroupStudent", back_populates="group")
    lessons = relationship("Lesson", back_populates="group")


class GroupStudent(Base):
    __tablename__ = "group_students"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.datetime.utcnow)

    group = relationship("Group", back_populates="students")
    student = relationship("Student", back_populates="groups")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=True)
    topic = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("Teacher", back_populates="lessons")
    group = relationship("Group", back_populates="lessons")
    student = relationship("Student")


class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    max_score = Column(Integer, nullable=True)
    grading_type = Column(String(20), default="points")
    saved_in_library = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    teacher = relationship("Teacher", back_populates="homeworks")
    assignments = relationship("HomeworkAssignment", back_populates="homework")


class HomeworkAssignment(Base):
    __tablename__ = "homework_assignments"

    id = Column(Integer, primary_key=True, index=True)
    homework_id = Column(Integer, ForeignKey("homeworks.id"), nullable=False)
    assigned_to_type = Column(String(10))  # student/group/multi
    assigned_to_id = Column(Integer, nullable=True)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    homework = relationship("Homework", back_populates="assignments")
    submissions = relationship("HomeworkSubmission", back_populates="assignment")


class HomeworkSubmission(Base):
    __tablename__ = "homework_submissions"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("homework_assignments.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="submitted")
    score_value = Column(Integer, nullable=True)
    score_percent = Column(Integer, nullable=True)
    teacher_comment = Column(Text, nullable=True)
    content = Column(Text, nullable=True)      # текст решения
    file_path = Column(String, nullable=True)  # путь к файлу, если есть

    assignment = relationship("HomeworkAssignment", back_populates="submissions")
    student = relationship("Student", back_populates="submissions")

