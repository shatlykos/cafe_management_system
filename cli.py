"""
CLI интерфейс для системы управления кафе
"""

import sys
from datetime import datetime
from typing import Optional
from database import CafeDatabase
from excel_export import ExcelExporter


class CafeCLI:
    """Командная строка для управления кафе"""

    def __init__(self, db_path: str = "cafe_data.sqlite3"):
        self.db = CafeDatabase(db_path)
        self.exporter = ExcelExporter(self.db)

    def print_menu(self):
        """Вывести главное меню"""
        print("\n" + "="*50)
        print("  СИСТЕМА УПРАВЛЕНИЯ КАФЕ")
        print("="*50)
        print("1.  Управление ингредиентами")
        print("2.  Управление блюдами")
        print("3.  Техкарты")
        print("4.  Расчет себестоимости и наценки")
        print("5.  Управление расходами")
        print("6.  Продажи")
        print("7.  Финансовая отчетность")
        print("8.  Экспорт в Excel")
        print("9.  Завтраки (программа лояльности)")
        print("0.  Выход")
        print("="*50)

    def run(self):
        """Запустить CLI"""
        while True:
            self.print_menu()
            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                print("До свидания!")
                break
            elif choice == "1":
                self.manage_ingredients()
            elif choice == "2":
                self.manage_dishes()
            elif choice == "3":
                self.manage_recipes()
            elif choice == "4":
                self.view_costs_and_margins()
            elif choice == "5":
                self.manage_expenses()
            elif choice == "6":
                self.manage_sales()
            elif choice == "7":
                self.view_financial_report()
            elif choice == "8":
                self.export_to_excel()
            elif choice == "9":
                self.manage_breakfasts()
            else:
                print("Неверный выбор. Попробуйте снова.")

    def manage_ingredients(self):
        """Управление ингредиентами"""
        while True:
            print("\n--- Управление ингредиентами ---")
            print("1. Список ингредиентов")
            print("2. Добавить ингредиент")
            print("3. Редактировать ингредиент")
            print("4. Удалить ингредиент")
            print("0. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                ingredients = self.db.get_ingredients()
                if not ingredients:
                    print("Ингредиентов пока нет.")
                else:
                    print(f"\n{'ID':<5} {'Название':<20} {'Ед.':<10} {'Цена':<15} {'Поставщик'}")
                    print("-" * 70)
                    for ing in ingredients:
                        print(f"{ing.id:<5} {ing.name:<20} {ing.unit:<10} {ing.price_per_unit:<15.2f} {ing.supplier or ''}")
            elif choice == "2":
                name = input("Название ингредиента: ").strip()
                unit = input("Единица измерения (кг, литр, шт и т.д.): ").strip()
                try:
                    price = float(input("Цена за единицу: ").strip())
                    supplier = input("Поставщик (необязательно): ").strip() or None
                    notes = input("Примечания (необязательно): ").strip() or None

                    self.db.add_ingredient(name, unit, price, supplier, notes)
                    print("Ингредиент добавлен!")
                except ValueError:
                    print("Ошибка: неверный формат цены")
            elif choice == "3":
                try:
                    ing_id = int(input("ID ингредиента для редактирования: ").strip())
                    ingredient = self.db.get_ingredient(ing_id)
                    if not ingredient:
                        print("Ингредиент не найден.")
                        continue

                    name = input(f"Название [{ingredient.name}]: ").strip() or ingredient.name
                    unit = input(f"Единица [{ingredient.unit}]: ").strip() or ingredient.unit
                    try:
                        price = input(f"Цена [{ingredient.price_per_unit}]: ").strip()
                        price = float(price) if price else ingredient.price_per_unit
                        supplier = input(f"Поставщик [{ingredient.supplier or ''}]: ").strip() or ingredient.supplier
                        notes = input(f"Примечания [{ingredient.notes or ''}]: ").strip() or ingredient.notes

                        self.db.update_ingredient(ing_id, name, unit, price, supplier, notes)
                        print("Ингредиент обновлен!")
                    except ValueError:
                        print("Ошибка: неверный формат цены")
                except ValueError:
                    print("Ошибка: неверный формат ID")
            elif choice == "4":
                try:
                    ing_id = int(input("ID ингредиента для удаления: ").strip())
                    self.db.delete_ingredient(ing_id)
                    print("Ингредиент удален!")
                except ValueError:
                    print("Ошибка: неверный формат ID")

    def manage_dishes(self):
        """Управление блюдами"""
        while True:
            print("\n--- Управление блюдами ---")
            print("1. Список блюд")
            print("2. Добавить блюдо")
            print("3. Редактировать блюдо")
            print("4. Удалить блюдо")
            print("0. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                dishes = self.db.get_dishes()
                if not dishes:
                    print("Блюд пока нет.")
                else:
                    print(f"\n{'ID':<5} {'Название':<25} {'Категория':<20} {'Цена':<10}")
                    print("-" * 70)
                    for dish in dishes:
                        print(f"{dish.id:<5} {dish.name:<25} {dish.category:<20} {dish.price:<10.2f}")
            elif choice == "2":
                name = input("Название блюда: ").strip()
                try:
                    price = float(input("Цена продажи: ").strip())
                    category = input("Категория (напитки, десерты, основные и т.д.): ").strip()
                    description = input("Описание (необязательно): ").strip() or None

                    self.db.add_dish(name, price, category, description)
                    print("Блюдо добавлено!")
                except ValueError:
                    print("Ошибка: неверный формат цены")
            elif choice == "3":
                try:
                    dish_id = int(input("ID блюда для редактирования: ").strip())
                    dish = self.db.get_dish(dish_id)
                    if not dish:
                        print("Блюдо не найдено.")
                        continue

                    name = input(f"Название [{dish.name}]: ").strip() or dish.name
                    try:
                        price = input(f"Цена [{dish.price}]: ").strip()
                        price = float(price) if price else dish.price
                        category = input(f"Категория [{dish.category}]: ").strip() or dish.category
                        description = input(f"Описание [{dish.description or ''}]: ").strip() or dish.description

                        self.db.update_dish(dish_id, name, price, category, description)
                        print("Блюдо обновлено!")
                    except ValueError:
                        print("Ошибка: неверный формат цены")
                except ValueError:
                    print("Ошибка: неверный формат ID")
            elif choice == "4":
                try:
                    dish_id = int(input("ID блюда для удаления: ").strip())
                    self.db.delete_dish(dish_id)
                    print("Блюдо удалено!")
                except ValueError:
                    print("Ошибка: неверный формат ID")

    def manage_recipes(self):
        """Управление техкартами"""
        while True:
            print("\n--- Управление техкартами ---")
            print("1. Просмотр техкарты блюда")
            print("2. Добавить ингредиент в техкарту")
            print("3. Удалить ингредиент из техкарты")
            print("0. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                dishes = self.db.get_dishes()
                if not dishes:
                    print("Блюд пока нет.")
                    continue

                print("\nСписок блюд:")
                for dish in dishes:
                    print(f"{dish.id}. {dish.name}")

                try:
                    dish_id = int(input("\nID блюда: ").strip())
                    dish = self.db.get_dish(dish_id)
                    if not dish:
                        print("Блюдо не найдено.")
                        continue

                    recipe = self.db.get_recipe(dish_id)
                    if not recipe:
                        print(f"\nТехкарта для '{dish.name}' пуста.")
                    else:
                        print(f"\nТехкарта: {dish.name}")
                        print(f"{'Ингредиент':<25} {'Количество':<15} {'Ед.':<10} {'Цена/ед.':<15} {'Сумма':<15}")
                        print("-" * 80)
                        total = 0
                        for item in recipe:
                            ingredient = self.db.get_ingredient(item.ingredient_id)
                            if ingredient:
                                item_cost = ingredient.price_per_unit * item.quantity
                                total += item_cost
                                print(f"{ingredient.name:<25} {item.quantity:<15} {ingredient.unit:<10} "
                                     f"{ingredient.price_per_unit:<15.2f} {item_cost:<15.2f}")
                        print("-" * 80)
                        print(f"{'Себестоимость:':<55} {total:.2f}")
                except ValueError:
                    print("Ошибка: неверный формат ID")
            elif choice == "2":
                dishes = self.db.get_dishes()
                ingredients = self.db.get_ingredients()

                if not dishes or not ingredients:
                    print("Нужны блюда и ингредиенты.")
                    continue

                print("\nСписок блюд:")
                for dish in dishes:
                    print(f"{dish.id}. {dish.name}")

                print("\nСписок ингредиентов:")
                for ing in ingredients:
                    print(f"{ing.id}. {ing.name} ({ing.unit})")

                try:
                    dish_id = int(input("\nID блюда: ").strip())
                    ingredient_id = int(input("ID ингредиента: ").strip())
                    quantity = float(input("Количество: ").strip())

                    self.db.add_recipe_item(dish_id, ingredient_id, quantity)
                    print("Ингредиент добавлен в техкарту!")
                except ValueError:
                    print("Ошибка: неверный формат данных")
            elif choice == "3":
                try:
                    dish_id = int(input("ID блюда: ").strip())
                    recipe = self.db.get_recipe(dish_id)
                    if not recipe:
                        print("Техкарта пуста.")
                        continue

                    print("\nИнгредиенты в техкарте:")
                    for item in recipe:
                        print(f"{item.id}. {item.ingredient_name} - {item.quantity}")

                    recipe_item_id = int(input("\nID элемента для удаления: ").strip())
                    self.db.delete_recipe_item(recipe_item_id)
                    print("Ингредиент удален из техкарты!")
                except ValueError:
                    print("Ошибка: неверный формат ID")

    def view_costs_and_margins(self):
        """Просмотр себестоимости и наценки"""
        dishes = self.db.get_dishes()
        if not dishes:
            print("Блюд пока нет.")
            return

        print("\n--- Себестоимость и наценка ---")
        print(f"{'Блюдо':<25} {'Цена':<12} {'Себестоимость':<15} {'Прибыль':<12} {'Наценка %':<12} {'Маржа %':<12}")
        print("-" * 90)

        for dish in dishes:
            margin_info = self.db.get_dish_margin(dish.id)
            print(f"{dish.name:<25} {margin_info['price']:<12.2f} {margin_info['cost']:<15.2f} "
                 f"{margin_info['margin_amount']:<12.2f} {margin_info['markup_percent']:<12.1f} "
                 f"{margin_info['margin_percent']:<12.1f}")

        input("\nНажмите Enter для продолжения...")

    def manage_expenses(self):
        """Управление расходами"""
        while True:
            print("\n--- Управление расходами ---")
            print("1. Список расходов")
            print("2. Добавить расход")
            print("3. Расходы по категориям")
            print("0. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                start_date = input("Начальная дата (YYYY-MM-DD, необязательно): ").strip() or None
                end_date = input("Конечная дата (YYYY-MM-DD, необязательно): ").strip() or None

                expenses = self.db.get_expenses(start_date, end_date)
                if not expenses:
                    print("Расходов нет.")
                else:
                    print(f"\n{'ID':<5} {'Дата':<12} {'Категория':<20} {'Сумма':<15} {'Описание'}")
                    print("-" * 80)
                    for exp in expenses:
                        print(f"{exp.id:<5} {exp.date:<12} {exp.category:<20} {exp.amount:<15.2f} {exp.description or ''}")
            elif choice == "2":
                date = input("Дата (YYYY-MM-DD) [сегодня]: ").strip() or datetime.now().strftime("%Y-%m-%d")
                category = input("Категория (аренда, зарплата, коммунальные, продукты, прочее): ").strip()
                try:
                    amount = float(input("Сумма: ").strip())
                    description = input("Описание (необязательно): ").strip() or None

                    self.db.add_expense(date, category, amount, description)
                    print("Расход добавлен!")
                except ValueError:
                    print("Ошибка: неверный формат суммы")
            elif choice == "3":
                start_date = input("Начальная дата (YYYY-MM-DD, необязательно): ").strip() or None
                end_date = input("Конечная дата (YYYY-MM-DD, необязательно): ").strip() or None

                by_category = self.db.get_expenses_by_category(start_date, end_date)
                if not by_category:
                    print("Расходов нет.")
                else:
                    print("\nРасходы по категориям:")
                    print(f"{'Категория':<25} {'Сумма':<15}")
                    print("-" * 40)
                    total = 0
                    for category, amount in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                        print(f"{category:<25} {amount:<15.2f}")
                        total += amount
                    print("-" * 40)
                    print(f"{'ИТОГО':<25} {total:<15.2f}")

    def manage_sales(self):
        """Управление продажами"""
        while True:
            print("\n--- Управление продажами ---")
            print("1. Список продаж")
            print("2. Добавить продажу")
            print("0. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                start_date = input("Начальная дата (YYYY-MM-DD, необязательно): ").strip() or None
                end_date = input("Конечная дата (YYYY-MM-DD, необязательно): ").strip() or None

                sales = self.db.get_sales(start_date, end_date)
                if not sales:
                    print("Продаж нет.")
                else:
                    print(f"\n{'ID':<5} {'Дата':<12} {'Блюдо':<25} {'Количество':<12} {'Сумма':<15}")
                    print("-" * 75)
                    total = 0
                    for sale in sales:
                        print(f"{sale.id:<5} {sale.date:<12} {sale.dish_name:<25} {sale.quantity:<12} {sale.total_amount:<15.2f}")
                        total += sale.total_amount
                    print("-" * 75)
                    print(f"{'ИТОГО':<42} {total:<15.2f}")
            elif choice == "2":
                dishes = self.db.get_dishes()
                if not dishes:
                    print("Блюд пока нет.")
                    continue

                print("\nСписок блюд:")
                for dish in dishes:
                    print(f"{dish.id}. {dish.name} - {dish.price:.2f}")

                date = input("\nДата (YYYY-MM-DD) [сегодня]: ").strip() or datetime.now().strftime("%Y-%m-%d")
                try:
                    dish_id = int(input("ID блюда: ").strip())
                    quantity = int(input("Количество порций: ").strip())

                    dish = self.db.get_dish(dish_id)
                    if not dish:
                        print("Блюдо не найдено.")
                        continue

                    total_amount = dish.price * quantity
                    self.db.add_sale(date, dish_id, quantity, total_amount)
                    print(f"Продажа добавлена! Сумма: {total_amount:.2f}")
                except ValueError:
                    print("Ошибка: неверный формат данных")

    def view_financial_report(self):
        """Просмотр финансового отчета"""
        start_date = input("Начальная дата (YYYY-MM-DD, необязательно): ").strip() or None
        end_date = input("Конечная дата (YYYY-MM-DD, необязательно): ").strip() or None

        profit_data = self.db.get_profit(start_date, end_date)

        print("\n--- Финансовый отчет ---")
        if start_date and end_date:
            print(f"Период: {start_date} - {end_date}")
        else:
            print("За весь период")

        print(f"\nВыручка:                          {profit_data['revenue']:>15.2f}")
        print(f"Себестоимость проданных товаров:   {profit_data['cost_of_goods_sold']:>15.2f}")
        print(f"Валовая прибыль:                   {profit_data['gross_profit']:>15.2f}")
        print(f"Расходы:                           {profit_data['total_expenses']:>15.2f}")
        print(f"Чистая прибыль:                    {profit_data['net_profit']:>15.2f}")

        input("\nНажмите Enter для продолжения...")

    def export_to_excel(self):
        """Экспорт в Excel"""
        print("\n--- Экспорт в Excel ---")
        print("1. Меню с себестоимостью")
        print("2. Техкарты")
        print("3. Финансовый отчет")
        print("0. Назад")

        choice = input("\nВыберите вариант экспорта: ").strip()

        if choice == "1":
            filename = input("Имя файла [cafe_menu.xlsx]: ").strip() or "cafe_menu.xlsx"
            try:
                self.exporter.export_menu_with_costs(filename)
                print(f"Файл сохранен: {filename}")
            except ImportError as e:
                print(f"Ошибка: {e}")
            except Exception as e:
                print(f"Ошибка при экспорте: {e}")
        elif choice == "2":
            filename = input("Имя файла [tech_cards.xlsx]: ").strip() or "tech_cards.xlsx"
            try:
                self.exporter.export_tech_cards(filename)
                print(f"Файл сохранен: {filename}")
            except ImportError as e:
                print(f"Ошибка: {e}")
            except Exception as e:
                print(f"Ошибка при экспорте: {e}")
        elif choice == "3":
            start_date = input("Начальная дата (YYYY-MM-DD, необязательно): ").strip() or None
            end_date = input("Конечная дата (YYYY-MM-DD, необязательно): ").strip() or None
            filename = input("Имя файла [financial_report.xlsx]: ").strip() or "financial_report.xlsx"
            try:
                self.exporter.export_financial_report(start_date, end_date, filename)
                print(f"Файл сохранен: {filename}")
            except ImportError as e:
                print(f"Ошибка: {e}")
            except Exception as e:
                print(f"Ошибка при экспорте: {e}")


    def manage_breakfasts(self):
        """Управление завтраками и клиентами (программа лояльности)"""
        while True:
            print("\n--- Завтраки: программа лояльности ---")
            print("Правило: каждый 7-й завтрак в течение месяца — БЕСПЛАТНО")
            print()
            print("1. Список клиентов")
            print("2. Добавить клиента")
            print("3. Удалить клиента")
            print("4. Зарегистрировать завтрак клиента")
            print("5. История завтраков клиента")
            print("6. Статистика клиента за текущий месяц")
            print("0. Назад")

            choice = input("\nВыберите действие: ").strip()

            if choice == "0":
                break
            elif choice == "1":
                clients = self.db.get_clients()
                if not clients:
                    print("Клиентов пока нет.")
                else:
                    print(f"\n{'ID':<5} {'Имя':<25} {'Баркод':<16} {'Телефон':<18} {'Примечания'}")
                    print("-" * 90)
                    for c in clients:
                        print(f"{c.id:<5} {c.name:<25} {c.barcode or '':<16} {c.phone or '':<18} {c.notes or ''}")
            elif choice == "2":
                name = input("Имя клиента: ").strip()
                if not name:
                    print("Имя не может быть пустым.")
                    continue
                phone = input("Телефон (необязательно): ").strip() or None
                notes = input("Примечания (необязательно): ").strip() or None
                client_id = self.db.add_client(name, phone, notes)
                client = self.db.get_client(client_id)
                print(f"Клиент добавлен! ID: {client_id}, баркод: {client.barcode}")
            elif choice == "3":
                try:
                    client_id = int(input("ID клиента для удаления: ").strip())
                    client = self.db.get_client(client_id)
                    if not client:
                        print("Клиент не найден.")
                        continue
                    confirm = input(f"Удалить '{client.name}' и все его завтраки? (да/нет): ").strip().lower()
                    if confirm in ("да", "y", "yes"):
                        self.db.delete_client(client_id)
                        print("Клиент удален.")
                    else:
                        print("Отменено.")
                except ValueError:
                    print("Ошибка: неверный формат ID")
            elif choice == "4":
                clients = self.db.get_clients()
                if not clients:
                    print("Сначала добавьте клиента.")
                    continue
                print("\nСписок клиентов:")
                for c in clients:
                    stats = self.db.get_client_breakfast_stats(c.id)
                    free_mark = " ← СЛЕДУЮЩИЙ БЕСПЛАТНЫЙ!" if stats['next_is_free'] else ""
                    print(f"  {c.id}. {c.name}  (в этом месяце: {stats['count_this_month']}, "
                          f"до бесплатного: {stats['visits_until_free']}){free_mark}")
                try:
                    client_id = int(input("\nID клиента: ").strip())
                    client = self.db.get_client(client_id)
                    if not client:
                        print("Клиент не найден.")
                        continue
                    date = input("Дата (YYYY-MM-DD) [сегодня]: ").strip() or None
                    visit_id, is_free = self.db.add_breakfast_visit(client_id, date)
                    if is_free:
                        print(f"\n*** ПОЗДРАВЛЯЕМ! Это 7-й завтрак {client.name} в этом месяце — БЕСПЛАТНО! ***")
                    else:
                        stats = self.db.get_client_breakfast_stats(client_id)
                        print(f"\nЗавтрак зарегистрирован! В этом месяце: {stats['count_this_month']}.")
                        if stats['next_is_free']:
                            print(">>> Следующий завтрак будет БЕСПЛАТНЫМ! <<<")
                        else:
                            print(f"До бесплатного завтрака осталось: {stats['visits_until_free']}.")
                except ValueError:
                    print("Ошибка: неверный формат данных")
            elif choice == "5":
                clients = self.db.get_clients()
                if not clients:
                    print("Клиентов пока нет.")
                    continue
                print("\nСписок клиентов:")
                for c in clients:
                    print(f"  {c.id}. {c.name}")
                try:
                    client_id = int(input("\nID клиента: ").strip())
                    client = self.db.get_client(client_id)
                    if not client:
                        print("Клиент не найден.")
                        continue
                    visits = self.db.get_breakfast_visits(client_id=client_id)
                    if not visits:
                        print(f"У {client.name} пока нет завтраков.")
                    else:
                        print(f"\nИстория завтраков: {client.name}")
                        print(f"{'ID':<5} {'Дата':<14} {'Статус'}")
                        print("-" * 35)
                        for v in visits:
                            status = "БЕСПЛАТНО" if v.is_free else "Платный"
                            print(f"{v.id:<5} {v.date:<14} {status}")
                        total = len(visits)
                        free_count = sum(1 for v in visits if v.is_free)
                        print(f"\nВсего: {total}, из них бесплатных: {free_count}")
                except ValueError:
                    print("Ошибка: неверный формат ID")
            elif choice == "6":
                clients = self.db.get_clients()
                if not clients:
                    print("Клиентов пока нет.")
                    continue
                print("\nСписок клиентов:")
                for c in clients:
                    print(f"  {c.id}. {c.name}")
                try:
                    client_id = int(input("\nID клиента: ").strip())
                    client = self.db.get_client(client_id)
                    if not client:
                        print("Клиент не найден.")
                        continue
                    stats = self.db.get_client_breakfast_stats(client_id)
                    print(f"\n--- Статистика: {client.name} ---")
                    print(f"Завтраков в этом месяце:  {stats['count_this_month']}")
                    print(f"До бесплатного осталось:  {stats['visits_until_free']}")
                    if stats['next_is_free']:
                        print(">>> Следующий завтрак — БЕСПЛАТНЫЙ! <<<")
                except ValueError:
                    print("Ошибка: неверный формат ID")

            input("\nНажмите Enter для продолжения...")


def main():
    """Главная функция для запуска CLI"""
    try:
        cli = CafeCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nПрограмма завершена.")
    except Exception as e:
        print(f"\nОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()
