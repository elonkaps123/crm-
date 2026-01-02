import asyncio
import os
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram3_calendar.simple_calendar import SimpleCalendar, SimpleCalendarCallback
from aiogram.fsm.storage.memory import MemoryStorage
from .db import SessionLocal
from .models import (
    Teacher, Student, Group, GroupStudent, Lesson,
    Homework, HomeworkAssignment, HomeworkSubmission
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in environment")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить ученика"), KeyboardButton(text="👥 Создать группу")],
        [KeyboardButton(text="📅 Назначить урок"), KeyboardButton(text="📝 Создать ДЗ")],
        [KeyboardButton(text="📚 Мои назначения"), KeyboardButton(text="🏠 Главное меню")]
    ],
    resize_keyboard=True
)

BACK_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="🏠 Главное меню")]],
    resize_keyboard=True
)


# ======= Навигация =======
@dp.message(F.text == "⬅️ Назад")
async def handle_back(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Вернулись назад.", reply_markup=MAIN_KB)


@dp.message(F.text == "🏠 Главное меню")
async def handle_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню", reply_markup=MAIN_KB)


# ===== START =====
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! 👨‍🏫 Это бот Класс Рум!\nВыбирай действие ниже 👇",
        reply_markup=MAIN_KB
    )


# ===== Регистрация =====
@dp.message(Command("register_teacher"))
async def register_teacher(message: types.Message):
    tg_id = str(message.from_user.id)
    name = message.from_user.full_name

    with SessionLocal() as db:
        t = db.query(Teacher).filter_by(telegram_id=tg_id).first()
        if t:
            await message.answer("Вы уже зарегистрированы как преподаватель.")
            return

        teacher = Teacher(telegram_id=tg_id, name=name)
        db.add(teacher)
        db.commit()

    await message.answer("✅ Вы зарегистрированы как преподаватель.", reply_markup=MAIN_KB)


# ===== Добавление ученика =====
class AddStudent(StatesGroup):
    waiting_for_name = State()


@dp.message(F.text == "➕ Добавить ученика")
async def btn_add_student(message: types.Message, state: FSMContext):
    await message.answer("Введите ФИО ученика:", reply_markup=BACK_KB)
    await state.set_state(AddStudent.waiting_for_name)


@dp.message(AddStudent.waiting_for_name)
async def process_student_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    teacher_tg = str(message.from_user.id)

    with SessionLocal() as db:
        teacher = db.query(Teacher).filter_by(telegram_id=teacher_tg).first()
        if not teacher:
            await message.answer("Сначала зарегистрируйтесь: /register_teacher")
            await state.clear()
            return

        student = Student(name=name, teacher_id=teacher.id)
        db.add(student)
        db.commit()

    await message.answer(f"👨‍🎓 Ученик {name} добавлен 🎉", reply_markup=MAIN_KB)
    await state.clear()


# ===== Группа =====
class CreateGroup(StatesGroup):
    waiting_for_title = State()


@dp.message(F.text == "👥 Создать группу")
async def btn_create_group(message: types.Message, state: FSMContext):
    await message.answer("Введите название группы:", reply_markup=BACK_KB)
    await state.set_state(CreateGroup.waiting_for_title)


@dp.message(CreateGroup.waiting_for_title)
async def process_group_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    teacher_tg = str(message.from_user.id)

    with SessionLocal() as db:
        teacher = db.query(Teacher).filter_by(telegram_id=teacher_tg).first()
        if not teacher:
            await message.answer("Сначала зарегистрируйтесь: /register_teacher")
            await state.clear()
            return

        group = Group(title=title, teacher_id=teacher.id)
        db.add(group)
        db.commit()

    await message.answer(f"👥 Группа '{title}' создана ✅", reply_markup=MAIN_KB)
    await state.clear()


