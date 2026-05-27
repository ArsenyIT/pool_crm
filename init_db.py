# init_db.py (ПОЛНАЯ ВЕРСИЯ с bcrypt)
import sqlite3
import os
import bcrypt
from database import db_instance, get_db_cursor, DATABASE_PATH
from datetime import datetime, time, date, timedelta

# Словарь для хранения созданных паролей (для отладки и тестирования)
created_credentials = {
    "admins": [],
    "trainers": [],
    "parents": []
}


def hash_password(password: str) -> str:
    """Хеширует пароль с помощью bcrypt"""
    if not password:
        password = "default123"
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет соответствие пароля хешу"""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception:
        return False


def print_credentials():
    """Выводит все созданные учётные данные для тестирования"""
    print("\n" + "=" * 60)
    print("🔐 TEST CREDENTIALS (сохраните для тестирования)")
    print("=" * 60)

    # 👑 АДМИНИСТРАТОР (один)
    if created_credentials["admins"]:
        print("\n👑 АДМИНИСТРАТОР (полный доступ ко всем данным):")
        for a in created_credentials["admins"]:
            print(f"   • {a['full_name']}: {a['login']} / {a['password']}")

    if created_credentials["trainers"]:
        print("\n👨‍🏫 ТРЕНЕРЫ (логин / пароль):")
        for t in created_credentials["trainers"]:
            print(f"   • {t['full_name']}: {t['login']} / {t['password']}")

    if created_credentials["parents"]:
        print("\n👨‍👩‍👧 РОДИТЕЛИ (телефон для входа, пароль = телефон):")
        for p in created_credentials["parents"]:
            print(f"   • {p['full_name']}: {p['phone']} / {p['phone']}")

    print("\n" + "=" * 60)
    print("💡 Для входа родителям нужен ТОЛЬКО телефон и пароль (по умолчанию = телефон)")
    print("💡 Тренерам нужны логин И пароль")
    print("=" * 60 + "\n")


def table_exists(cursor, table_name):
    """Проверяет, существует ли таблица в базе данных SQLite"""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def create_tables():
    """Создание всех таблиц согласно схеме"""
    with get_db_cursor() as cursor:
        # 1. Таблица родителей (parents)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parents ( 
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL UNIQUE,
                email VARCHAR(255),
                vk_id VARCHAR(100) UNIQUE,
                password_hash VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Таблица детей (children)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS children (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                age INTEGER CHECK (age BETWEEN 3 AND 17),
                class_number INTEGER CHECK (class_number BETWEEN 0 AND 11 OR class_number IS NULL),
                school_name VARCHAR(255),
                swimming_years INTEGER DEFAULT 1,
                shift VARCHAR(10) CHECK (shift IN ('day', 'evening')),
                desired_lessons_per_week INTEGER CHECK (desired_lessons_per_week IN (1,2,3)),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES parents(id) ON DELETE CASCADE
            )
        """)

        # 3. Таблица тренеров (trainers)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trainers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(255),
                login VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                specialization TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. Таблица групп (groups)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                trainer_id INTEGER,
                min_age INTEGER DEFAULT 3,
                max_age INTEGER DEFAULT 17,
                swimming_year INTEGER DEFAULT 1,
                max_students INTEGER DEFAULT 15,
                shift VARCHAR(10) CHECK (shift IN ('day', 'evening')),
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (trainer_id) REFERENCES trainers(id) ON DELETE SET NULL
            )
        """)

        # 5. Таблица зачислений (enrollments)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                child_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                UNIQUE(child_id, group_id),
                FOREIGN KEY (child_id) REFERENCES children(id),
                FOREIGN KEY (group_id) REFERENCES groups(id)
            )
        """)

        # 6. Таблица расписания (schedule)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                weekday INTEGER CHECK (weekday BETWEEN 0 AND 6),
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                location VARCHAR(100),
                is_recurring BOOLEAN DEFAULT 1,
                single_date DATE,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)

        # 7. Таблица посещаемости(attendance)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                enrollment_id INTEGER NOT NULL,
                date DATE NOT NULL,
                status VARCHAR(20) CHECK (status IN ('present', 'absent', 'sick', 'excused')),
                mark_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE,
                UNIQUE(enrollment_id, date)
            )
        """)

        # 8. Таблица заявок (applications)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_full_name VARCHAR(255) NOT NULL,
                parent_phone VARCHAR(20) NOT NULL,
                parent_email VARCHAR(255),
                child_full_name VARCHAR(255) NOT NULL,
                child_age INTEGER NOT NULL,
                child_class INTEGER,
                school_name VARCHAR(255),
                swimming_years INTEGER DEFAULT 1,
                shift VARCHAR(10) CHECK (shift IN ('day', 'evening')),
                desired_lessons_per_week INTEGER,
                status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'processing', 'approved', 'rejected')),
                rejection_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                processed_by INTEGER,
                FOREIGN KEY (processed_by) REFERENCES trainers(id)
            )
        """)

        # 9. Таблица администраторов (admins)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name VARCHAR(255) NOT NULL,
                login VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 10. Таблица логов администратора (admin_logs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action VARCHAR(255) NOT NULL,
                entity_type VARCHAR(50),
                entity_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
            )
        """)

        # 11. Таблица уведомлений (notifications)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_type VARCHAR(20) CHECK (user_type IN ('parent', 'trainer')),
                type VARCHAR(50) CHECK (type IN ('email', 'sms', 'vk', 'system')),
                title VARCHAR(255),
                message TEXT,
                status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed')),
                sent_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Создание индексов для производительности
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_children_parent ON children(parent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_child ON enrollments(child_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enrollments_group ON enrollments(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_enrollment ON attendance(enrollment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_applications_phone ON applications(parent_phone)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_schedule_group ON schedule(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_groups_trainer ON groups(trainer_id)")

        print("✅ All tables created successfully")


def ensure_tables_exist():
    """Проверяет существование таблиц и создаёт их при необходимости"""
    with get_db_cursor() as cursor:
        if not table_exists(cursor, 'trainers'):
            print("📋 Tables not found, creating them first...")
            create_tables()
            return True
    return False


def seed_test_data():
    """Заполнение тестовыми данными для разработки"""
    global created_credentials
    created_credentials = {
        "admins": [],
        "trainers": [],
        "parents": []
    }

    ensure_tables_exist()

    with get_db_cursor() as cursor:
        # Проверяем, есть ли уже данные
        try:
            cursor.execute("SELECT COUNT(*) FROM trainers")
            count = cursor.fetchone()[0]
            if count > 0:
                print("📊 Test data already exists, skipping seed")
                print_credentials()
                return
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print("❌ Tables still don't exist, cannot seed data")
                print("   Please run 'create_tables()' first or use 'reset_database()'")
                return
            raise e

        print("🌱 Seeding test data...")

        # 1. Создаём тренеров (trainers)
        trainers_data = [
            ("Анна Иванова", "+79001234567", "anna@swim.ru", "anna.trainer", "anna123",
             "Детское плавание, начальная подготовка"),
            ("Михаил Петров", "+79007654321", "mikhail@swim.ru", "mikhail.trainer", "mikhail123",
             "Спортивное плавание, старшие группы"),
            ("Елена Смирнова", "+79009998877", "elena@swim.ru", "elena.trainer", "elena123",
             "Оздоровительное плавание, малыши"),
        ]

        trainers_list = []
        for trainer in trainers_data:
            created_credentials["trainers"].append({
                "full_name": trainer[0],
                "login": trainer[3],
                "password": trainer[4]
            })
            password_hash = hash_password(trainer[4])
            trainers_list.append((
                trainer[0], trainer[1], trainer[2],
                trainer[3], password_hash, trainer[5]
            ))

        cursor.executemany("""
            INSERT INTO trainers (full_name, phone, email, login, password_hash, specialization)
            VALUES (?, ?, ?, ?, ?, ?)
        """, trainers_list)

        # 2. Создаём группы (groups)
        groups_data = [
            ("Дельфинчики (3-5 лет)", 1, 3, 5, 1, 10, "day"),
            ("Рыбки (6-8 лет)", 1, 6, 8, 1, 12, "day"),
            ("Спортивная (9-12 лет)", 2, 9, 12, 2, 15, "evening"),
            ("Продвинутая (13-17 лет)", 2, 13, 17, 3, 15, "evening"),
            ("Оздоровительная (7-10 лет)", 3, 7, 10, 1, 12, "day"),
        ]

        cursor.executemany("""
            INSERT INTO groups (name, trainer_id, min_age, max_age, swimming_year, max_students, shift)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, groups_data)

        # 3. Создаём родителей (parents) с хешированным паролем (пароль = телефон)
        parents_data = [
            ("Сергей Петров", "+79123456789", "sergey@example.com", None),
            ("Ольга Сидорова", "+79234567890", "olga@example.com", None),
            ("Дмитрий Козлов", "+79345678901", "dmitry@example.com", None),
        ]

        for parent in parents_data:
            created_credentials["parents"].append({
                "full_name": parent[0],
                "phone": parent[1]
            })
            password_hash = hash_password(parent[1])  # пароль = телефон
            cursor.execute("""
                INSERT INTO parents (full_name, phone, email, vk_id, password_hash)
                VALUES (?, ?, ?, ?, ?)
            """, (parent[0], parent[1], parent[2], parent[3], password_hash))

        # 4. Создаём детей (children)
        children_data = [
            (1, "Алексей Петров", 7, 1, "Школа №1", 1, "day", 2),
            (1, "Мария Петрова", 5, 0, "Детский сад №5", 1, "day", 2),
            (2, "Екатерина Сидорова", 10, 3, "Школа №2", 2, "evening", 3),
            (3, "Иван Козлов", 14, 7, "Школа №3", 3, "evening", 2),
        ]

        cursor.executemany("""
            INSERT INTO children (parent_id, full_name, age, class_number, school_name, swimming_years, shift, desired_lessons_per_week)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, children_data)

        # 5. Зачисляем детей в группы (enrollments)
        enrollments_data = [
            (1, 2),  # Алексей Петров -> Рыбки
            (2, 1),  # Мария Петрова -> Дельфинчики
            (3, 3),  # Екатерина Сидорова -> Спортивная
            (4, 4),  # Иван Козлов -> Продвинутая
        ]

        cursor.executemany("""
            INSERT INTO enrollments (child_id, group_id)
            VALUES (?, ?)
        """, enrollments_data)

        # 6. Добавляем расписание (schedule)
        schedule_data = [
            (1, 0, "10:00", "11:00", "Дорожка 1", 1, None),
            (1, 2, "10:00", "11:00", "Дорожка 1", 1, None),
            (2, 0, "11:30", "12:30", "Дорожка 2", 1, None),
            (2, 3, "11:30", "12:30", "Дорожка 2", 1, None),
            (3, 1, "18:00", "19:30", "Дорожка 3", 1, None),
            (3, 4, "18:00", "19:30", "Дорожка 3", 1, None),
            (4, 1, "19:30", "21:00", "Дорожка 4", 1, None),
            (4, 4, "19:30", "21:00", "Дорожка 4", 1, None),
            (5, 0, "15:00", "16:00", "Дорожка 1", 1, None),
            (5, 3, "15:00", "16:00", "Дорожка 1", 1, None),
        ]

        cursor.executemany("""
            INSERT INTO schedule (group_id, weekday, start_time, end_time, location, is_recurring, single_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, schedule_data)

        # 7. Добавляем посещаемость за последнюю неделю (attendance)
        attendance_data = []
        today = date.today()
        enrollments_ids = [(1, 2), (2, 1), (3, 3), (4, 4)]

        for i, enrollment in enumerate(enrollments_ids, start=1):
            enrollment_id = i
            for days_ago in [1, 3, 5]:
                d = today - timedelta(days=days_ago)
                status = "present" if days_ago != 5 else "absent"
                attendance_data.append((enrollment_id, d.isoformat(), status))

        cursor.executemany("""
            INSERT INTO attendance (enrollment_id, date, status)
            VALUES (?, ?, ?)
        """, attendance_data)

        # 8. Добавляем тестовые заявки (applications)
        applications_data = [
            ("Нина Соколова", "+79991112233", "nina@example.com", "Артём Соколов", 8, 2, "Школа №4", 1, "day", 2, "new",
             None, None, None),
            (
            "Виктор Морозов", "+79885556677", None, "Дарья Морозова", 6, 0, "Школа №5", 1, "day", 2, "processing", None,
            None, None),
        ]

        cursor.executemany("""
            INSERT INTO applications (parent_full_name, parent_phone, parent_email, child_full_name, child_age, child_class, school_name, swimming_years, shift, desired_lessons_per_week, status, rejection_reason, processed_at, processed_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, applications_data)

        # 9. Создаём администратора
        admins_list = [
            ("Администратор", "admin", "admin123", "admin@swim.ru", "+79001112233")
        ]

        for admin in admins_list:
            created_credentials["admins"].append({
                "full_name": admin[0],
                "login": admin[1],
                "password": admin[2]
            })
            password_hash = hash_password(admin[2])
            cursor.execute("""
                INSERT INTO admins (full_name, login, password_hash, email, phone)
                VALUES (?, ?, ?, ?, ?)
            """, (admin[0], admin[1], password_hash, admin[3], admin[4]))

        print("✅ Test data seeded successfully")
        print(f"📊 Statistics:")
        print(f"   - Trainers: {cursor.execute('SELECT COUNT(*) FROM trainers').fetchone()[0]}")
        print(f"   - Groups: {cursor.execute('SELECT COUNT(*) FROM groups').fetchone()[0]}")
        print(f"   - Parents: {cursor.execute('SELECT COUNT(*) FROM parents').fetchone()[0]}")
        print(f"   - Children: {cursor.execute('SELECT COUNT(*) FROM children').fetchone()[0]}")
        print(f"   - Enrollments: {cursor.execute('SELECT COUNT(*) FROM enrollments').fetchone()[0]}")

        print_credentials()


def drop_all_tables():
    """Удаляет ВСЕ таблицы из базы данных"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = cursor.fetchall()

        if not tables:
            print("ℹ️ No tables found to drop")
            return

        cursor.execute("PRAGMA foreign_keys = OFF")
        for table in tables:
            table_name = table[0]
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            print(f"   Dropped table: {table_name}")
        cursor.execute("PRAGMA foreign_keys = ON")

    print(f"✅ Dropped {len(tables)} tables successfully")


def reset_database():
    """Удаляет все таблицы и создаёт их заново с тестовыми данными"""
    print("🔄 Starting database reset...")
    drop_all_tables()
    create_tables()
    seed_test_data()
    print("✅ Database reset completed successfully!")


def recreate_database():
    """Полностью пересоздаёт базу данных"""
    import os
    from database import db_instance, DATABASE_PATH

    print("🔄 Recreating database from scratch...")
    db_instance.close()

    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)
        print(f"🗑️ Removed database file: {DATABASE_PATH}")

    create_tables()
    seed_test_data()
    print("✅ Database recreated from scratch!")


def show_tables():
    """Показать список всех таблиц в базе данных"""
    with get_db_cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = cursor.fetchall()

        if not tables:
            print("ℹ️ No tables found")
            return

        print("\n📋 Tables in database:")
        print("-" * 30)
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"   {table[0]}: {count} records")
        print("-" * 30)


