"""
База данных для системы управления кафе
Включает: ингредиенты, блюда, техкарты, расходы, продажи, клиенты, завтраки
"""

import sqlite3
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import secrets


@dataclass
class Ingredient:
    """Ингредиент"""
    id: Optional[int]
    name: str
    unit: str  # единица измерения (кг, литр, шт)
    price_per_unit: float  # цена за единицу
    supplier: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class Dish:
    """Блюдо в меню"""
    id: Optional[int]
    name: str
    price: float  # цена продажи
    category: str  # категория (напитки, десерты, основные блюда и т.д.)
    description: Optional[str] = None


@dataclass
class RecipeItem:
    """Элемент техкарты (ингредиент в блюде)"""
    id: Optional[int]
    dish_id: int
    ingredient_id: int
    quantity: float  # количество ингредиента
    ingredient_name: Optional[str] = None  # для удобства при выборке


@dataclass
class Expense:
    """Расход"""
    id: Optional[int]
    date: str
    category: str  # аренда, зарплата, коммунальные, продукты, прочее
    amount: float
    description: Optional[str] = None


@dataclass
class Sale:
    """Продажа/чеки"""
    id: Optional[int]
    date: str
    dish_id: int
    quantity: int  # количество проданных порций
    total_amount: float  # общая сумма
    dish_name: Optional[str] = None  # для удобства при выборке


@dataclass
class Client:
    """Клиент кафе"""
    id: Optional[int]
    name: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    barcode: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    history_token: Optional[str] = None


@dataclass
class BreakfastVisit:
    """Посещение завтрака клиентом"""
    id: Optional[int]
    client_id: int
    date: str
    is_free: bool = False  # бесплатный (7-й в месяце)
    client_name: Optional[str] = None


@dataclass
class BarcodeEvent:
    """Событие по баркоду клиента"""
    id: Optional[int]
    client_id: int
    event_type: str
    event_date: str
    details: Optional[str] = None


