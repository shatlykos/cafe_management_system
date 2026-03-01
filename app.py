"""
Веб-интерфейс для системы управления кафе GALAXY FOOD
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response
from datetime import datetime
from database import CafeDatabase
import os
import json
import ssl
import zlib
import struct
import urllib.parse
import urllib.request
import urllib.error
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, "templates"),
            static_folder=os.path.join(BASE_DIR, "static"))
app.secret_key = "galaxyfood2026"
app.config["TEMPLATES_AUTO_RELOAD"] = True

db = CafeDatabase(os.path.join(BASE_DIR, "cafe_data.sqlite3"))


def today():
    return datetime.now().strftime("%Y-%m-%d")


def build_public_url(path: str) -> str:
    base = request.url_root.rstrip("/")
    return f"{base}{path}"


def generate_barcode_svg(barcode_value: str) -> bytes:
    bits = build_ean13_bits(barcode_value)
    module = 2
    quiet = 10
    height = 96
    text_h = 18
    width = (len(bits) + quiet * 2) * module
    bars = []
    for i, bit in enumerate(bits):
        if bit == "1":
            x = (quiet + i) * module
            bars.append(f'<rect x="{x}" y="0" width="{module}" height="{height}" fill="#000"/>')

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height + text_h}" '
        f'viewBox="0 0 {width} {height + text_h}">'
        f'<rect width="{width}" height="{height + text_h}" fill="#fff"/>'
        f'{"".join(bars)}'
        f'<text x="{width / 2}" y="{height + 14}" font-family="monospace" font-size="14" '
        f'text-anchor="middle" fill="#000">{barcode_value}</text>'
        f'</svg>'
    )
    return svg.encode("utf-8")


def build_ean13_bits(barcode_value: str) -> str:
    l_codes = {
        "0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101", "4": "0100011",
        "5": "0110001", "6": "0101111", "7": "0111011", "8": "0110111", "9": "0001011"
    }
    g_codes = {
        "0": "0100111", "1": "0110011", "2": "0011011", "3": "0100001", "4": "0011101",
        "5": "0111001", "6": "0000101", "7": "0010001", "8": "0001001", "9": "0010111"
    }
    r_codes = {
        "0": "1110010", "1": "1100110", "2": "1101100", "3": "1000010", "4": "1011100",
        "5": "1001110", "6": "1010000", "7": "1000100", "8": "1001000", "9": "1110100"
    }
    parity = {
        "0": "LLLLLL", "1": "LLGLGG", "2": "LLGGLG", "3": "LLGGGL", "4": "LGLLGG",
        "5": "LGGLLG", "6": "LGGGLL", "7": "LGLGLG", "8": "LGLGGL", "9": "LGGLGL"
    }

    if len(barcode_value) != 13 or not barcode_value.isdigit():
        raise ValueError("EAN-13 должен содержать 13 цифр.")

    first = barcode_value[0]
    left_digits = barcode_value[1:7]
    right_digits = barcode_value[7:]
    pattern = parity[first]

    left_bits = ""
    for i, d in enumerate(left_digits):
        left_bits += l_codes[d] if pattern[i] == "L" else g_codes[d]
    right_bits = "".join(r_codes[d] for d in right_digits)
    return f"101{left_bits}01010{right_bits}101"


def generate_barcode_png(barcode_value: str) -> bytes:
    bits = build_ean13_bits(barcode_value)
    module = 4
    quiet = 12
    width = (len(bits) + quiet * 2) * module
    height = 220
    bar_top = 12
    bar_height = 180

    rows = []
    for y in range(height):
        row = bytearray([0])
        in_bar_y = bar_top <= y < (bar_top + bar_height)
        for x in range(width):
            module_x = x // module - quiet
            is_black = in_bar_y and 0 <= module_x < len(bits) and bits[module_x] == "1"
            color = 0 if is_black else 255
            row.extend((color, color, color))
        rows.append(bytes(row))
    raw = b"".join(rows)
    compressed = zlib.compress(raw, level=9)

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack("!I", len(data)) + chunk_type + data + struct.pack("!I", crc)

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"".join([
        signature,
        png_chunk(b"IHDR", ihdr),
        png_chunk(b"IDAT", compressed),
        png_chunk(b"IEND", b""),
    ])


def telegram_open(req: urllib.request.Request) -> str:
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.URLError as exc:
        err_text = str(exc.reason) if getattr(exc, "reason", None) else str(exc)
        if "CERTIFICATE_VERIFY_FAILED" not in err_text:
            raise
        insecure_ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=10, context=insecure_ctx) as resp:
            return resp.read().decode("utf-8")


def telegram_request(method: str, payload: dict) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан.")
    url = f"https://api.telegram.org/bot{token}/{method}"
    body = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body)
    data = telegram_open(req)
    parsed = json.loads(data)
    if not parsed.get("ok"):
        raise RuntimeError(parsed.get("description", "Ошибка Telegram API"))
    return parsed


def telegram_send_photo(chat_id: str, filename: str, image_bytes: bytes, caption: str = ""):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN не задан.")
    boundary = "----codexboundary" + os.urandom(8).hex()
    parts = []

    def add_field(name: str, value: str):
        parts.append(f"--{boundary}\r\n".encode("utf-8"))
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        parts.append(value.encode("utf-8"))
        parts.append(b"\r\n")

    add_field("chat_id", chat_id)
    if caption:
        add_field("caption", caption)

    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode("utf-8")
    )
    parts.append(b"Content-Type: image/png\r\n\r\n")
    parts.append(image_bytes)
    parts.append(b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    data = telegram_open(req)
    parsed = json.loads(data)
    if not parsed.get("ok"):
        raise RuntimeError(parsed.get("description", "Ошибка Telegram API"))


def send_client_card_to_telegram(client, chat_id: str):
    history_path = url_for("client_portal", token=client.history_token)
    history_url = build_public_url(history_path)
    png_bytes = generate_barcode_png(client.barcode)
    text = (
        f"Ваш штрихкод: `{client.barcode}`\n"
        f"История и статус: {history_url}\n"
        "Покажите этот штрихкод в кафе при визите."
    )
    telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })
    telegram_send_photo(
        chat_id,
        f"barcode_{client.id}.png",
        png_bytes,
        f"Ваш штрихкод: {client.barcode}"
    )


def send_client_menu(chat_id: str):
    telegram_request("sendMessage", {
        "chat_id": chat_id,
        "text": "Выберите действие:",
        "reply_markup": json.dumps({
            "keyboard": [
                ["Мой баркод", "Моя история"],
                ["Мой завтрак", "Мой кофе"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False,
            "input_field_placeholder": "Нажмите кнопку меню"
        })
    })


# ─────────────────────────────────────────────
# Главная
# ─────────────────────────────────────────────

@app.route("/")
def index():
    clients = db.get_clients()
    breakfasts_today = db.get_breakfast_visits(start_date=today(), end_date=today())
    coffees_today = db.get_coffee_visits(start_date=today(), end_date=today())
    return render_template("index.html",
                           breakfasts_today=len(breakfasts_today),
                           coffees_today=len(coffees_today),
                           clients_count=len(clients),
                           today=today())


# ─────────────────────────────────────────────
# Завтраки
# ─────────────────────────────────────────────

@app.route("/breakfasts")
def breakfasts():
    clients = db.get_clients()
    client_data = []
    for c in clients:
        stats = db.get_client_breakfast_stats(c.id)
        client_data.append({"client": c, "stats": stats})
    return render_template("breakfasts.html", client_data=client_data, today=today())


@app.route("/breakfasts/register", methods=["POST"])
def register_breakfast():
    client_id = int(request.form["client_id"])
    date = request.form.get("date") or today()
    client = db.get_client(client_id)
    _, is_free = db.add_breakfast_visit(client_id, date)
    if is_free:
        flash(f"🎉 Поздравляем! 7-й завтрак {client.name} за 30 дней — БЕСПЛАТНО!", "success")
    else:
        stats = db.get_client_breakfast_stats(client_id)
        if stats["next_is_free"]:
            flash(f"Завтрак записан. Следующий завтрак {client.name} за 30 дней будет БЕСПЛАТНЫМ!", "warning")
        else:
            flash(f"Завтрак записан. До бесплатного (30 дней) осталось: {stats['visits_until_free']}.", "info")
    return redirect(url_for("breakfasts"))


@app.route("/breakfasts/scan", methods=["POST"])
def scan_breakfast_by_barcode():
    barcode_value = (request.form.get("barcode") or "").strip()
    date = request.form.get("date") or today()
    if not barcode_value:
        flash("Введите штрихкод для сканирования.", "danger")
        return redirect(url_for("breakfasts"))
    client = db.get_client_by_barcode(barcode_value)
    if not client:
        flash(f"Клиент с кодом {barcode_value} не найден.", "danger")
        return redirect(url_for("breakfasts"))
    _, is_free = db.add_breakfast_visit(client.id, date)
    db.log_barcode_event(client.id, "scanned", f"Завтрак зарегистрирован за {date}")
    if is_free:
        flash(f"Сканирование OK: {client.name}. Это бесплатный завтрак.", "success")
    else:
        flash(f"Сканирование OK: {client.name}. Завтрак записан.", "success")
    return redirect(url_for("breakfasts"))


@app.route("/breakfasts/history/<int:client_id>")
def breakfast_history(client_id):
    client = db.get_client(client_id)
    if not client:
        flash("Клиент не найден.", "danger")
        return redirect(url_for("breakfasts"))
    visits = db.get_breakfast_visits(client_id=client_id)
    stats = db.get_client_breakfast_stats(client_id)
    events = db.get_client_barcode_events(client_id=client_id, limit=100)
    return render_template("breakfast_history.html", client=client, visits=visits, stats=stats, events=events)


# ─────────────────────────────────────────────
# Кофе
# ─────────────────────────────────────────────

@app.route("/coffee")
def coffee():
    clients = db.get_clients()
    client_data = []
    for c in clients:
        stats = db.get_client_coffee_stats(c.id)
        client_data.append({"client": c, "stats": stats})
    return render_template("coffee.html", client_data=client_data, today=today())


@app.route("/coffee/register", methods=["POST"])
def register_coffee():
    client_id = int(request.form["client_id"])
    date = request.form.get("date") or today()
    client = db.get_client(client_id)
    _, is_free = db.add_coffee_visit(client_id, date)
    if is_free:
        flash(f"🎉 Поздравляем! 7-й кофе {client.name} за 30 дней — БЕСПЛАТНО!", "success")
    else:
        stats = db.get_client_coffee_stats(client_id)
        if stats["next_is_free"]:
            flash(f"Кофе записан. Следующий кофе {client.name} за 30 дней будет БЕСПЛАТНЫМ!", "warning")
        else:
            flash(f"Кофе записан. До бесплатного (30 дней) осталось: {stats['visits_until_free']}.", "info")
    return redirect(url_for("coffee"))


@app.route("/coffee/scan", methods=["POST"])
def scan_coffee_by_barcode():
    barcode_value = (request.form.get("barcode") or "").strip()
    date = request.form.get("date") or today()
    if not barcode_value:
        flash("Введите штрихкод для сканирования.", "danger")
        return redirect(url_for("coffee"))
    client = db.get_client_by_barcode(barcode_value)
    if not client:
        flash(f"Клиент с кодом {barcode_value} не найден.", "danger")
        return redirect(url_for("coffee"))
    _, is_free = db.add_coffee_visit(client.id, date)
    db.log_barcode_event(client.id, "coffee_scanned", f"Кофе зарегистрирован за {date}")
    if is_free:
        flash(f"Сканирование OK: {client.name}. Это бесплатный кофе.", "success")
    else:
        flash(f"Сканирование OK: {client.name}. Кофе записан.", "success")
    return redirect(url_for("coffee"))


@app.route("/coffee/history/<int:client_id>")
def coffee_history(client_id):
    client = db.get_client(client_id)
    if not client:
        flash("Клиент не найден.", "danger")
        return redirect(url_for("coffee"))
    visits = db.get_coffee_visits(client_id=client_id)
    stats = db.get_client_coffee_stats(client_id)
    events = db.get_client_barcode_events(client_id=client_id, limit=100)
    return render_template("coffee_history.html", client=client, visits=visits, stats=stats, events=events)


@app.route("/clients/add", methods=["POST"])
def add_client():
    name = request.form["name"].strip()
    phone_local = (request.form.get("phone_local") or "").strip()
    phone_digits = "".join(ch for ch in phone_local if ch.isdigit())
    phone = f"+995{phone_digits}" if phone_digits else None
    notes = request.form.get("notes", "").strip() or None
    if not name:
        flash("Введите имя клиента.", "danger")
        return redirect(url_for("breakfasts"))
    client_id = db.add_client(name, phone, notes)
    client = db.get_client(client_id)
    flash(f"Клиент «{name}» добавлен. Баркод: {client.barcode}", "success")
    return_to = (request.form.get("return_to") or "").strip()
    if return_to == "index":
        return redirect(url_for("index"))
    return redirect(url_for("breakfasts"))


@app.route("/clients/search", methods=["POST"])
def search_client_by_barcode():
    barcode_value = (request.form.get("barcode") or "").strip()
    return_to = (request.form.get("return_to") or "").strip()
    fallback = url_for("index") if return_to == "index" else url_for("breakfasts")
    if not barcode_value:
        flash("Введите штрихкод для поиска.", "danger")
        return redirect(fallback)
    client = db.get_client_by_barcode(barcode_value)
    if not client:
        flash(f"Клиент с кодом {barcode_value} не найден.", "warning")
        return redirect(fallback)
    return redirect(url_for("breakfast_history", client_id=client.id))


@app.route("/clients/send-barcode/<int:client_id>", methods=["POST"])
def send_barcode_to_client_bot(client_id):
    client = db.get_client(client_id)
    if not client:
        flash("Клиент не найден.", "danger")
        return redirect(url_for("breakfasts"))
    chat_id = (request.form.get("telegram_chat_id") or client.telegram_chat_id or "").strip()
    if not chat_id:
        flash("Укажите Telegram chat_id клиента.", "danger")
        return redirect(url_for("breakfasts"))
    db.set_client_telegram_chat(client_id, chat_id)
    client = db.get_client(client_id)
    try:
        send_client_card_to_telegram(client, chat_id)
        db.log_barcode_event(client_id, "sent_to_bot", f"chat_id={chat_id}")
        flash(f"Штрихкод клиента «{client.name}» отправлен в Telegram.", "success")
    except Exception as exc:
        flash(f"Ошибка отправки в Telegram: {exc}", "danger")
    return redirect(url_for("breakfasts"))


@app.route("/clients/<int:client_id>/barcode.svg")
def client_barcode_svg(client_id):
    client = db.get_client(client_id)
    if not client or not client.barcode:
        return Response("Client not found", status=404)
    svg_bytes = generate_barcode_svg(client.barcode)
    return Response(svg_bytes, mimetype="image/svg+xml")


@app.route("/client/history/<token>")
def client_portal(token):
    client = db.get_client_by_history_token(token)
    if not client:
        return render_template("client_portal.html", client=None, visits=[], stats=None, coffee_visits=[], coffee_stats=None, events=[]), 404
    visits = db.get_breakfast_visits(client_id=client.id)
    stats = db.get_client_breakfast_stats(client.id)
    coffee_visits = db.get_coffee_visits(client_id=client.id)
    coffee_stats = db.get_client_coffee_stats(client.id)
    events = db.get_client_barcode_events(client_id=client.id, limit=100)
    return render_template("client_portal.html",
                           client=client,
                           visits=visits,
                           stats=stats,
                           coffee_visits=coffee_visits,
                           coffee_stats=coffee_stats,
                           events=events)


@app.route("/telegram/webhook", methods=["POST"])
def telegram_webhook():
    try:
        payload = request.get_json(silent=True) or {}
        message = payload.get("message") or {}
        chat = message.get("chat") or {}
        text = (message.get("text") or "").strip()
        chat_id = str(chat.get("id", "")).strip()
        if not chat_id:
            return jsonify({"ok": True})

        if text.lower().startswith("/start"):
            existing = db.get_client_by_telegram_chat(chat_id)
            if existing:
                send_client_card_to_telegram(existing, chat_id)
                send_client_menu(chat_id)
                return jsonify({"ok": True})

            first_name = (message.get("from") or {}).get("first_name", "").strip()
            username = (message.get("from") or {}).get("username", "").strip()
            if first_name:
                client_name = first_name
            elif username:
                client_name = f"@{username}"
            else:
                client_name = f"Клиент {chat_id}"

            candidate = db.find_unlinked_client_by_name(client_name)
            if candidate:
                db.set_client_telegram_chat(candidate.id, chat_id)
                client = db.get_client(candidate.id)
                db.log_barcode_event(candidate.id, "bot_linked", f"matched_by_name chat_id={chat_id}")
            else:
                client_id = db.add_client(client_name, phone=None, notes="Создан через Telegram /start")
                db.set_client_telegram_chat(client_id, chat_id)
                client = db.get_client(client_id)
                db.log_barcode_event(client_id, "bot_linked", f"auto chat_id={chat_id}")
            send_client_card_to_telegram(client, chat_id)
            telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": "Готово. Ваш профиль создан автоматически."
            })
            send_client_menu(chat_id)
            return jsonify({"ok": True})

        existing = db.get_client_by_telegram_chat(chat_id)
        if existing:
            text_l = text.lower()
            if text_l in {"/menu", "меню"}:
                send_client_menu(chat_id)
                return jsonify({"ok": True})
            if text_l in {"мой баркод", "баркод", "/barcode"}:
                send_client_card_to_telegram(existing, chat_id)
                send_client_menu(chat_id)
                return jsonify({"ok": True})
            if text_l in {"моя история", "история", "/history"}:
                history_url = build_public_url(url_for("client_portal", token=existing.history_token))
                telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": f"Ваша история: {history_url}"
                })
                send_client_menu(chat_id)
                return jsonify({"ok": True})
            if text_l in {"мой завтрак", "/breakfast"}:
                stats = db.get_client_breakfast_stats(existing.id)
                telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": (
                        f"Завтрак: цикл {stats['cycle_step']}/7 за 30 дней.\n"
                        f"До бесплатного: {stats['visits_until_free']}."
                    )
                })
                send_client_menu(chat_id)
                return jsonify({"ok": True})
            if text_l in {"мой кофе", "/coffee"}:
                stats = db.get_client_coffee_stats(existing.id)
                telegram_request("sendMessage", {
                    "chat_id": chat_id,
                    "text": (
                        f"Кофе: цикл {stats['cycle_step']}/7 за 30 дней.\n"
                        f"До бесплатного: {stats['visits_until_free']}."
                    )
                })
                send_client_menu(chat_id)
                return jsonify({"ok": True})

            history_url = build_public_url(url_for("client_portal", token=existing.history_token))
            telegram_request("sendMessage", {
                "chat_id": chat_id,
                "text": f"Ваш клиентский профиль: {history_url}\nКоманда: /start — прислать штрихкод снова."
            })
            send_client_menu(chat_id)
            return jsonify({"ok": True})

        telegram_request("sendMessage", {
            "chat_id": chat_id,
            "text": "Нажмите /start для автоматической регистрации и получения штрихкода."
        })
    except Exception:
        app.logger.error("Telegram webhook handler failed")
        app.logger.error(traceback.format_exc())
        # Telegram ожидает быстрый 200-ответ, чтобы не зациклить повторные delivery.
        return jsonify({"ok": True})
    return jsonify({"ok": True})


@app.route("/clients/delete/<int:client_id>", methods=["POST"])
def delete_client(client_id):
    client = db.get_client(client_id)
    if client:
        db.delete_client(client_id)
        flash(f"Клиент «{client.name}» удалён.", "info")
    return redirect(url_for("breakfasts"))


# ─────────────────────────────────────────────
# Продажи
# ─────────────────────────────────────────────

@app.route("/sales")
def sales():
    dishes = db.get_dishes()
    start = request.args.get("start") or today()
    end = request.args.get("end") or today()
    sales_list = db.get_sales(start, end)
    total = sum(s.total_amount for s in sales_list)
    return render_template("sales.html", dishes=dishes, sales=sales_list,
                           total=total, start=start, end=end)


@app.route("/sales/add", methods=["POST"])
def add_sale():
    dish_id = int(request.form["dish_id"])
    quantity = int(request.form["quantity"])
    date = request.form.get("date") or today()
    dish = db.get_dish(dish_id)
    if not dish:
        flash("Блюдо не найдено.", "danger")
        return redirect(url_for("sales"))
    total = dish.price * quantity
    db.add_sale(date, dish_id, quantity, total)
    flash(f"Продажа «{dish.name}» x{quantity} записана. Сумма: {total:.0f}", "success")
    return redirect(url_for("sales"))


# ─────────────────────────────────────────────
# Блюда
# ─────────────────────────────────────────────

@app.route("/dishes")
def dishes():
    dishes_list = db.get_dishes()
    dish_data = []
    for d in dishes_list:
        margin = db.get_dish_margin(d.id)
        dish_data.append({"dish": d, "margin": margin})
    return render_template("dishes.html", dish_data=dish_data)


@app.route("/dishes/add", methods=["POST"])
def add_dish():
    name = request.form["name"].strip()
    price = float(request.form["price"])
    category = request.form["category"].strip()
    description = request.form.get("description", "").strip() or None
    db.add_dish(name, price, category, description)
    flash(f"Блюдо «{name}» добавлено.", "success")
    return redirect(url_for("dishes"))


@app.route("/dishes/delete/<int:dish_id>", methods=["POST"])
def delete_dish(dish_id):
    dish = db.get_dish(dish_id)
    if dish:
        db.delete_dish(dish_id)
        flash(f"Блюдо «{dish.name}» удалено.", "info")
    return redirect(url_for("dishes"))


# ─────────────────────────────────────────────
# Расходы
# ─────────────────────────────────────────────

@app.route("/expenses")
def expenses():
    start = request.args.get("start") or datetime.now().strftime("%Y-%m-01")
    end = request.args.get("end") or today()
    expenses_list = db.get_expenses(start, end)
    by_cat = db.get_expenses_by_category(start, end)
    total = sum(e.amount for e in expenses_list)
    return render_template("expenses.html", expenses=expenses_list,
                           by_cat=by_cat, total=total, start=start, end=end)


@app.route("/expenses/add", methods=["POST"])
def add_expense():
    date = request.form.get("date") or today()
    category = request.form["category"].strip()
    amount = float(request.form["amount"])
    description = request.form.get("description", "").strip() or None
    db.add_expense(date, category, amount, description)
    flash(f"Расход «{category}» {amount:.0f} записан.", "success")
    return redirect(url_for("expenses"))


# ─────────────────────────────────────────────
# Отчёт
# ─────────────────────────────────────────────

@app.route("/report")
def report():
    start = request.args.get("start") or datetime.now().strftime("%Y-%m-01")
    end = request.args.get("end") or today()
    profit = db.get_profit(start, end)
    return render_template("report.html", profit=profit, start=start, end=end)


if __name__ == "__main__":
    app.run(
        debug=False,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080"))
    )