def get_database_info():
    """Получить подробную информацию о базе данных"""
    import os
    from database import DATABASE_PATH

    print("\n📊 Database Information:")
    print("=" * 40)

    if os.path.exists(DATABASE_PATH):
        size = os.path.getsize(DATABASE_PATH)
        print(f"📁 File: {DATABASE_PATH}")
        print(f"💾 Size: {size} bytes ({size / 1024:.2f} KB)")
    else:
        print(f"❌ Database file not found: {DATABASE_PATH}")
        return

    show_tables()
    print(f"\n🔧 SQLite version: {sqlite3.sqlite_version}")
    print("=" * 40)


def create_full_database():
    """Создаёт полную базу данных с таблицами и тестовыми данными"""
    print("🚀 Creating full database...")
    create_tables()
    seed_test_data()
    print("✅ Full database created successfully!")


# Если запускаем файл напрямую
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("\n📚 Database Management Script")
        print("=" * 40)
        print("Usage:")
        print("  python init_db.py create     - Create tables")
        print("  python init_db.py seed       - Seed test data (auto-creates tables if needed)")
        print("  python init_db.py reset      - Reset database (drop + create + seed)")
        print("  python init_db.py drop       - Drop all tables")
        print("  python init_db.py recreate   - Recreate database from scratch")
        print("  python init_db.py show       - Show all tables")
        print("  python init_db.py info       - Show database information")
        print("  python init_db.py full       - Create full database (tables + data)")
        print("=" * 40)
        sys.exit(0)

    command = sys.argv[1]

    if command == "create":
        create_tables()
    elif command == "seed":
        seed_test_data()
    elif command == "reset":
        reset_database()
    elif command == "drop":
        drop_all_tables()
    elif command == "recreate":
        recreate_database()
    elif command == "show":
        show_tables()
    elif command == "info":
        get_database_info()
    elif command == "full":
        create_full_database()
    else:
        print(f"❌ Unknown command: {command}")
        print("Use: create, seed, reset, drop, recreate, show, info, full")