class CafeDatabase:
    """Класс для работы с базой данных кафе"""

    def __init__(self, db_path: str = "cafe_data.sqlite3"):
        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Получить соединение с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Инициализация базы данных - создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Ингредиенты
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                unit TEXT NOT NULL,
                price_per_unit REAL NOT NULL,
                supplier TEXT,
                notes TEXT
            )
        """)

        # Блюда
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dishes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT
            )
        """)

        # Техкарты (рецепты)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recipe_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dish_id INTEGER NOT NULL,
                ingredient_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
                FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
                UNIQUE(dish_id, ingredient_id)
            )
        """)

        # Расходы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT
            )
        """)

        # Продажи
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                dish_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                FOREIGN KEY (dish_id) REFERENCES dishes(id)
            )
        """)

        # Клиенты
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                notes TEXT,
                barcode TEXT
            )
        """)

        # Посещения завтрака
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS breakfast_visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                is_free INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        # Журнал событий по баркодам (отправка, сканирование и т.д.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS barcode_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
            )
        """)

        conn.commit()
        self._ensure_clients_barcode(conn)
        self._ensure_clients_telegram_fields(conn)
        conn.close()

    def _ensure_clients_barcode(self, conn):
        """Добавить/проверить поле barcode у клиентов и заполнить пропуски."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(clients)")
        columns = {row["name"] for row in cursor.fetchall()}

        if "barcode" not in columns:
            cursor.execute("ALTER TABLE clients ADD COLUMN barcode TEXT")

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_barcode
            ON clients(barcode)
        """)

        cursor.execute("SELECT id, barcode FROM clients")
        rows = cursor.fetchall()
        for row in rows:
            client_id = row["id"]
            barcode = row["barcode"] or ""
            if not self._is_valid_ean13(barcode):
                cursor.execute(
                    "UPDATE clients SET barcode = ? WHERE id = ?",
                    (self._build_barcode(client_id), client_id)
                )

        conn.commit()

    def _ensure_clients_telegram_fields(self, conn):
        """Добавить служебные поля для Telegram и клиентской страницы."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(clients)")
        columns = {row["name"] for row in cursor.fetchall()}

        if "telegram_chat_id" not in columns:
            cursor.execute("ALTER TABLE clients ADD COLUMN telegram_chat_id TEXT")
        if "history_token" not in columns:
            cursor.execute("ALTER TABLE clients ADD COLUMN history_token TEXT")

        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_clients_history_token
            ON clients(history_token)
        """)

        cursor.execute("SELECT id, history_token FROM clients")
        for row in cursor.fetchall():
            if not row["history_token"]:
                cursor.execute(
                    "UPDATE clients SET history_token = ? WHERE id = ?",
                    (self._build_history_token(), row["id"])
                )

        conn.commit()

    def _build_barcode(self, client_id: int) -> str:
        """Сформировать стабильный уникальный EAN-13 баркод клиента."""
        base12 = f"290{client_id:09d}"
        checksum = self._ean13_checksum(base12)
        return f"{base12}{checksum}"

    def _build_history_token(self) -> str:
        """Сформировать уникальный токен для страницы клиента."""
        return secrets.token_urlsafe(18)

    def _ean13_checksum(self, base12: str) -> int:
        """Вычислить контрольную цифру EAN-13 для 12 цифр."""
        digits = [int(ch) for ch in base12]
        odd_sum = sum(digits[::2])
        even_sum = sum(digits[1::2])
        total = odd_sum + even_sum * 3
        return (10 - (total % 10)) % 10

    def _is_valid_ean13(self, code: str) -> bool:
        """Проверить корректность EAN-13."""
        if len(code) != 13 or not code.isdigit():
            return False
        return self._ean13_checksum(code[:12]) == int(code[-1])

    # ========== Ингредиенты ==========

    def add_ingredient(self, name: str, unit: str, price_per_unit: float,
                      supplier: Optional[str] = None, notes: Optional[str] = None) -> int:
        """Добавить ингредиент"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ingredients (name, unit, price_per_unit, supplier, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (name, unit, price_per_unit, supplier, notes))
        conn.commit()
        ingredient_id = cursor.lastrowid
        conn.close()
        return ingredient_id

    def get_ingredients(self) -> List[Ingredient]:
        """Получить все ингредиенты"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ingredients ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [Ingredient(id=r['id'], name=r['name'], unit=r['unit'],
                          price_per_unit=r['price_per_unit'], supplier=r['supplier'],
                          notes=r['notes']) for r in rows]

    def get_ingredient(self, ingredient_id: int) -> Optional[Ingredient]:
        """Получить ингредиент по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ingredients WHERE id = ?", (ingredient_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Ingredient(id=row['id'], name=row['name'], unit=row['unit'],
                            price_per_unit=row['price_per_unit'], supplier=row['supplier'],
                            notes=row['notes'])
        return None

    def update_ingredient(self, ingredient_id: int, name: str, unit: str,
                         price_per_unit: float, supplier: Optional[str] = None,
                         notes: Optional[str] = None):
        """Обновить ингредиент"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE ingredients
            SET name = ?, unit = ?, price_per_unit = ?, supplier = ?, notes = ?
            WHERE id = ?
        """, (name, unit, price_per_unit, supplier, notes, ingredient_id))
        conn.commit()
        conn.close()

    def delete_ingredient(self, ingredient_id: int):
        """Удалить ингредиент"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ingredients WHERE id = ?", (ingredient_id,))
        conn.commit()
        conn.close()

    # ========== Блюда ==========

    def add_dish(self, name: str, price: float, category: str,
                description: Optional[str] = None) -> int:
        """Добавить блюдо"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO dishes (name, price, category, description)
            VALUES (?, ?, ?, ?)
        """, (name, price, category, description))
        conn.commit()
        dish_id = cursor.lastrowid
        conn.close()
        return dish_id

    def get_dishes(self) -> List[Dish]:
        """Получить все блюда"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dishes ORDER BY category, name")
        rows = cursor.fetchall()
        conn.close()
        return [Dish(id=r['id'], name=r['name'], price=r['price'],
                    category=r['category'], description=r['description']) for r in rows]

    def get_dish(self, dish_id: int) -> Optional[Dish]:
        """Получить блюдо по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM dishes WHERE id = ?", (dish_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Dish(id=row['id'], name=row['name'], price=row['price'],
                       category=row['category'], description=row['description'])
        return None

    def update_dish(self, dish_id: int, name: str, price: float,
                   category: str, description: Optional[str] = None):
        """Обновить блюдо"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE dishes
            SET name = ?, price = ?, category = ?, description = ?
            WHERE id = ?
        """, (name, price, category, description, dish_id))
        conn.commit()
        conn.close()

    def delete_dish(self, dish_id: int):
        """Удалить блюдо"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dishes WHERE id = ?", (dish_id,))
        conn.commit()
        conn.close()

    # ========== Техкарты (рецепты) ==========

    def add_recipe_item(self, dish_id: int, ingredient_id: int, quantity: float):
        """Добавить ингредиент в техкарту блюда"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO recipe_items (dish_id, ingredient_id, quantity)
            VALUES (?, ?, ?)
        """, (dish_id, ingredient_id, quantity))
        conn.commit()
        conn.close()

    def get_recipe(self, dish_id: int) -> List[RecipeItem]:
        """Получить техкарту блюда"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ri.*, i.name as ingredient_name
            FROM recipe_items ri
            JOIN ingredients i ON ri.ingredient_id = i.id
            WHERE ri.dish_id = ?
            ORDER BY i.name
        """, (dish_id,))
        rows = cursor.fetchall()
        conn.close()
        return [RecipeItem(id=r['id'], dish_id=r['dish_id'],
                          ingredient_id=r['ingredient_id'], quantity=r['quantity'],
                          ingredient_name=r['ingredient_name']) for r in rows]

    def delete_recipe_item(self, recipe_item_id: int):
        """Удалить элемент техкарты"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM recipe_items WHERE id = ?", (recipe_item_id,))
        conn.commit()
        conn.close()

    def calculate_dish_cost(self, dish_id: int) -> float:
        """Рассчитать себестоимость блюда на основе техкарты"""
        recipe = self.get_recipe(dish_id)
        total_cost = 0.0

        for item in recipe:
            ingredient = self.get_ingredient(item.ingredient_id)
            if ingredient:
                total_cost += ingredient.price_per_unit * item.quantity

        return round(total_cost, 2)

    def get_dish_margin(self, dish_id: int) -> Dict[str, float]:
        """Получить информацию о наценке блюда"""
        dish = self.get_dish(dish_id)
        if not dish:
            return {}

        cost = self.calculate_dish_cost(dish_id)
        margin_amount = dish.price - cost
        margin_percent = (margin_amount / dish.price * 100) if dish.price > 0 else 0
        markup_percent = (margin_amount / cost * 100) if cost > 0 else 0

        return {
            'cost': cost,
            'price': dish.price,
            'margin_amount': round(margin_amount, 2),
            'margin_percent': round(margin_percent, 2),
            'markup_percent': round(markup_percent, 2)
        }

    # ========== Расходы ==========

    def add_expense(self, date: str, category: str, amount: float,
                   description: Optional[str] = None) -> int:
        """Добавить расход"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (date, category, amount, description)
            VALUES (?, ?, ?, ?)
        """, (date, category, amount, description))
        conn.commit()
        expense_id = cursor.lastrowid
        conn.close()
        return expense_id

    def get_expenses(self, start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> List[Expense]:
        """Получить расходы за период"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute("""
                SELECT * FROM expenses
                WHERE date >= ? AND date <= ?
                ORDER BY date DESC
            """, (start_date, end_date))
        else:
            cursor.execute("SELECT * FROM expenses ORDER BY date DESC")

        rows = cursor.fetchall()
        conn.close()
        return [Expense(id=r['id'], date=r['date'], category=r['category'],
                       amount=r['amount'], description=r['description']) for r in rows]

    def get_expenses_by_category(self, start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> Dict[str, float]:
        """Получить расходы по категориям"""
        expenses = self.get_expenses(start_date, end_date)
        by_category = {}
        for expense in expenses:
            by_category[expense.category] = by_category.get(expense.category, 0) + expense.amount
        return by_category

    # ========== Продажи ==========

    def add_sale(self, date: str, dish_id: int, quantity: int, total_amount: float) -> int:
        """Добавить продажу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sales (date, dish_id, quantity, total_amount)
            VALUES (?, ?, ?, ?)
        """, (date, dish_id, quantity, total_amount))
        conn.commit()
        sale_id = cursor.lastrowid
        conn.close()
        return sale_id

    def get_sales(self, start_date: Optional[str] = None,
                 end_date: Optional[str] = None) -> List[Sale]:
        """Получить продажи за период"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if start_date and end_date:
            cursor.execute("""
                SELECT s.*, d.name as dish_name
                FROM sales s
                JOIN dishes d ON s.dish_id = d.id
                WHERE s.date >= ? AND s.date <= ?
                ORDER BY s.date DESC
            """, (start_date, end_date))
        else:
            cursor.execute("""
                SELECT s.*, d.name as dish_name
                FROM sales s
                JOIN dishes d ON s.dish_id = d.id
                ORDER BY s.date DESC
            """)

        rows = cursor.fetchall()
        conn.close()
        return [Sale(id=r['id'], date=r['date'], dish_id=r['dish_id'],
                    quantity=r['quantity'], total_amount=r['total_amount'],
                    dish_name=r['dish_name']) for r in rows]

    def get_revenue(self, start_date: Optional[str] = None,
                   end_date: Optional[str] = None) -> float:
        """Получить выручку за период"""
        sales = self.get_sales(start_date, end_date)
        return sum(sale.total_amount for sale in sales)

    def get_profit(self, start_date: Optional[str] = None,
                  end_date: Optional[str] = None) -> Dict[str, float]:
        """Рассчитать прибыль за период"""
        revenue = self.get_revenue(start_date, end_date)
        expenses = self.get_expenses(start_date, end_date)
        total_expenses = sum(expense.amount for expense in expenses)

        # Рассчитать себестоимость проданных блюд
        sales = self.get_sales(start_date, end_date)
        cost_of_goods_sold = 0.0
        for sale in sales:
            dish_cost = self.calculate_dish_cost(sale.dish_id)
            cost_of_goods_sold += dish_cost * sale.quantity

        gross_profit = revenue - cost_of_goods_sold
        net_profit = revenue - total_expenses - cost_of_goods_sold

        return {
            'revenue': round(revenue, 2),
            'cost_of_goods_sold': round(cost_of_goods_sold, 2),
            'gross_profit': round(gross_profit, 2),
            'total_expenses': round(total_expenses, 2),
            'net_profit': round(net_profit, 2)
        }

    # ========== Клиенты ==========

    def add_client(self, name: str, phone: Optional[str] = None,
                   notes: Optional[str] = None) -> int:
        """Добавить клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO clients (name, phone, notes, history_token)
            VALUES (?, ?, ?, ?)
        """, (name, phone, notes, self._build_history_token()))
        conn.commit()
        client_id = cursor.lastrowid
        barcode = self._build_barcode(client_id)
        cursor.execute("UPDATE clients SET barcode = ? WHERE id = ?", (barcode, client_id))
        conn.commit()
        conn.close()
        return client_id

    def get_clients(self) -> List[Client]:
        """Получить всех клиентов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients ORDER BY name")
        rows = cursor.fetchall()
        conn.close()
        return [Client(id=r['id'], name=r['name'], phone=r['phone'],
                       notes=r['notes'], barcode=r['barcode'],
                       telegram_chat_id=r['telegram_chat_id'],
                       history_token=r['history_token']) for r in rows]

    def get_client(self, client_id: int) -> Optional[Client]:
        """Получить клиента по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Client(id=row['id'], name=row['name'], phone=row['phone'],
                          notes=row['notes'], barcode=row['barcode'],
                          telegram_chat_id=row['telegram_chat_id'],
                          history_token=row['history_token'])
        return None

    def get_client_by_barcode(self, barcode: str) -> Optional[Client]:
        """Получить клиента по EAN-13 баркоду."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE barcode = ?", (barcode,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Client(id=row['id'], name=row['name'], phone=row['phone'],
                          notes=row['notes'], barcode=row['barcode'],
                          telegram_chat_id=row['telegram_chat_id'],
                          history_token=row['history_token'])
        return None

    def get_client_by_history_token(self, token: str) -> Optional[Client]:
        """Получить клиента по токену страницы истории."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE history_token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Client(id=row['id'], name=row['name'], phone=row['phone'],
                          notes=row['notes'], barcode=row['barcode'],
                          telegram_chat_id=row['telegram_chat_id'],
                          history_token=row['history_token'])
        return None

    def get_client_by_telegram_chat(self, chat_id: str) -> Optional[Client]:
        """Получить клиента по Telegram chat_id."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE telegram_chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Client(id=row['id'], name=row['name'], phone=row['phone'],
                          notes=row['notes'], barcode=row['barcode'],
                          telegram_chat_id=row['telegram_chat_id'],
                          history_token=row['history_token'])
        return None

    def find_unlinked_client_by_name(self, name: str) -> Optional[Client]:
        """Найти клиента по имени, который еще не привязан к Telegram."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM clients
            WHERE lower(name) = lower(?)
              AND (telegram_chat_id IS NULL OR telegram_chat_id = '')
            ORDER BY id DESC
            LIMIT 1
        """, (name,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return Client(id=row['id'], name=row['name'], phone=row['phone'],
                          notes=row['notes'], barcode=row['barcode'],
                          telegram_chat_id=row['telegram_chat_id'],
                          history_token=row['history_token'])
        return None

    def set_client_telegram_chat(self, client_id: int, chat_id: str):
        """Привязать Telegram chat_id к клиенту."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE clients SET telegram_chat_id = ? WHERE id = ?",
            (chat_id, client_id)
        )
        conn.commit()
        conn.close()

    def delete_client(self, client_id: int):
        """Удалить клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        conn.close()

    # ========== Завтраки ==========

    def get_breakfast_count_total(self, client_id: int) -> int:
        """Общее количество завтраков клиента за всё время."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as cnt FROM breakfast_visits
            WHERE client_id = ?
        """, (client_id,))
        row = cursor.fetchone()
        conn.close()
        return row['cnt'] if row else 0

    def add_breakfast_visit(self, client_id: int,
                            date: Optional[str] = None) -> Tuple[int, bool]:
        """
        Зарегистрировать завтрак клиента.
        Возвращает (id записи, is_free).
        Каждый 7-й завтрак за всё время — бесплатный (без сброса по месяцу).
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        total_count = self.get_breakfast_count_total(client_id)

        # Следующий завтрак будет (total_count + 1)-м
        next_number = total_count + 1
        is_free = (next_number % 7 == 0)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO breakfast_visits (client_id, date, is_free)
            VALUES (?, ?, ?)
        """, (client_id, date, int(is_free)))
        conn.commit()
        visit_id = cursor.lastrowid
        conn.close()
        return visit_id, is_free

    def get_breakfast_visits(self, client_id: Optional[int] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None) -> List[BreakfastVisit]:
        """Получить историю завтраков"""
        conn = self.get_connection()
        cursor = conn.cursor()

        query = """
            SELECT bv.*, c.name as client_name
            FROM breakfast_visits bv
            JOIN clients c ON bv.client_id = c.id
            WHERE 1=1
        """
        params = []

        if client_id is not None:
            query += " AND bv.client_id = ?"
            params.append(client_id)
        if start_date:
            query += " AND bv.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND bv.date <= ?"
            params.append(end_date)

        query += " ORDER BY bv.date DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [BreakfastVisit(id=r['id'], client_id=r['client_id'],
                               date=r['date'], is_free=bool(r['is_free']),
                               client_name=r['client_name']) for r in rows]

    def get_client_breakfast_stats(self, client_id: int) -> Dict:
        """Статистика завтраков клиента (непрерывная система 7-го бесплатного)."""
        count = self.get_breakfast_count_total(client_id)
        visits_until_free = 7 - (count % 7)
        if visits_until_free == 7 and count > 0:
            visits_until_free = 7
        return {
            'count_total': count,
            'count_this_month': count,  # оставлено для обратной совместимости шаблонов
            'visits_until_free': visits_until_free,
            'next_is_free': (count % 7 == 6),
        }

    # ========== Журнал баркодов ==========

    def log_barcode_event(self, client_id: int, event_type: str,
                          details: Optional[str] = None) -> int:
        """Записать событие баркода (отправлен, сканирован и т.д.)."""
        conn = self.get_connection()
        cursor = conn.cursor()
        event_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO barcode_events (client_id, event_type, event_date, details)
            VALUES (?, ?, ?, ?)
        """, (client_id, event_type, event_date, details))
        conn.commit()
        event_id = cursor.lastrowid
        conn.close()
        return event_id

    def get_client_barcode_events(self, client_id: int, limit: int = 100) -> List[BarcodeEvent]:
        """Получить историю событий по баркоду клиента."""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM barcode_events
            WHERE client_id = ?
            ORDER BY event_date DESC, id DESC
            LIMIT ?
        """, (client_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [BarcodeEvent(id=r['id'],
                             client_id=r['client_id'],
                             event_type=r['event_type'],
                             event_date=r['event_date'],
                             details=r['details']) for r in rows]
