from typing import Final, Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import json
import os
from datetime import datetime

TOKEN: Final = "8493597534:AAHNuyfSW3SjUrtQmSNZyVTamzEnGlDUvbw"
BOT_USERNAME: Final = "@regiment_builder_bot"

# Функция для загрузки данных из JSON файлов
def load_faction_data():
    """Загружает данные о юнитах и их стоимости из JSON файлов"""
    faction_data = {}
    json_dir = "json/point army"
    
    # Маппинг названий фракций
    faction_mapping = {
        "space marines": "Space Marines",
        "orks": "Orks", 
        "eldar": "Eldar",
        "chaos space marines": "Chaos Space Marines",
        "tyranyds": "Tyranids"
    }
    
    try:
        for filename in os.listdir(json_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(json_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        
                    # Извлекаем данные из структуры JSON
                    for faction_key, faction_info in data.items():
                        if faction_key in faction_mapping:
                            mapped_faction = faction_mapping[faction_key]
                            faction_data[mapped_faction] = {
                                'name': faction_info.get('name', mapped_faction),
                                'description': faction_info.get('description', ''),
                                'units': []
                            }
                            
                            # Извлекаем юниты из bases
                            if 'bases' in faction_info:
                                for unit_data in faction_info['bases']:
                                    faction_data[mapped_faction]['units'].append({
                                        'name': unit_data['unit'],
                                        'points': unit_data['points'],
                                        'id': unit_data['id']
                                    })
                except Exception as e:
                    print(f"Ошибка при загрузке {filename}: {e}")
    except FileNotFoundError:
        print(f"Папка {json_dir} не найдена!")
    
    return faction_data

# Загружаем данные из JSON файлов
JSON_FACTION_DATA = load_faction_data()
print(f"Загружены фракции: {list(JSON_FACTION_DATA.keys())}")

# Структуры данных для Warhammer
class Unit:
    def __init__(self, name: str, points: int, category: str, faction: str, 
                 min_size: int = 1, max_size: int = 1, special_rules: List[str] = None):
        self.name = name
        self.points = points
        self.category = category  # HQ, Troops, Elites, Fast Attack, Heavy Support, Flyer, Transport
        self.faction = faction
        self.min_size = min_size
        self.max_size = max_size
        self.special_rules = special_rules or []

class ArmyUnit:
    def __init__(self, unit: Unit, count: int = 1):
        self.unit = unit
        self.count = count
    
    @property
    def total_points(self) -> int:
        return self.unit.points * self.count

class Army:
    def __init__(self, faction: str, max_points: int = 2000):
        self.faction = faction
        self.max_points = max_points
        self.units: List[ArmyUnit] = []
        # Базовые слоты для армии
        self.hq_slots = 1
        self.troop_slots = 2
        self.elite_slots = 3
        self.fast_attack_slots = 3
        self.heavy_support_slots = 3
        self.flyer_slots = 2
        self.transport_slots = 3
    
    @property
    def total_points(self) -> int:
        return sum(unit.total_points for unit in self.units)
    
    @property
    def remaining_points(self) -> int:
        return self.max_points - self.total_points
    
    def can_add_unit(self, unit: Unit, count: int = 1) -> tuple[bool, str]:
        # Проверка поинтов
        if unit.points * count > self.remaining_points:
            return False, f"Недостаточно поинтов. Нужно: {unit.points * count}, доступно: {self.remaining_points}"
        
        # Проверка размера юнита
        if count < unit.min_size:
            return False, f"Минимальный размер юнита: {unit.min_size}"
        if count > unit.max_size:
            return False, f"Максимальный размер юнита: {unit.max_size}"
        
        # Проверка слотов
        if unit.category == "HQ" and self.hq_slots <= 0:
            return False, "Нет доступных HQ слотов"
        elif unit.category == "Troops" and self.troop_slots <= 0:
            return False, "Нет доступных Troops слотов"
        elif unit.category == "Elites" and self.elite_slots <= 0:
            return False, "Нет доступных Elites слотов"
        elif unit.category == "Fast Attack" and self.fast_attack_slots <= 0:
            return False, "Нет доступных Fast Attack слотов"
        elif unit.category == "Heavy Support" and self.heavy_support_slots <= 0:
            return False, "Нет доступных Heavy Support слотов"
        elif unit.category == "Flyer" and self.flyer_slots <= 0:
            return False, "Нет доступных Flyer слотов"
        elif unit.category == "Transport" and self.transport_slots <= 0:
            return False, "Нет доступных Transport слотов"
        
        # Проверка правил армии
        validation_result = self._validate_army_rules(unit, count)
        if not validation_result[0]:
            return validation_result
        
        return True, "OK"
    
    def _validate_army_rules(self, unit: Unit, count: int) -> tuple[bool, str]:
        """Дополнительная валидация правил армии"""
        # Проверка минимальных требований для армии
        if not self.units:  # Если армия пуста
            if unit.category != "HQ":
                return False, "Армия должна начинаться с HQ юнита!"
        
        # Проверка на обязательные Troops (минимум 1 для большинства фракций)
        troops_count = sum(1 for army_unit in self.units if army_unit.unit.category == "Troops")
        if unit.category == "Elites" and troops_count == 0:
            return False, "Нужен минимум 1 Troops юнит перед добавлением Elites!"
        
        # Проверка на максимальное количество одинаковых юнитов (обычно 3)
        same_units = sum(1 for army_unit in self.units if army_unit.unit.name == unit.name)
        if same_units >= 3:
            return False, f"Максимум 3 одинаковых юнита в армии! Уже есть {same_units} {unit.name}"
        
        return True, "OK"
    
    def add_unit(self, unit: Unit, count: int = 1) -> tuple[bool, str]:
        can_add, message = self.can_add_unit(unit, count)
        if can_add:
            # Проверяем, есть ли уже такой юнит
            for army_unit in self.units:
                if army_unit.unit.name == unit.name:
                    army_unit.count += count
                    self._update_slots(unit.category, -1)
                    return True, f"Добавлено {count} {unit.name}. Всего: {army_unit.count}"
            
            # Добавляем новый юнит
            self.units.append(ArmyUnit(unit, count))
            self._update_slots(unit.category, -1)
            return True, f"Добавлено {count} {unit.name}"
        
        return False, message
    
    def _update_slots(self, category: str, change: int):
        if category == "HQ":
            self.hq_slots += change
        elif category == "Troops":
            self.troop_slots += change
        elif category == "Elites":
            self.elite_slots += change
        elif category == "Fast Attack":
            self.fast_attack_slots += change
        elif category == "Heavy Support":
            self.heavy_support_slots += change
        elif category == "Flyer":
            self.flyer_slots += change
        elif category == "Transport":
            self.transport_slots += change

# Функция для получения юнитов фракции из JSON данных
def get_faction_units(faction_name: str) -> List[Unit]:
    """Возвращает список юнитов для указанной фракции из JSON данных"""
    units = []
    
    if faction_name not in JSON_FACTION_DATA:
        return units
    
    faction_data = JSON_FACTION_DATA[faction_name]
    
    for unit_data in faction_data['units']:
        # Определяем категорию юнита на основе названия (базовая логика)
        category = "Troops"  # По умолчанию
        min_size = 1
        max_size = 1
        
        unit_name = unit_data['name'].lower()
        points = unit_data['points']
        
        # Простая логика определения категории по названию
        if any(word in unit_name for word in ['captain', 'lord', 'warboss', 'farseer', 'autarch', 'hive tyrant']):
            category = "HQ"
        elif any(word in unit_name for word in ['dreadnought', 'terminator', 'nobz', 'wraithguard', 'chosen', 'lictor', 'warrior', 'zoanthrope', 'venomthrope', 'malanthrope']):
            category = "Elites"
            if any(word in unit_name for word in ['terminator', 'warrior']):
                min_size = 3
                max_size = 10
            elif any(word in unit_name for word in ['gaunt', 'genestealer']):
                min_size = 5
                max_size = 20
        elif any(word in unit_name for word in ['squad', 'boyz', 'guardian', 'marines', 'termagant', 'hormagaunt', 'ripper swarm']):
            category = "Troops"
            if any(word in unit_name for word in ['squad', 'boyz', 'marines']):
                min_size = 5
                max_size = 10
            elif any(word in unit_name for word in ['guardian']):
                min_size = 10
                max_size = 20
            elif any(word in unit_name for word in ['gaunt', 'ripper']):
                min_size = 10
                max_size = 30
        elif any(word in unit_name for word in ['assault', 'stormboyz', 'swooping', 'raptors', 'gargoyle']):
            category = "Fast Attack"
            min_size = 5
            max_size = 10
        elif any(word in unit_name for word in ['devastator', 'predator', 'lootas', 'dark reapers', 'carnifex', 'trygon', 'mawloc', 'tyrannofex', 'exocrine', 'haruspex', 'biovore', 'hive guard']):
            category = "Heavy Support"
            if any(word in unit_name for word in ['squad']):
                min_size = 5
                max_size = 10
        
        # Создаем объект Unit
        unit = Unit(
            name=unit_data['name'],
            points=points,
            category=category,
            faction=faction_name,
            min_size=min_size,
            max_size=max_size
        )
        units.append(unit)
    
    return units

# Функция для получения всех доступных фракций
def get_available_factions() -> List[str]:
    """Возвращает список доступных фракций из JSON данных"""
    return list(JSON_FACTION_DATA.keys())

# Хранилище армий пользователей
user_armies: Dict[int, Army] = {}

# Функции для работы с данными пользователей
def load_users_data():
    """Загружает данные пользователей из JSON файла"""
    users_file = "json/create army/users_data.json"
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"users": {}}

def save_users_data(data):
    """Сохраняет данные пользователей в JSON файл"""
    users_file = "json/create army/users_data.json"
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_user_registered(user_id: int) -> bool:
    """Проверяет, зарегистрирован ли пользователь"""
    users_data = load_users_data()
    return str(user_id) in users_data["users"]

def register_user(user_id: int, username: str, player_type: str, contact: str = None):
    """Регистрирует нового пользователя"""
    users_data = load_users_data()
    users_data["users"][str(user_id)] = {
        "username": username,
        "player_type": player_type,
        "contact": contact,
        "registration_date": datetime.now().isoformat(),
        "armies": []
    }
    save_users_data(users_data)

def get_user_data(user_id: int):
    """Получает данные пользователя"""
    users_data = load_users_data()
    return users_data["users"].get(str(user_id))

def save_user_army(user_id: int, faction: str, points: int):
    """Сохраняет армию пользователя в JSON"""
    users_data = load_users_data()
    if str(user_id) not in users_data["users"]:
        return False
    
    army_data = {
        "faction": faction,
        "points": points,
        "created_date": datetime.now().isoformat(),
        "units": []
    }
    
    users_data["users"][str(user_id)]["armies"].append(army_data)
    save_users_data(users_data)
    return True


# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name
        
        # Проверяем, зарегистрирован ли пользователь
        if not is_user_registered(user_id):
            # Показываем клавиатуру для выбора типа игрока
            keyboard = [
                [InlineKeyboardButton("🆕 Новый игрок", callback_data="new_player")],
                [InlineKeyboardButton("🎖️ Опытный игрок", callback_data="experienced_player")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = """
🎖️ **Добро пожаловать в Warhammer Army Builder!** 🎖️

Я помогу вам создать армию для Warhammer 40k по поинтам.

**Выберите ваш тип:**
🆕 **Новый игрок** - если вы только начинаете играть в Warhammer 40k
🎖️ **Опытный игрок** - если у вас уже есть опыт игры

После регистрации вы сможете создавать и сохранять свои армии!
            """
            await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)
        else:
            # Пользователь уже зарегистрирован
            user_data = get_user_data(user_id)
            player_type_emoji = "🆕" if user_data["player_type"] == "new_player" else "🎖️"
            
            welcome_text = f"""
{player_type_emoji} **Добро пожаловать обратно, {username}!** {player_type_emoji}

Вы зарегистрированы как: **{user_data["player_type"].replace("_", " ").title()}**

**Доступные команды:**
/help - Показать все команды
/newarmy <фракция> <поинты> - Создать новую армию
/listarmy - Показать текущую армию
/addunit <юнит> [количество] - Добавить юнит в армию
/removeunit <юнит> - Удалить юнит из армии
/units <фракция> - Показать доступные юниты фракции
/unitcost <юнит> - Показать стоимость конкретного юнита
/costs <фракция/юнит> - Показать стоимость всех юнитов фракции или конкретного юнита
/coast <фракция/юнит> - Показать все юниты с поинтами (альтернатива /costs)
/points - Показать информацию о поинтах
/stats - Подробная статистика армии
/export - Экспорт армии в текстовом формате
/clear - Очистить армию

**Доступные фракции:**
• Space Marines
• Orks  
• Eldar
• Chaos Space Marines
• Tyranids

Начните с создания армии командой /newarmy!
            """
            await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        help_text = """
**📋 Команды бота:**

/newarmy <фракция> <поинты> - Создать новую армию
• Пример: /newarmy Space Marines 2000

/listarmy - Показать текущую армию

/addunit <юнит> [количество] - Добавить юнит
• Пример: /addunit Captain 1

/removeunit <юнит> - Удалить юнит

/units <фракция> - Показать юниты фракции
• Пример: /units Space Marines

/unitcost <юнит> - Показать стоимость юнита
• Пример: /unitcost Dreadnought

/costs <фракция/юнит> - Показать стоимость всех юнитов фракции или конкретного юнита
• Пример: /costs Space Marines
• Пример: /costs Dreadnought

/coast <фракция/юнит> - Показать все юниты с поинтами
• Пример: /coast Space Marines
• Пример: /coast Hive Tyrant

/points - Информация о поинтах

/stats - Подробная статистика армии

/export - Экспорт армии в текстовом формате

/clear - Очистить армию

**Фракции:** Space Marines, Orks, Eldar, Chaos Space Marines, Tyranids
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

async def newarmy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and context.args:
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        user_id = update.message.from_user.id
        
        # Проверяем, зарегистрирован ли пользователь
        if not is_user_registered(user_id):
            await update.message.reply_text(
                "❌ Вы не зарегистрированы! Используйте команду /start для регистрации."
            )
            return
        
        if len(context.args) < 2:
            await update.message.reply_text("Использование: /newarmy <фракция> <поинты>\nПример: /newarmy Space Marines 2000")
            return
        
        faction = " ".join(context.args[:-1])
        try:
            points = int(context.args[-1])
        except ValueError:
            await update.message.reply_text("Поинты должны быть числом!")
            return
        
        if faction not in get_available_factions():
            available_factions = ", ".join(get_available_factions())
            await update.message.reply_text(f"Фракция '{faction}' не найдена. Доступные: {available_factions}")
            return
        
        if points < 500 or points > 3000:
            await update.message.reply_text("Поинты должны быть от 500 до 3000!")
            return
        
        # Создаем армию в памяти
        user_armies[user_id] = Army(faction, points)
        
        # Сохраняем армию в JSON
        if save_user_army(user_id, faction, points):
            await update.message.reply_text(
                f"✅ **Создана новая армия {faction} на {points} поинтов!**\n\n"
                f"Армия сохранена в вашем профиле. Теперь вы можете добавлять юниты командой /addunit.\n\n"
                f"Используйте /listarmy для просмотра армии или /units {faction} для просмотра доступных юнитов.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"✅ Создана новая армия {faction} на {points} поинтов!")

async def listarmy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии! Создайте её командой /newarmy")
            return
        
        army = user_armies[user_id]
        text = f"**🎖️ Армия {army.faction}**\n"
        text += f"Поинты: {army.total_points}/{army.max_points} ({army.remaining_points} осталось)\n\n"
        
        if not army.units:
            text += "Армия пуста. Добавьте юниты командой /addunit"
        else:
            text += "**Состав армии:**\n"
            for army_unit in army.units:
                text += f"• {army_unit.unit.name} x{army_unit.count} ({army_unit.total_points} поинтов) [{army_unit.unit.category}]\n"
        
        text += f"\n**Слоты:**\n"
        text += f"HQ: {army.hq_slots}, Troops: {army.troop_slots}, Elites: {army.elite_slots}\n"
        text += f"Fast Attack: {army.fast_attack_slots}, Heavy Support: {army.heavy_support_slots}\n"
        text += f"Flyer: {army.flyer_slots}, Transport: {army.transport_slots}"
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def addunit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and context.args:
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии! Создайте её командой /newarmy")
            return
        
        army = user_armies[user_id]
        unit_name = " ".join(context.args[:-1]) if len(context.args) > 1 else " ".join(context.args)
        count = 1
        
        if len(context.args) > 1:
            try:
                count = int(context.args[-1])
                unit_name = " ".join(context.args[:-1])
            except ValueError:
                pass
        
        # Поиск юнита в JSON данных
        unit = None
        faction_units = get_faction_units(army.faction)
        for u in faction_units:
            if u.name.lower() == unit_name.lower():
                unit = u
                break
        
        if not unit:
            await update.message.reply_text(f"Юнит '{unit_name}' не найден в фракции {army.faction}!")
            return
        
        success, message = army.add_unit(unit, count)
        if success:
            await update.message.reply_text(f"✅ {message}")
        else:
            await update.message.reply_text(f"❌ {message}")

async def removeunit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and context.args:
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии!")
            return
        
        army = user_armies[user_id]
        unit_name = " ".join(context.args)
        
        # Поиск и удаление юнита
        for i, army_unit in enumerate(army.units):
            if army_unit.unit.name.lower() == unit_name.lower():
                army.units.pop(i)
                army._update_slots(army_unit.unit.category, 1)  # Возвращаем слот
                await update.message.reply_text(f"✅ Удален {army_unit.unit.name}")
                return
        
        await update.message.reply_text(f"Юнит '{unit_name}' не найден в армии!")

async def units_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and context.args:
        faction = " ".join(context.args)
        
        if faction not in get_available_factions():
            available_factions = ", ".join(get_available_factions())
            await update.message.reply_text(f"Фракция '{faction}' не найдена. Доступные: {available_factions}")
            return
        
        text = f"**{faction} - Доступные юниты:**\n\n"
        
        categories = {}
        faction_units = get_faction_units(faction)
        for unit in faction_units:
            if unit.category not in categories:
                categories[unit.category] = []
            categories[unit.category].append(unit)
        
        for category, units in categories.items():
            text += f"**{category}:**\n"
            for unit in units:
                text += f"• {unit.name} - {unit.points} поинтов"
                if unit.min_size != unit.max_size:
                    text += f" ({unit.min_size}-{unit.max_size} моделей)"
                if unit.special_rules:
                    text += f" [{', '.join(unit.special_rules)}]"
                text += "\n"
            text += "\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии! Создайте её командой /newarmy")
            return
        
        army = user_armies[user_id]
        text = f"**📊 Информация о поинтах:**\n"
        text += f"Использовано: {army.total_points}/{army.max_points}\n"
        text += f"Осталось: {army.remaining_points}\n"
        text += f"Процент использования: {(army.total_points/army.max_points)*100:.1f}%"
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии!")
            return
        
        del user_armies[user_id]
        await update.message.reply_text("✅ Армия очищена!")

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии! Создайте её командой /newarmy")
            return
        
        army = user_armies[user_id]
        text = f"🎖️ **ЭКСПОРТ АРМИИ {army.faction.upper()}** 🎖️\n"
        text += f"Поинты: {army.total_points}/{army.max_points}\n\n"
        
        if not army.units:
            text += "Армия пуста."
        else:
            # Группируем по категориям
            categories = {}
            for army_unit in army.units:
                category = army_unit.unit.category
                if category not in categories:
                    categories[category] = []
                categories[category].append(army_unit)
            
            for category, units in categories.items():
                text += f"**{category}:**\n"
                for army_unit in units:
                    text += f"• {army_unit.unit.name} x{army_unit.count} ({army_unit.total_points} поинтов)\n"
                text += "\n"
        
        text += f"**Итого поинтов:** {army.total_points}/{army.max_points}"
        await update.message.reply_text(text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        
        if user_id not in user_armies:
            await update.message.reply_text("У вас нет армии! Создайте её командой /newarmy")
            return
        
        army = user_armies[user_id]
        
        # Статистика по категориям
        category_stats = {}
        for army_unit in army.units:
            category = army_unit.unit.category
            if category not in category_stats:
                category_stats[category] = {"units": 0, "points": 0}
            category_stats[category]["units"] += army_unit.count
            category_stats[category]["points"] += army_unit.total_points
        
        text = f"📊 **СТАТИСТИКА АРМИИ {army.faction}** 📊\n\n"
        text += f"**Общая информация:**\n"
        text += f"• Всего юнитов: {sum(army_unit.count for army_unit in army.units)}\n"
        text += f"• Уникальных юнитов: {len(army.units)}\n"
        text += f"• Использовано поинтов: {army.total_points}/{army.max_points} ({(army.total_points/army.max_points)*100:.1f}%)\n\n"
        
        text += f"**По категориям:**\n"
        for category, stats in category_stats.items():
            text += f"• {category}: {stats['units']} юнитов, {stats['points']} поинтов\n"
        
        text += f"\n**Оставшиеся слоты:**\n"
        text += f"HQ: {army.hq_slots}, Troops: {army.troop_slots}, Elites: {army.elite_slots}\n"
        text += f"Fast Attack: {army.fast_attack_slots}, Heavy Support: {army.heavy_support_slots}\n"
        text += f"Flyer: {army.flyer_slots}, Transport: {army.transport_slots}"
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def unitcost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра стоимости конкретного юнита"""
    if update.message and context.args:
        unit_name = " ".join(context.args)
        unit_found = False
        
        text = f"💰 **Поиск стоимости юнита: {unit_name}** 💰\n\n"
        
        # Ищем юнит во всех фракциях
        for faction, faction_data in JSON_FACTION_DATA.items():
            for unit in faction_data['units']:
                if unit_name.lower() in unit['name'].lower():
                    unit_found = True
                    text += f"**{unit['name']}** ({faction})\n"
                    text += f"💰 Стоимость: {unit['points']} поинтов\n\n"
        
        if not unit_found:
            text += "❌ Юнит не найден!\n\n"
            text += "**Доступные фракции для поиска:**\n"
            for faction in JSON_FACTION_DATA.keys():
                text += f"• {faction}\n"
            text += "\nПопробуйте использовать /costs <фракция> для просмотра всех юнитов фракции"
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def costs_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра стоимости юнитов фракции или конкретного юнита"""
    if update.message and context.args:
        args_text = " ".join(context.args)
        
        # Сначала проверяем, является ли это фракцией
        faction_found = False
        for faction, faction_data in JSON_FACTION_DATA.items():
            if args_text.lower() in faction.lower():
                faction_found = True
                text = f"💰 **Стоимость юнитов: {faction}** 💰\n\n"
                
                if faction_data['description']:
                    text += f"*{faction_data['description']}*\n\n"
                
                # Сортируем юниты по стоимости
                sorted_units = sorted(faction_data['units'], key=lambda x: x['points'])
                
                for unit in sorted_units:
                    text += f"• **{unit['name']}** - {unit['points']} поинтов\n"
                
                text += f"\n📊 Всего юнитов: {len(faction_data['units'])}"
                break
        
        if faction_found:
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        
        # Если не найдена фракция, ищем конкретный юнит
        unit_found = False
        text = f"💰 **Поиск юнита: {args_text}** 💰\n\n"
        
        for faction, faction_data in JSON_FACTION_DATA.items():
            for unit in faction_data['units']:
                if args_text.lower() in unit['name'].lower():
                    unit_found = True
                    text += f"**{unit['name']}** ({faction})\n"
                    text += f"💰 Стоимость: {unit['points']} поинтов\n\n"
        
        if not unit_found:
            text += "❌ Юнит не найден!\n\n"
            text += "**Доступные фракции:**\n"
            for faction in JSON_FACTION_DATA.keys():
                text += f"• {faction}\n"
            text += "\n**Использование:**\n"
            text += "• `/costs <фракция>` - показать все юниты фракции\n"
            text += "• `/costs <юнит>` - найти конкретный юнит"
        
        await update.message.reply_text(text, parse_mode='Markdown')

async def coast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра юнитов с поинтами (фракция или конкретный юнит)"""
    if update.message and context.args:
        args_text = " ".join(context.args)
        
        # Сначала проверяем, является ли это фракцией
        faction_found = False
        for faction, faction_data in JSON_FACTION_DATA.items():
            if args_text.lower() in faction.lower():
                faction_found = True
                text = f"💰 **Все юниты с поинтами: {faction}** 💰\n\n"
                
                if faction_data['description']:
                    text += f"*{faction_data['description']}*\n\n"
                
                # Сортируем юниты по стоимости
                sorted_units = sorted(faction_data['units'], key=lambda x: x['points'])
                
                for unit in sorted_units:
                    text += f"• **{unit['name']}** - {unit['points']} поинтов\n"
                
                text += f"\n📊 Всего юнитов: {len(faction_data['units'])}"
                break
        
        if faction_found:
            await update.message.reply_text(text, parse_mode='Markdown')
            return
        
        # Если не найдена фракция, ищем конкретный юнит
        unit_found = False
        text = f"💰 **Поиск юнита: {args_text}** 💰\n\n"
        
        for faction, faction_data in JSON_FACTION_DATA.items():
            for unit in faction_data['units']:
                if args_text.lower() in unit['name'].lower():
                    unit_found = True
                    text += f"**{unit['name']}** ({faction})\n"
                    text += f"💰 Стоимость: {unit['points']} поинтов\n\n"
        
        if not unit_found:
            text += "❌ Юнит не найден!\n\n"
            text += "**Доступные фракции:**\n"
            for faction in JSON_FACTION_DATA.keys():
                text += f"• {faction}\n"
            text += "\n**Использование:**\n"
            text += "• `/coast <фракция>` - показать все юниты фракции\n"
            text += "• `/coast <юнит>` - найти конкретный юнит"
        
        await update.message.reply_text(text, parse_mode='Markdown')

# Callback query handler для обработки нажатий на inline кнопки
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    if query.data == "new_player":
        # Отправляем новое сообщение с клавиатурой для контакта
        contact_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Поделиться контактом", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
        
        await query.message.reply_text(
            "🆕 **Отлично! Вы выбрали \"Новый игрок\"**\n\n"
            "Для завершения регистрации, пожалуйста, поделитесь своим контактом, "
            "нажав на кнопку ниже. Это поможет нам связаться с вами при необходимости.\n\n"
            "📱 Нажмите на кнопку ниже:",
            parse_mode='Markdown',
            reply_markup=contact_keyboard
        )
        
        # Сохраняем состояние ожидания контакта
        context.user_data['waiting_for_contact'] = True
        context.user_data['player_type'] = 'new_player'
        
    elif query.data == "experienced_player":
        # Регистрируем опытного игрока без запроса контакта
        register_user(user_id, username, "experienced_player")
        
        await query.edit_message_text(
            "🎖️ **Отлично! Вы зарегистрированы как опытный игрок!**\n\n"
            "Теперь вы можете создавать и сохранять свои армии.\n\n"
            "Используйте команду /newarmy <фракция> <поинты> для создания армии.\n"
            "Например: /newarmy Space Marines 2000",
            parse_mode='Markdown'
        )

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_type: str = update.message.chat.type
        user_message: str = update.message.text if update.message.text is not None else ""
        user_id = update.message.from_user.id
        username = update.message.from_user.username or update.message.from_user.first_name
        
        print(f"Message type: ({update.message.chat.id}) in {message_type}: '{user_message}'")
        
        # Проверяем, ожидаем ли мы контакт от пользователя
        if context.user_data.get('waiting_for_contact', False):
            if update.message.contact:
                # Получаем контакт
                contact_info = f"{update.message.contact.phone_number}"
                if update.message.contact.first_name:
                    contact_info += f" ({update.message.contact.first_name})"
                
                # Регистрируем пользователя
                register_user(user_id, username, context.user_data['player_type'], contact_info)
                
                # Очищаем состояние
                context.user_data.pop('waiting_for_contact', None)
                context.user_data.pop('player_type', None)
                
                # Убираем клавиатуру и отправляем подтверждение
                remove_keyboard = ReplyKeyboardMarkup([[]], resize_keyboard=True, one_time_keyboard=True)
                await update.message.reply_text(
                    "✅ **Регистрация завершена!**\n\n"
                    "Ваш контакт сохранен. Теперь вы можете создавать и сохранять свои армии.\n\n"
                    "Используйте команду /newarmy <фракция> <поинты> для создания армии.\n"
                    "Например: /newarmy Space Marines 2000",
                    parse_mode='Markdown',
                    reply_markup=remove_keyboard
                )
                return
            else:
                await update.message.reply_text(
                    "Пожалуйста, поделитесь контактом, нажав на кнопку \"📱 Поделиться контактом\""
                )
                return
        
        # Простые ответы на общие вопросы
        processed_text = user_message.lower()
        
        if any(word in processed_text for word in ["привет", "hello", "hi", "здравствуй"]):
            await update.message.reply_text("Привет! Я помогу создать армию для Warhammer 40k. Используйте /help для списка команд!")
        elif any(word in processed_text for word in ["армия", "army", "войска"]):
            await update.message.reply_text("Для работы с армией используйте команды:\n/newarmy - создать армию\n/listarmy - показать армию\n/addunit - добавить юнит")
        elif any(word in processed_text for word in ["поинты", "points", "очки"]):
            await update.message.reply_text("Для информации о поинтах используйте команду /points")
        elif any(word in processed_text for word in ["помощь", "help", "команды"]):
            await update.message.reply_text("Используйте /help для полного списка команд!")
    else:
        # Сообщение не распознано, но update.message всегда None здесь, поэтому ничего не делаем
        pass

# Error handler
async def error(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update {update} caused error {context.error}")

if __name__ == '__main__':
    print("Starting bot...")
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("newarmy", newarmy_command))
    app.add_handler(CommandHandler("listarmy", listarmy_command))
    app.add_handler(CommandHandler("addunit", addunit_command))
    app.add_handler(CommandHandler("removeunit", removeunit_command))
    app.add_handler(CommandHandler("units", units_command))
    app.add_handler(CommandHandler("unitcost", unitcost_command))
    app.add_handler(CommandHandler("costs", costs_command))
    app.add_handler(CommandHandler("coast", coast_command))
    app.add_handler(CommandHandler("points", points_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("clear", clear_command))
    
    # Callback query handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT | filters.CONTACT, handle_message))
    
    # Error handler
    app.add_error_handler(error)
    
    print("Polling...")
    app.run_polling(poll_interval=3)