# ===== Урок =====
class ScheduleLesson(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_topic = State()

@dp.message(F.text == "📅 Назначить урок")
async def btn_schedule(message: types.Message, state: FSMContext):
    await state.set_state(ScheduleLesson.waiting_for_date)

    await message.answer(
        "Выберите дату урока:",
        reply_markup=await SimpleCalendar().start_calendar()
    )


@dp.message(F.text == "📅 Назначить урок")
async def btn_schedule(message: types.Message, state: FSMContext):
    await state.set_state(ScheduleLesson.waiting_for_date)
    await message.answer(
        "📅 Выберите дату урока:",
        reply_markup=await SimpleCalendar().start_calendar()
    )

@dp.callback_query(SimpleCalendarCallback.filter())
async def calendar_handler(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback, state: FSMContext):
    selected, date = await SimpleCalendar().process_selection(callback, callback_data)

    if selected:
        await state.update_data(date=date.strftime("%Y-%m-%d"))
        await callback.message.answer(f"Дата выбрана: {date.strftime('%Y-%m-%d')}")
        await callback.message.answer("Введите время (HH:MM):")
        await state.set_state(ScheduleLesson.waiting_for_time)

@dp.message(ScheduleLesson.waiting_for_time)
async def lesson_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text.strip())
    await message.answer("Введите тему урока:")
    await state.set_state(ScheduleLesson.waiting_for_topic)


@dp.message(ScheduleLesson.waiting_for_topic)
async def lesson_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()

    try:
        dt = datetime.datetime.strptime(
            f"{data['date']} {data['time']}",
            "%Y-%m-%d %H:%M"
        )
    except:
        await message.answer("❌ Неверный формат.", reply_markup=MAIN_KB)
        await state.clear()
        return

    teacher_tg = str(message.from_user.id)

    with SessionLocal() as db:
        teacher = db.query(Teacher).filter_by(telegram_id=teacher_tg).first()
        if not teacher:
            await message.answer("Сначала зарегистрируйтесь.", reply_markup=MAIN_KB)
            await state.clear()
            return

        lesson = Lesson(
            teacher_id=teacher.id,
            topic=message.text.strip(),
            start_time=dt
        )
        db.add(lesson)
        db.commit()

    await message.answer("📅 Урок назначен!", reply_markup=MAIN_KB)
    await state.clear()


# ======= ДЗ: создание =======
class CreateHomework(StatesGroup):
    waiting_for_title = State()
    waiting_for_content = State()
    waiting_for_max_score = State()
    waiting_for_saved_in_library = State()


@dp.message(F.text == "📝 Создать ДЗ")
@dp.message(Command("create_homework"))
async def create_hw(message: types.Message, state: FSMContext):
    await message.answer("Введите заголовок:", reply_markup=BACK_KB)
    await state.set_state(CreateHomework.waiting_for_title)


@dp.message(CreateHomework.waiting_for_title)
async def hw_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await message.answer("Введите описание или 'skip':", reply_markup=BACK_KB)
    await state.set_state(CreateHomework.waiting_for_content)


@dp.message(CreateHomework.waiting_for_content)
async def hw_content(message: types.Message, state: FSMContext):
    text = message.text.strip()
    await state.update_data(content=None if text.lower() == "skip" else text)
    await message.answer("Введите максимальный балл или 'skip':", reply_markup=BACK_KB)
    await state.set_state(CreateHomework.waiting_for_max_score)


@dp.message(CreateHomework.waiting_for_max_score)
async def hw_score(message: types.Message, state: FSMContext):
    text = message.text.strip()
    max_score = None

    if text.lower() != "skip":
        try:
            max_score = int(text)
        except:
            await message.answer("Введите число.", reply_markup=BACK_KB)
            return

    await state.update_data(max_score=max_score)
    await message.answer("Сохранить в библиотеке? yes/no", reply_markup=BACK_KB)
    await state.set_state(CreateHomework.waiting_for_saved_in_library)


@dp.message(CreateHomework.waiting_for_saved_in_library)
async def hw_save(message: types.Message, state: FSMContext):
    saved = message.text.strip().lower() in ("yes", "y", "да")
    data = await state.get_data()
    teacher_tg = str(message.from_user.id)

    with SessionLocal() as db:
        teacher = db.query(Teacher).filter_by(telegram_id=teacher_tg).first()
        if not teacher:
            await message.answer("Сначала /register_teacher", reply_markup=MAIN_KB)
            await state.clear()
            return

        hw = Homework(
            teacher_id=teacher.id,
            title=data["title"],
            content=data.get("content"),
            max_score=data.get("max_score"),
            saved_in_library=saved
        )
        db.add(hw)
        db.commit()
        db.refresh(hw)

    await message.answer(f"✅ Домашка создана. ID: {hw.id}", reply_markup=MAIN_KB)
    await state.clear()


