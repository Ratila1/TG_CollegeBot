from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, CallbackContext

import sqlite3

ADMIN_EMAIL = "weldet2007@gmail.com"
DB_PATH = "users.db"

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица для изображений расписания
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image BLOB
    )
    """)

    # Таблица для pdf файлов расписания
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_pdf (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pdf_file BLOB
    )
    """)

    # Таблица для изображений расписания по секциям (4 картинки)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_section_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        section_id INTEGER,
        image BLOB
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    year INTEGER,
    month TEXT,
    day INTEGER,
    time TEXT,
    reminder_text TEXT,
    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
);

    """)
    conn.commit()
    conn.close()

def upgrade_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Если столбец уже существует
    conn.close()

async def add_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Используйте формат: /add_mail <роль> <email>\nРоль должна быть 'студент' или 'преподаватель'."
        )
        return

    role = context.args[0].strip().lower()  # Убираем пробелы и приводим к нижнему регистру
    email = context.args[1].strip()

    if role not in ["студент", "преподаватель"]:
        await update.message.reply_text("Некорректная роль. Используйте 'студент' или 'преподаватель'.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Определяем таблицу на основе роли
    table = "student_emails" if role == "студент" else "teacher_emails"

    try:
        cursor.execute(f"INSERT INTO {table} (email) VALUES (?)", (email,))
        conn.commit()
        await update.message.reply_text(f"Email {email} успешно добавлен в список {role}.")
    except sqlite3.IntegrityError:
        await update.message.reply_text(f"Email {email} уже существует в списке {role}.")
    finally:
        conn.close()

async def delete_mail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Используйте формат: /delete_mail <роль> <email>\nРоль должна быть 'студент' или 'преподаватель'."
        )
        return

    role = context.args[0].strip().lower()  # Убираем пробелы и приводим к нижнему регистру
    email = context.args[1].strip()

    if role not in ["студент", "преподаватель"]:
        await update.message.reply_text("Некорректная роль. Используйте 'студент' или 'преподаватель'.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    table = "student_emails" if role == "студент" else "teacher_emails"

    cursor.execute(f"DELETE FROM {table} WHERE email = ?", (email,))
    if cursor.rowcount > 0:
        conn.commit()
        await update.message.reply_text(f"Email {email} успешно удален из списка {role}.")
    else:
        await update.message.reply_text(f"Email {email} не найден в списке {role}.")
    conn.close()

async def delete_previous_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    if "messages" in context.user_data:
        for message_id in context.user_data["messages"]:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
        context.user_data["messages"] = []

async def send_message_with_tracking(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, **kwargs):
    msg = await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)
    if "messages" not in context.user_data:
        context.user_data["messages"] = []
    context.user_data["messages"].append(msg.message_id)
    return msg

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await delete_previous_messages(context, chat_id)
    await menu_registration(update, context)

async def menu_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await delete_previous_messages(context, chat_id)

    keyboard = [
        [InlineKeyboardButton("Студент", callback_data="student"),
         InlineKeyboardButton("Преподаватель", callback_data="teacher"),
         InlineKeyboardButton("Посетитель", callback_data="visitor")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await send_message_with_tracking(
        context,
        chat_id,
        "Добро пожаловать в бота!\nВыберите, кто вы:",
        reply_markup=reply_markup,
    )

    # Сброс данных о пользователе
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (user_id,))
    conn.commit()
    conn.close()

async def user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await delete_previous_messages(context, chat_id)

    # Inline-кнопки
    keyboard = [
        [InlineKeyboardButton("О колледже", callback_data="about"),
         InlineKeyboardButton("Новости", callback_data="news")],
        [InlineKeyboardButton("Для абитуриентов", callback_data="applicants"),
         InlineKeyboardButton("Справочная информация", callback_data="info")],
        [InlineKeyboardButton("Контакты", callback_data="contacts"),
         InlineKeyboardButton("Соц. Сети колледжа", callback_data="socials")],  # Добавлена запятая
        [InlineKeyboardButton("FAQ", callback_data="faq")]  # Закрыта скобка
    ]
    inline_reply_markup = InlineKeyboardMarkup(keyboard)

    # Кастомная клавиатура
    custom_keyboard = [["В меню регистрации", "В главное меню", "Проблема с ботом?"]]
    custom_reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

    # Отправляем сообщение с обеими клавишами
    await send_message_with_tracking(
        context,
        chat_id,
        "Вы выбрали режим посетителя. Выберите нужную для вас информацию.",
        reply_markup=inline_reply_markup
    )

    # Отправляем второе сообщение с кастомной клавиатурой
    await send_message_with_tracking(
        context,
        chat_id,
        "Если у вас возникли проблемы или надо выйти в меню регистрации, воспользуйтесь меню под вводом сообщения",
        reply_markup=custom_reply_markup
    )

async def teacher_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await delete_previous_messages(context, chat_id)

    # Inline-кнопки
    keyboard = [
        [InlineKeyboardButton("О колледже", callback_data="about"),
         InlineKeyboardButton("Расписание", callback_data="schedule")],
        [InlineKeyboardButton("Новости", callback_data="student_news"),
         InlineKeyboardButton("Календарь событий", callback_data="event_calendar")],
        [InlineKeyboardButton("Справочная информация", callback_data="student_info"),
        InlineKeyboardButton("Соц. сети колледжа", callback_data="socials"),
         InlineKeyboardButton("FAQ", callback_data="faq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Кастомная клавиатура
    custom_keyboard = [["В меню регистрации", "В главное меню", "Проблема с ботом?"]]
    reply_custom = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

    # Отправляем inline-кнопки
    await send_message_with_tracking(
        context,
        chat_id,
        "Здравствуйте, вы находитесь в меню преподавателя. Выберите нужную для вас информацию.",
        reply_markup=reply_markup,
    )

    # Отправляем кастомную клавиатуру
    await send_message_with_tracking(
        context,
        chat_id,
        "Если у вас возникли проблемы или надо выйти в меню регистрации, воспользуйтесь меню под вводом сообщения",
        reply_markup=reply_custom,
    )

async def student_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await delete_previous_messages(context, chat_id)

    # Inline-кнопки
    keyboard = [
        [InlineKeyboardButton("О колледже", callback_data="about"),
         InlineKeyboardButton("Расписание", callback_data="schedule")],
        [InlineKeyboardButton("Новости", callback_data="student_news"),
         InlineKeyboardButton("Справочная информация", callback_data="student_info")],
        [InlineKeyboardButton("Контакты преподавателей и администрации", callback_data="contacts_staff")],
        [InlineKeyboardButton("Соц. сети колледжа", callback_data="socials"),
        InlineKeyboardButton("FAQ", callback_data="faq")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Кастомная клавиатура
    custom_keyboard = [["В меню регистрации", "В главное меню", "Проблема с ботом?"]]
    reply_custom = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

    # Отправляем inline-кнопки
    await send_message_with_tracking(
        context,
        chat_id,
        "Здравствуйте, вы находитесь в меню студента. Выберите нужную для вас информацию.",
        reply_markup=reply_markup,
    )

    # Отправляем кастомную клавиатуру
    await send_message_with_tracking(
        context,
        chat_id,
        "Если у вас возникли проблемы или надо выйти в меню регистрации, воспользуйтесь меню под вводом сообщения",
        reply_markup=reply_custom,
    )

async def news_post(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Указываем ID канала (можно использовать username канала, например: '@ggmk_gomel')
    source_channel_id = "@ggmk_gomel"  # Канал, из которого нужно переслать сообщение

    # Получаем последние 1 сообщение из канала
    async for message in context.bot.get_chat_history(source_channel_id, limit=1):
        # Пересылаем сообщение в чат пользователя
        await context.bot.forward_message(
            chat_id=chat_id,  # Чат пользователя, куда пересылаем сообщение
            from_chat_id=source_channel_id,  # Канал, из которого пересылаем
            message_id=message.message_id  # ID последнего сообщения
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if "awaiting_email" in context.user_data:
        role = context.user_data.pop("awaiting_email")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Проверяем почту
        if role == "student":
            cursor.execute("SELECT email FROM student_emails WHERE email = ?", (text,))
        elif role == "teacher":
            cursor.execute("SELECT email FROM teacher_emails WHERE email = ?", (text,))
        result = cursor.fetchone()
        conn.close()

        if result:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO users (telegram_id, role, email) VALUES (?, ?, ?)", (user_id, role, text))
            conn.commit()
            conn.close()

            if role == "student":
                await student_menu(update, context)
            elif role == "teacher":
                await teacher_menu(update, context)
        else:
            await update.message.reply_text("Эта почта не зарегистрирована для выбранной роли.")
    elif text == "В меню регистрации":
        await menu_registration(update, context)
    elif text == "В главное меню":
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Исправленный запрос для извлечения роли пользователя
        cursor.execute("SELECT role FROM users WHERE telegram_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            role = result[0]
            if role == "student":
                await student_menu(update, context)
            elif role == "teacher":
                await teacher_menu(update, context)
            elif role == "visitor":
                await user_menu(update, context)
            else:
                await update.message.reply_text("Роль пользователя не определена. Обратитесь к администратору.")
        else:
            await update.message.reply_text("Вы не зарегистрированы. Пожалуйста, пройдите регистрацию.")
    elif text == "Проблема с ботом?":
        await update.message.reply_text("Пожалуйста, опишите вашу проблему, и мы постараемся вам помочь.")
    else:
        await update.message.reply_text("Я не понимаю ваш запрос. Выберите действие из меню.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    role = query.data

    # Логирование полученных данных
    print(f"[LOG] Received callback data: {role}")
    print(f"[LOG] User ID: {user_id}")
    print(f"[LOG] Current user_data: {context.user_data}")

    # Основная обработка ролей
    if role in ["student", "teacher"]:
        print(f"[LOG] Role selected: {role}")
        await send_message_with_tracking(context, query.message.chat_id, "Введите вашу зарегистрированную почту:")
        context.user_data["awaiting_email"] = role
        print("[LOG] Awaiting email set in user_data.")
    elif role == "visitor":
        print("[LOG] Visitor role selected. Saving to database.")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("REPLACE INTO users (telegram_id, role) VALUES (?, ?)", (user_id, role))
        conn.commit()
        conn.close()
        await user_menu(update, context)
        print("[LOG] Visitor role saved and user menu called.")
    elif role == "about":
        print("[LOG] 'About' section requested.")
        await college_info(update, context)
    elif role == "schedule":
        print("[LOG] Schedule requested.")
        await schedule(update, context)
    elif role == "schedule_tom":
        print("[LOG] Schedule for tomorrow requested.")
        await shedule_tom(update, context)
    elif role == "schedule_year":
        print("[LOG] Yearly schedule requested.")
        await shedule_year(update, context)
    elif role == "schedule_section":
        print("[LOG] Section schedule requested.")
        await shedule_section(update, context)
    elif role in ["student_news", "news"]:
        print("[LOG] News section requested.")
        await query.message.reply_text("Здесь будут новости.")
    elif role in ["student_info", "info"]:
        print("[LOG] Info section requested.")
        await information(update, context)
    elif role in ["contacts_staff", "contacts"]:
        print("[LOG] Contacts section requested.")
        await contacts(update, context)
    elif role == "event_calendar":
        print("[LOG] Event calendar requested.")
        await query.message.reply_text("Здесь будет информация о календаре событий.")
    elif role == "socials":
        print("[LOG] Socials section requested.")
        await web(update, context)
    elif role == "faq":
        print("[LOG] FAQ section requested.")
        await faq(update, context)
    elif role == "admissions":
        print("[LOG] Admissions section requested.")
        await admissions(update, context)
    elif role == "applicants":
        print("[LOG] Applicants section requested.")
        await abitur(update, context)
    elif role == "extra_material":
        print("[LOG] Extra material section requested.")
        await query.message.reply_text("Здесь будет дополнительный материал.")
    elif role == "college_rules":
        print("[LOG] College rules requested.")
        await information_rules(update, context)
    elif role == "admission_dates":
        print("[LOG] Admission dates section requested.")
        await deadlines(update, context)
    elif role == "specialties":
        print("[LOG] Specialties section requested.")
        await specials(update, context)
    elif role.startswith("specialty_"):
        specialty_functions = {
            "1": metals,
            "2": emergency,
            "3": mobile_programming,
            "4": economic_planning,
            "5": software_development,
            "6": tech_service_robotics,
            "7": tech_support_machining,
            "8": tech_support_transport,
        }
        specialty_id = role.split("_")[1]
        print(f"[LOG] Specialty selected: {specialty_id}")
        if specialty_id in specialty_functions:
            await specialty_functions[specialty_id](update, context)
    elif role == "back":
        print("[LOG] Back to specialties.")
        await specials(update, context)

async def web(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    socials_message = (
        "🎉 **Присоединяйтесь к нашим социальным сетям!**\n"
        "Будьте в курсе последних новостей, мероприятий и достижений колледжа!\n\n"
        "🌐 **Вот где нас найти:**\n"
        "🌐 **Наш сайт:** [uoggmk.by](http://uoggmk.by) — официальный сайт колледжа для подробной информации.\n"
        "🔹 [Наш Telegram-канал](https://t.me/ggmk_gomel) — все важные анонсы и обновления.\n"
        "📸 [Instagram](https://www.instagram.com/ggmk.gomel/) — яркие фото и жизнь колледжа.\n"
        "🎥 [TikTok](https://www.tiktok.com/@ggmk_official) — динамичные видео и интересные тренды.\n"
        "💬 [ВКонтакте](https://vk.com/ggmk_club) — общение, события и многое другое.\n\n"
        "Подписывайтесь и оставайтесь на связи с нами! ✨"
    )

    # Отправка сообщения с поддержкой обычного Markdown
    await context.bot.send_message(
        chat_id=chat_id,
        text=socials_message,  # Используем socials_message
        parse_mode="Markdown",  # Используем старую версию Markdown
        disable_web_page_preview=True
    )

async def college_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    message = (
        "🎉 *Гомельскому государственному машиностроительному колледжу – 65 лет!* 🎓\n\n"
        "С момента основания в 1955 году колледж прошёл путь становления, став одним из ведущих образовательных учреждений региона. "
        "За 65 лет здесь подготовили более 22 тысяч квалифицированных специалистов, которые успешно трудятся на благо Беларуси.\n\n"
        "📚 *Наши достижения*:\n"
        "• 66 педагогов, включая кандидатов наук, магистров и обладателей высших квалификационных категорий.\n"
        "• Награды: грамоты Министерства образования, победы в республиканских и международных конкурсах.\n"
        "• Активное участие в научных конференциях и инновационных проектах, включая адаптивные мультимедиа технологии для лиц с нарушением слуха.\n"
        "• Уникальный проект *«Театр Тишины»* и студенческая газета *«Муравейник»*.\n\n"
        "🌟 *Важные даты*:\n"
        "• *1955* – Основание как машиностроительный техникум на базе завода «Гомсельмаш».\n"
        "• *1963* – Открытие отделения для глухих и слабослышащих.\n"
        "• *2007* – Переименование в Гомельский государственный машиностроительный колледж.\n\n"
        "🏆 *Признание*:\n"
        "• Лауреат областных и республиканских конкурсов.\n"
        "• Занесение на Доску Почета города Гомеля в номинации *«Лучшее учреждение среднего специального образования»*.\n\n"
        "🎓 *Специальности*:\n"
        "• Программируемые мобильные системы.\n"
        "• Предупреждение и ликвидация чрезвычайных ситуаций. И другие!\n\n"
        "💡 *Социальное партнёрство*:\n"
        "Колледж активно сотрудничает с ведущими предприятиями региона, а его выпускники возвращаются в стены альма-матер уже в качестве педагогов и специалистов.\n\n"
        "✨ *Гордость региона, успех страны!*"
    )

    # Отправка сообщения
    await context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def specials(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    # Сообщение, которое будет отправлено
    message = (
        "🌟 В нашем колледже представлены 8 уникальных специальностей, каждая из которых откроет перед вами новые горизонты! 🚀\n\n"
        "💼 Выберите ту, которая соответствует вашим интересам и амбициям, и начните свой путь к успешной карьере уже сегодня! 🌱\n\n"
        "🎓 Станьте частью нашей дружной и профессиональной команды!"
    )

    # Кнопки для выбора специальности
    keyboard = [
        [InlineKeyboardButton("Производство и переработка металлов", callback_data='specialty_1')],
        [InlineKeyboardButton("Предупреждение и ликвидация чрезвычайных ситуаций", callback_data='specialty_2')],
        [InlineKeyboardButton("Программирование мобильных устройств", callback_data='specialty_3')],
        [InlineKeyboardButton("Планово-экономическая и аналитическая деятельность", callback_data='specialty_4')],
        [InlineKeyboardButton("Разработка и сопровождение программного обеспечения информационных систем", callback_data='specialty_5')],
        [InlineKeyboardButton("Техническое обслуживание технологического оборудования и средств робототехники в автоматизированном производстве", callback_data='specialty_6')],
        [InlineKeyboardButton("Технологическое обеспечение машиностроительного производства", callback_data='specialty_7')],
        [InlineKeyboardButton("Техническое обслуживание электронных систем транспортных средств", callback_data='specialty_8')]
    ]

    # Отправка сообщения с кнопками
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def abitur(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    # Сообщение, которое будет отправлено
    message = (
        "🎓 **Добро пожаловать в наш колледж!** 🌟\n\n"
        "Мы рады пригласить вас стать частью нашей дружной и профессиональной команды. Наш колледж предлагает уникальные возможности для развития и карьеры!\n\n"
        "🔍 Выберите интересующую вас информацию, чтобы узнать больше:\n"
    )

    # Кнопки для выбора информации
    keyboard = [
        [InlineKeyboardButton("Специальности", callback_data='specialties')],
        [InlineKeyboardButton("Приемная комиссия и требуемые документы", callback_data='admissions')],
        [InlineKeyboardButton("Сроки проведения приемной кампании", callback_data='admission_dates')]
    ]

    # Отправка сообщения с кнопками
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def contacts(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    # Сообщение с контактной информацией
    message = (
        "📞 **Контакты для связи с нашим колледжем:**\n\n"
        
        "👨‍🏫 **Приёмная директора:**\n"
        "📞 8 (0232) 50-12-71\n\n"
        
        "📝 **Приёмная комиссия:**\n"
        "📞 8 (0232) 50-12-73\n\n"
        
        "---\n\n"
        
        "📞 **Телефоны «Горячей линии» государственной комиссии по контролю за ходом вступительных испытаний:**\n\n"
        "Работа горячих линий организована с понедельника по пятницу с 9:00 до 13:00 и с 14:00 до 18:00.\n\n"
        
        "**Рабочая группа государственной комиссии (КГГ):**\n"
        "📞 8 017 327-66-80\n"
        "Режим работы: Пн-Пт с 9:00 до 13:00 и с 14:00 до 18:00\n\n"
        "Горячая линия также работает в выходные дни: 23.06 (Вс), 29.06 (Сб), 06.07 (Сб), 20.07 (Сб), 27.07 (Сб)\n\n"
        
        "**Гомельская областная комиссия (КГК Гомельской области):**\n"
        "📞 +375 232 23 83 85\n"
        "📞 +375 232 23 83 68\n\n"
        
        "**Горячая линия Министерства образования Республики Беларусь (работает только в период приемной кампании):**\n"
        "📞 8-017 222-43-12\n\n"
        
        "**Черненький Дмитрий Николаевич** — заместитель начальника отдела дошкольного, общего среднего, специального профессионального образования\n"
        "📞 8 232 35 70 18\n\n"
        
        "Мы всегда готовы ответить на все ваши вопросы и помочь! 🌟"
    )
    
    # Отправка сообщения с контактами
    await context.bot.send_message(chat_id=chat_id, text=message)

async def schedule(update: Update, context: CallbackContext):

    chat_id = update.effective_chat.id

    # Сообщение с предложением выбрать расписание
    message = (
        "📅 В нашем боте хранится свежая информация по расписанию.\n\n"
        "Выберите нужное расписание:"
    )

    # Inline кнопки для выбора расписания
    keyboard = [
        [InlineKeyboardButton("Расписание на завтра", callback_data='schedule_tom')],
        [InlineKeyboardButton("Расписание на семестр", callback_data='schedule_year')],
        [InlineKeyboardButton("Расписание секций", callback_data='schedule_section')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправка сообщения с кнопками
    await context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup)

async def shedule_tom(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Пересылаем сообщение с расписанием на завтра (сообщение с картинкой)
    try:
        # Ожидаем, что картинка была отправлена в канал первым
        await context.bot.forward_message(chat_id=chat_id, from_chat_id='@BotGmk', message_id=3)
        await update.effective_message.reply_text("Вот ваше расписание на завтра.")
    except Exception as e:
        await update.effective_message.reply_text(f"Ошибка при пересылке: {e}")

async def shedule_year(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    # Пересылаем сообщение с расписанием на семестр (PDF файл)
    try:
        # Ожидаем, что PDF был отправлен в канал вторым
        await context.bot.forward_message(chat_id=chat_id, from_chat_id='@BotGmk', message_id=2)
        await update.effective_message.reply_text("Вот ваше расписание на семестр.")
    except Exception as e:
        await update.effective_message.reply_text(f"Ошибка при пересылке: {e}")

async def shedule_section(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message_ids = [4, 5, 6, 7]  # ID сообщений с расписанием секций

    try:
        # Пересылаем каждое сообщение по очереди
        for message_id in message_ids:
            await context.bot.forward_message(chat_id=chat_id, from_chat_id='@BotGmk', message_id=message_id)
        
        await update.effective_message.reply_text("Вот ваше расписание секций.")
    except Exception as e:
        await update.effective_message.reply_text(f"Ошибка при пересылке: {e}")

async def information(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Текст сообщения
    text = "Здесь хранится информация, дополнительные материалы колледжа. Выберите интересующее вас."

    # Создаем инлайн-кнопки
    keyboard = [
        [InlineKeyboardButton("Дополнительный материал", callback_data="extra_material")],
        [InlineKeyboardButton("Правила колледжа", callback_data="college_rules")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Если это callback от inline кнопки
    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Отвечаем на запрос
        await query.message.reply_text(text, reply_markup=reply_markup)
    elif update.message:
        # Если это обычное сообщение (например, текстовое)
        await update.message.reply_text(text, reply_markup=reply_markup)

async def information_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Текст сообщения
    text = (
        "📜 **Правила внутреннего распорядка колледжа** 📜\n\n"
        "👩‍🎓👨‍🎓 **1. Общие положения:**\n\n"
        "Соблюдайте правила колледжа, уважайте друг друга и имущество.\n"
        "Запрещены курение, алкоголь, наркотики и опасные вещества.\n\n"
        "📚 **2. Учебный процесс:**\n\n"
        "Посещайте занятия вовремя. Пропуски возможны только по уважительным причинам.\n"
        "Выполняйте задания, участвуйте в проектах и мероприятиях.\n"
        "На уроках запрещено пользоваться мобильными телефонами без разрешения.\n\n"
        "👔 **3. Внешний вид:**\n\n"
        "Придерживайтесь делового стиля одежды или установленного дресс-кода.\n"
        "Одежда должна быть опрятной и подходящей для учебного процесса.\n\n"
        "🏫 **4. Поведение на территории:**\n\n"
        "Соблюдайте порядок и тишину.\n"
        "Уничтожение имущества или мусор — недопустимо.\n"
        "Сообщайте администрации о любых инцидентах.\n\n"
        "🔥 **5. Безопасность:**\n\n"
        "Следуйте правилам пожарной безопасности и инструкциям при ЧС.\n"
        "Используйте личный транспорт только в отведённых местах.\n\n"
        "📋 **6. Взаимодействие с администрацией:**\n\n"
        "Обращения должны быть вежливыми и конструктивными.\n"
        "Конфликтные ситуации решаются через куратора или администрацию.\n\n"
        "💻 **7. Использование техники:**\n\n"
        "Компьютеры и оборудование используются только с разрешения преподавателя.\n"
        "Интернет доступен исключительно для учебных целей.\n\n"
        "⚠️ **8. Санкции за нарушения:**\n\n"
        "Замечание, выговор или иные меры в зависимости от серьёзности нарушения.\n\n"
        "✨ **Следуйте правилам, и учёба станет комфортной и успешной!** 🎓"
    )

    if update.callback_query:
        query = update.callback_query
        await query.answer()  # Отвечаем на запрос
        await query.message.reply_text(text, parse_mode="Markdown")
    elif update.message:
        # Если это обычное сообщение
        await update.message.reply_text(text, parse_mode="Markdown")

async def faq(update: Update, context: CallbackContext):
    text = (
        "*Вопрос:* Предоставляется ли общежитие иногородним учащимся?  \n"
        "*Ответ:* Да. Все иногородние учащиеся обеспечиваются общежитием.\n\n"
        
        "---\n\n"
        
        "*Вопрос:* Какое преимущество дает наличие удостоверения ЧАЭС?  \n"
        "*Ответ:* Удостоверение ЧАЭС, как и удостоверение многодетной семьи и другие подобные документы, дает преимущественное право на зачисление при равных сумме баллов (Пункт 29 Правил приема лиц для получения среднего специального образования).\n\n"
        
        "---\n\n"
        
        "*Вопрос:* Какой у вас проходной балл?  \n"
        "*Ответ:* Проходной балл текущего года формируется после завершения приема на конкретную специальность (бюджетной или платной формы обучения)."
    )

    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown")
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown")
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def admissions(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    # Сообщение с информацией о приеме
    message = (
        "📍 **Приемная комиссия**\n\n"
        "🗓 **График работы:** понедельник – суббота, с 9.00 до 18.00\n"
        "🏢 **Адрес колледжа:** г. Гомель, ул. Объездная, 2\n"
        "📞 **Телефон:** 50-12-73\n\n"
        
        "📋 **Перечень документов для подачи**\n"
        "Абитуриенты подают в приемную комиссию следующие документы:\n\n"
        "- Заявление на имя руководителя колледжа по установленной форме;\n"
        "- Оригиналы документа об образовании и приложения к нему;\n"
        "- Медицинскую справку по форме, установленной Министерством здравоохранения;\n"
        "- Документы, подтверждающие право абитуриента на льготы при приеме на обучение;\n"
        "- Шесть фотографий размером 3x4 см.\n\n"
        
        "Дополнительно (при необходимости) в приемную комиссию представляются:\n\n"
        "- Заключение врачебно-консультационной или медико-реабилитационной экспертной комиссии об отсутствии противопоказаний для обучения по выбранной специальности (для лиц, закончивших учреждения, обеспечивающие получение специального образования, детей-инвалидов в возрасте до 18 лет, инвалидов I, II и III группы);\n"
        "- Заключение государственного центра коррекционно-развивающего обучения и реабилитации по рекомендации обучения в учреждениях, обеспечивающих получение специального образования (для лиц с нарушениями зрения, слуха, функций опорно-двигательного аппарата);\n"
        "- Паспорт или заменяющий его документ (предъявляется абитуриентом отдельно).\n\n"
        
        "🎓 **Условия поступления:**\n"
        "Абитуриенты, поступающие на все специальности на основе общего базового образования, общего среднего образования, на дневную форму получения образования, зачисляются по конкурсу среднего балла документа об образовании.\n\n"
        
        "🏠 **ИНОГОРОДНИМ УЧАЩИМСЯ ПРЕДОСТАВЛЯЕТСЯ ОБЩЕЖИТИЕ**\n\n"
        
        "Адрес колледжа: г. Гомель, ул. Объездная, 2\n"
        "Телефон: 50-12-73"
    )
    
    # Отправка сообщения с информацией о приеме
    await context.bot.send_message(chat_id=chat_id, text=message)

async def deadlines(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    
    try:
        # Пересылаем 8-е сообщение из канала
        await context.bot.forward_message(chat_id=chat_id, from_chat_id='@BotGmk', message_id=8)
        await update.message.reply_text("Вот информация о сроках.")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при пересылке: {e}")

async def metals(update: Update, context: CallbackContext):
    text = (
        "🔧 **ПРОИЗВОДСТВО И ПЕРЕРАБОТКА МЕТАЛЛОВ**\n\n"
        "📚 **Специальность:**\n"
        "5-04-0714-04  «Производство и переработка металлов»\n\n"
        
        "🎓 **Квалификация специалиста:**\n"
        "«Техник-технолог»\n\n"
        
        "🛠️ **Квалификация рабочего:**\n"
        "- Заливщик металлов – 3-4 разряд\n"
        "- Плавильщик металлов и сплавов – 3-4 разряд\n"
        "- Контролер в литейном производстве – 3-4 разряд\n"
        "- Слесарь-ремонтник – 3-4 разряд\n"
        "- Формовщик машинной формовки – 3-4 разряд\n\n"
        
        "🕒 **Продолжительность обучения:**\n"
        "Общее базовое образование — 3 года 7 месяцев\n\n"
        
        "🎓 **Форма обучения:**\n"
        "Дневная (бюджетная)\n\n"
        
        "💼 **Профессиональная сфера специалиста:**\n"
        "Производство готовых металлических изделий, кроме машин и оборудования.\n\n"
        
        "🔧 **Объектами профессиональной деятельности специалиста являются:**\n"
        "- Технологическое оборудование, технологическая оснастка и комплектующие\n"
        "- Элементы для технологического оборудования и производства, средства автоматизации\n"
        "- Производственный и технологический процесс\n"
        "- Обрабатываемые материалы\n"
        "- Нормативные правовые акты (НПА) и технические нормативные правовые акты (ТНПА), регламентирующие профессиональную деятельность, и технологическая документация"
    )
    
    # Создание inline кнопки "Назад"
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверка типа сообщения и отправка с reply_markup
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def emergency(update: Update, context: CallbackContext):
    text = (
        "🔥 **ПРЕДУПРЕЖДЕНИЕ И ЛИКВИДАЦИЯ ЧРЕЗВЫЧАЙНЫХ СИТУАЦИЙ**\n\n"
        "📚 **Специальность:**\n"
        "5-04-1033-01 «Предупреждение и ликвидация чрезвычайных ситуаций»\n\n"
        
        "🎓 **Квалификация специалиста:**\n"
        "«Техник»\n\n"
        
        "🛠️ **Квалификация рабочего:**\n"
        "Спасатель-пожарный – 7 разряд\n\n"
        
        "🕒 **Продолжительность обучения:**\n"
        "На основе общего среднего образования — 2 года 7 месяцев\n\n"
        
        "🎓 **Форма обучения:**\n"
        "Дневная (бюджетная и платная)\n\n"
        
        "💼 **Подразделения для работы специалистов:**\n"
        "- Подразделения городских и районных отделов по ЧС;\n"
        "- Подразделения специального назначения Министерства по чрезвычайным ситуациям (МЧС);\n"
        "- Аварийно-спасательные, аварийно-восстановительные подразделения других республиканских органов государственного управления, объединений (учреждений), подчиненных правительству Республики Беларусь."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def mobile_programming(update: Update, context: CallbackContext):
    text = (
        "📱 **ПРОГРАММИРОВАНИЕ МОБИЛЬНЫХ УСТРОЙСТВ**\n\n"
        "📚 **Специальность:**\n"
        "5-04-0611-01 «Программирование мобильных устройств»\n\n"
        
        "🎓 **Квалификация:**\n"
        "Техник-программист\n\n"
        
        "🕒 **Срок получения образования:**\n"
        "На основе общего базового образования – 3 года 10 месяцев\n\n"
        
        "🎓 **Форма получения образования:**\n"
        "Дневная\n\n"
        
        "🛠️ **Квалификация рабочего:**\n"
        "Оператор электронных вычислительных машин (персональных ЭВМ), 5-й разряд\n\n"
        
        "💼 **Основные виды (подвидами) профессиональной деятельности специалиста:**\n"
        "- Деятельность в области проводной связи;\n"
        "- Деятельность в области беспроводной связи;\n"
        "- Компьютерное программирование, консультационные и другие сопутствующие услуги;\n"
        "- Деятельность в области информационного обслуживания.\n\n"
        
        "🔧 **Объектами профессиональной деятельности специалиста являются:**\n"
        "- Программируемые мобильные устройства и их составные функциональные части;\n"
        "- Радиоэлектронные устройства и специализированные электронные вычислительные устройства (микропроцессоры);\n"
        "- Технологии программирования мобильных устройств;\n"
        "- Нормативные правовые акты, технические нормативные правовые акты, технологическая документация по разработке программного обеспечения."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def economic_planning(update: Update, context: CallbackContext):
    text = (
        "📊 **ПЛАНОВО-ЭКОНОМИЧЕСКАЯ И АНАЛИТИЧЕСКАЯ ДЕЯТЕЛЬНОСТЬ**\n\n"
        "📚 **Специальность:**\n"
        "5-04-0311-01 «Планово-экономическая и аналитическая деятельность»\n\n"
        
        "🎓 **Квалификация специалиста:**\n"
        "Техник-экономист\n\n"
        
        "🕒 **Продолжительность обучения:**\n"
        "На основе общего базового образования — 3 года\n\n"
        
        "🎓 **Форма обучения:**\n"
        "Дневная (платная)\n\n"
        
        "📘 **Специалист должен знать:**\n"
        "- Основы технологии машиностроения, металлообрабатывающих станков и инструментов;\n"
        "- Материалы, которые применяются в машиностроении, и способы их производства;\n"
        "- Основы машиностроительного черчения;\n"
        "- Основные положения Государственной системы стандартизации, показатели качества продукции, критерии оценки качества, требования к сертификации продукции;\n"
        "- Порядок проведения сертификации продукции предприятия;\n"
        "- Механизм разработки бизнес-плана и методику расчета технико-экономических показателей;\n"
        "- Характеристику методов исследования трудовых процессов и затрат рабочего времени, методологические положения по обоснованию норм труда."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def software_development(update: Update, context: CallbackContext):
    text = (
        "💻 **РАЗРАБОТКА И СОПРОВОЖДЕНИЕ ПРОГРАММНОГО ОБЕСПЕЧЕНИЯ ИНФОРМАЦИОННЫХ СИСТЕМ**\n\n"
        "📚 **Специальность:**\n"
        "5-04-0612-02 «Разработка и сопровождение программного обеспечения информационных систем»\n\n"
        
        "🎓 **Квалификация:**\n"
        "Техник-программист\n\n"
        
        "🕒 **Срок получения образования:**\n"
        "На основе общего базового образования – 3 года 10 месяцев\n\n"
        
        "🎓 **Форма получения образования:**\n"
        "Дневная\n\n"
        
        "🛠️ **Квалификация рабочего:**\n"
        "Оператор электронных вычислительных машин (персональных электронно-вычислительных машин), 5-й разряд\n\n"
        
        "📘 **Основными видами профессиональной деятельности специалиста являются:**\n"
        "- Деятельность в области компьютерного программирования;\n"
        "- Консультационные услуги в области компьютерных технологий;\n"
        "- Деятельность по управлению компьютерными системами.\n\n"
        
        "🔧 **Объектами профессиональной деятельности специалиста являются:**\n"
        "- Вычислительные системы (компьютерные системы);\n"
        "- Программное обеспечение компьютерных систем (программы, программные комплексы и системы);\n"
        "- Системы и технологии разработки программного обеспечения;\n"
        "- Сопроводительная документация по разработке программного обеспечения."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def tech_service_robotics(update: Update, context: CallbackContext):
    text = (
        "🤖 **ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ ТЕХНОЛОГИЧЕСКОГО ОБОРУДОВАНИЯ И СРЕДСТВ РОБОТОТЕХНИКИ В АВТОМАТИЗИРОВАННОМ ПРОИЗВОДСТВЕ**\n\n"
        
        "📚 **Специальность:**\n"
        "5-04-0713-08 «Техническая эксплуатация технологического оборудования и средств робототехники в автоматизированном производстве»\n\n"
        
        "🎓 **Квалификация специалиста:**\n"
        "Техник-электроник\n\n"
        
        "🛠️ **Квалификации рабочего:**\n"
        "- Оператор станков с ПУ (3,4 разряд);\n"
        "- Слесарь-электромонтажник (2-3 разряд);\n"
        "- Слесарь контрольно-измерительных приборов и автоматики (3-4 разряд);\n"
        "- Наладчик технологического оборудования (3-4 разряд);\n"
        "- Наладчик контрольно-измерительных приборов и автоматики (4 разряд);\n"
        "- Оператор автоматических и полуавтоматических линий станков и установок (3-4 разряд);\n"
        "- Электромонтер по ремонту и обслуживанию электрооборудования (3-4 разряд).\n\n"
        
        "🕒 **Продолжительность обучения:**\n"
        "- 3 года 7 месяцев (на базе 9 классов);\n"
        "- 2 года 7 месяцев (на базе 11 классов).\n\n"
        
        "🎓 **Форма обучения:**\n"
        "Дневная (бюджетная)\n\n"
        
        "💼 **Профессиональная сфера деятельности и назначение специалиста:**\n"
        "Техник-электроник подготавливается для наладки и эксплуатации электронных систем программного управления на предприятиях машиностроительного комплекса в механических, механосборочных цехах, лабораториях, отделах заводов, производящих и эксплуатирующих электронные системы программного управления. Специалисты работают на должностях техника, техника по ремонту и эксплуатации оборудования, а также на рабочих местах в соответствии с перечнем рабочих профессий высших разрядов, на которых должны быть использованы специалисты со средним специальным образованием."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def tech_support_machining(update: Update, context: CallbackContext):
    text = (
        "🔧 **ТЕХНОЛОГИЧЕСКОЕ ОБЕСПЕЧЕНИЕ МАШИНОСТРОИТЕЛЬНОГО ПРОИЗВОДСТВА**\n\n"
        
        "📚 **Специальность:**\n"
        "5-04-0714-01 Технологическое обеспечение машиностроительного производства\n\n"
        
        "🎓 **Квалификация специалиста:**\n"
        "Техник\n\n"
        
        "🛠️ **Квалификации рабочего:**\n"
        "- Оператор станков с программным управлением — 3-4 разряд\n"
        "- Токарь — 3-4 разряд\n"
        "- Фрезеровщик — 3-4 разряд\n"
        "- Контролер станочных и слесарных работ — 3-4 разряд\n"
        "- Контролер измерительных приборов и специального инструмента — 3-4 разряд\n\n"
        
        "🕒 **Продолжительность обучения:**\n"
        "- На основе общего базового образования — 3 года 7 месяцев\n"
        "- На основе общего среднего (специального) образования (лица с ОПФР) — 2 года 7 месяцев\n\n"
        
        "🎓 **Форма обучения:**\n"
        "Дневная (бюджетная)\n\n"
        
        "💼 **Профессиональная сфера деятельности и назначение специалиста:**\n"
        "Техник подготавливается для производственно-технологической, эксплуатационной и организационно-управленческой деятельности на предприятиях машиностроительного комплекса, в коммерческих и образовательных учреждениях, в механических, механосборочных, ремонтных, инструментальных цехах, лабораториях, технологических бюро и отделах. Специалист может работать на должностях: техника-технолога, мастера, контрольного мастера, а также на рабочих местах в соответствии с перечнем рабочих профессий высших разрядов, которые подлежат замещению специалистами со средним специальным образованием."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def tech_support_transport(update: Update, context: CallbackContext):
    text = (
        "🚗 **ТЕХНИЧЕСКОЕ ОБСЛУЖИВАНИЕ ЭЛЕКТРОННЫХ СИСТЕМ ТРАНСПОРТНЫХ СРЕДСТВ**\n\n"
        
        "📚 **Специальность:**\n"
        "5-04-0715-05 «Техническое обслуживание электронных систем транспортных средств»\n"
        "(Специальность 2-36 04 32 «Электроника механических транспортных средств»)\n\n"
        
        "🎓 **Квалификация:**\n"
        "Техник-электроник\n\n"
        
        "🕒 **Срок получения образования по специальности составляет:**\n"
        "- На основе общего базового образования (9-ти классов) — 3 года 7 месяцев\n\n"
        
        "🎓 **Форма получения образования:**\n"
        "Дневная (бюджет)\n\n"
        
        "🛠️ **Наименование профессии рабочего:**\n"
        "- Слесарь-электрик по ремонту электрооборудования, 3-4 разряд\n"
        "- Электромонтер по ремонту и обслуживанию электрооборудования, 3-4 разряд\n"
        "- Слесарь по контрольно-измерительным приборам и автоматике, 3-4 разряд\n"
        "- Слесарь по ремонту автомобилей, 3-4 разряд\n"
        "- Наладчик контрольно-измерительных приборов и систем автоматики, 4 разряд\n\n"
        
        "💼 **Профессиональная сфера деятельности:**\n"
        "Техник-электроник способен обеспечить правильное функционирование технического оборудования, поддерживать бесперебойную работу электроники, организовывать техническое обслуживание электронных устройств, поддерживать их работоспособность, эффективно использовать ресурсы, проводить профилактику и текущий ремонт оборудования и автомобилей. Он контролирует параметры и надежность электронных компонентов, а также проводит проверки для своевременного выявления неисправностей и их устранения.\n\n"
        
        "📍 **Профессиональная сфера деятельности техника-электроника охватывает:**\n"
        "Организации различных правовых форм, занимающиеся производством и эксплуатацией электронных систем механических транспортных средств."
    )
    keyboard = [
        [InlineKeyboardButton("Назад", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Проверка типа сообщения и отправка
    if update.message:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    elif update.effective_message:
        await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    else:
        await update.callback_query.answer("Произошла ошибка при получении сообщения.")

async def reminder(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.user_data.clear()  # Сброс данных, если они есть

    if update.message:
        # Обработка сообщения
        await update.message.reply_text(
            "Вы вошли в функцию напоминаний. Выберите год для напоминания.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(str(year), callback_data=str(year)) for year in range(2024, 2028)
            ]])
        )
    elif update.callback_query:
        # Обработка callback-запроса
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "Вы вошли в функцию напоминаний. Выберите год для напоминания.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(str(year), callback_data=str(year)) for year in range(2024, 2028)
            ]])
        )

async def select_year(update: Update, context: CallbackContext):
    query = update.callback_query
    selected_year = int(query.data)
    context.user_data['year'] = selected_year  # Сохраняем выбранный год

    await query.answer()

    # Создаем inline кнопки для выбора месяца
    await query.edit_message_text(
        f"Вы выбрали {selected_year}. Теперь выберите месяц.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton(month, callback_data=month.lower()) for month in
            ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        ]])
    )

async def select_month(update: Update, context: CallbackContext):
    query = update.callback_query
    selected_month = query.data.capitalize()  # Сохраняем выбранный месяц
    context.user_data['month'] = selected_month

    # Определяем, сколько дней в выбранном месяце
    month_days = 31
    if selected_month in ["Февраль"]:
        month_days = 28  # Пример: для февраля используем 28 дней
    elif selected_month in ["Апрель", "Июнь", "Сентябрь", "Ноябрь"]:
        month_days = 30  # 30 дней для этих месяцев

    # Создаем кнопки для выбора дня
    keyboard = [[InlineKeyboardButton(str(day), callback_data=str(day))] for day in range(1, month_days + 1)]

    await query.answer()

    await query.edit_message_text(
        f"Вы выбрали {selected_month}. Теперь выберите день.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def select_day(update: Update, context: CallbackContext):
    query = update.callback_query
    selected_day = int(query.data)
    context.user_data['day'] = selected_day

    await query.answer()

    # Просим ввести время для напоминания
    await query.edit_message_text(
        f"Вы выбрали {selected_day} {context.user_data['month']} {context.user_data['year']}. "
        "Теперь укажите время для напоминания (формат HH:MM)."
    )

if __name__ == "__main__":
    setup_database()
    upgrade_database()
    TOKEN = "7822734698:AAHcuNnEP0zXfs_3i7o4FJoIP3lcbLzUMFI"
    
    # Использование Application в версии 20 и выше
    application = Application.builder().token(TOKEN).build()

    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu_registration", menu_registration))
    application.add_handler(CommandHandler("user", user_menu))
    application.add_handler(CommandHandler("add_mail", add_mail))
    application.add_handler(CommandHandler("delete_mail", delete_mail))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    application.add_handler(CommandHandler("news_post", news_post))
    application.add_handler(CommandHandler("web", web))
    application.add_handler(CommandHandler("college_info", college_info))
    application.add_handler(CommandHandler("specials", specials))
    application.add_handler(CommandHandler("abitur", abitur))
    application.add_handler(CommandHandler("contacts", contacts))
    application.add_handler(CommandHandler("schedule", schedule))
    application.add_handler(CommandHandler("shedule_tom", shedule_tom))
    application.add_handler(CommandHandler("shedule_year", shedule_year))
    application.add_handler(CommandHandler("shedule_section", shedule_section))
    application.add_handler(CommandHandler("information_rules", information_rules))
    application.add_handler(CommandHandler("faq", faq))

    # Запуск бота
    application.run_polling()