# ======= Мои назначения =======
@dp.message(F.text == "📚 Мои назначения")
@dp.message(Command("my_assignments"))
async def my_assignments(message: types.Message):
    teacher_tg = str(message.from_user.id)

    with SessionLocal() as db:
        teacher = db.query(Teacher).filter_by(telegram_id=teacher_tg).first()
        if not teacher:
            await message.answer("Сначала зарегистрируйтесь.", reply_markup=MAIN_KB)
            return

        assigns = (
            db.query(HomeworkAssignment)
            .join(Homework)
            .filter(Homework.teacher_id == teacher.id)
            .all()
        )

        if not assigns:
            await message.answer("Назначений нет.", reply_markup=MAIN_KB)
            return

        text = ""
        for a in assigns:
            text += f"ID:{a.id} HW:{a.homework.title} deadline:{a.deadline}\n"

        await message.answer(text, reply_markup=MAIN_KB)


# ======= Загрузка файлов =======
@dp.message(F.document)
async def submit_file(message: types.Message):
    caption = (message.caption or "").strip()

    if not caption or not caption.split()[0].isdigit():
        await message.answer("Укажи AssignID в caption, пример: 5", reply_markup=MAIN_KB)
        return

    assign_id = int(caption.split()[0])
    student_tg = str(message.from_user.id)

    with SessionLocal() as db:
        student = db.query(Student).filter_by(telegram_id=student_tg).first()
        if not student:
            await message.answer("Сначала зарегистрируйтесь как ученик.", reply_markup=MAIN_KB)
            return

        assignment = db.query(HomeworkAssignment).filter_by(id=assign_id).first()
        if not assignment:
            await message.answer("Назначение не найдено.", reply_markup=MAIN_KB)
            return

        if assignment.deadline and datetime.datetime.utcnow() > assignment.deadline:
            await message.answer("Дедлайн прошёл.", reply_markup=MAIN_KB)
            return

        file = await message.document.get_file()
        os.makedirs("data/submissions", exist_ok=True)

        local_name = f"data/submissions/{assign_id}_{student.id}_{message.document.file_name}"
        await file.download(destination=local_name)

        submission = HomeworkSubmission(
            assignment_id=assign_id,
            student_id=student.id,
            file_path=local_name,
            status="submitted"
        )

        db.add(submission)
        db.commit()
        db.refresh(submission)

        hw = db.query(Homework).filter_by(id=assignment.homework_id).first()
        teacher = db.query(Teacher).filter_by(id=hw.teacher_id).first()

    await message.answer(f"Файл принят. Submission ID: {submission.id}", reply_markup=MAIN_KB)

    if teacher and teacher.telegram_id:
        await bot.send_message(
            int(teacher.telegram_id),
            f"📬 Новая работа. HW: {hw.title}"
        )


# ======= Оценка =======
@dp.message(Command("grade_submission"))
async def grade(message: types.Message):
    parts = message.text.strip().split(maxsplit=3)

    if len(parts) < 3:
        await message.answer(
            "Использование:\n/grade_submission <submission_id> <score> <comment>",
            reply_markup=MAIN_KB
        )
        return

    sub_id = int(parts[1])
    score = int(parts[2])
    comment = parts[3] if len(parts) > 3 else None
    teacher_tg = str(message.from_user.id)

    with SessionLocal() as db:
        teacher = db.query(Teacher).filter_by(telegram_id=teacher_tg).first()
        if not teacher:
            await message.answer("Сначала зарегистрируйтесь.", reply_markup=MAIN_KB)
            return

        submission = db.query(HomeworkSubmission).filter_by(id=sub_id).first()
        if not submission:
            await message.answer("Submission не найден.", reply_markup=MAIN_KB)
            return

        assignment = db.query(HomeworkAssignment).filter_by(id=submission.assignment_id).first()
        hw = db.query(Homework).filter_by(id=assignment.homework_id).first()

        if hw.teacher_id != teacher.id:
            await message.answer("Это не ваша работа.", reply_markup=MAIN_KB)
            return

        submission.score_value = score
        submission.score_percent = int(score / hw.max_score * 100) if hw.max_score else None
        submission.teacher_comment = comment
        submission.status = "graded"
        db.commit()

    await message.answer("Оценка выставлена.", reply_markup=MAIN_KB)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
