from typing import Final, Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import json
import os

TOKEN: Final = "8493597534:AAHNuyfSW3SjUrtQmSNZyVTamzEnGlDUvbw"
BOT_USERNAME: Final = "@regiment_builder_bot"

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

# База данных юнитов
UNITS_DATABASE = {
    "Space Marines": [
        # HQ
        Unit("Captain", 80, "HQ", "Space Marines", special_rules=["Aura of Command"]),
        Unit("Lieutenant", 60, "HQ", "Space Marines", special_rules=["Tactical Precision"]),
        Unit("Chaplain", 70, "HQ", "Space Marines", special_rules=["Litany of Hate"]),
        Unit("Librarian", 90, "HQ", "Space Marines", special_rules=["Psychic Powers"]),
        Unit("Techmarine", 50, "HQ", "Space Marines", special_rules=["Blessing of the Omnissiah"]),
        # Troops
        Unit("Tactical Squad", 100, "Troops", "Space Marines", min_size=5, max_size=10),
        Unit("Intercessor Squad", 90, "Troops", "Space Marines", min_size=5, max_size=10),
        Unit("Scout Squad", 70, "Troops", "Space Marines", min_size=5, max_size=10),
        Unit("Infiltrator Squad", 120, "Troops", "Space Marines", min_size=5, max_size=10),
        # Elites
        Unit("Terminator Squad", 200, "Elites", "Space Marines", min_size=3, max_size=10),
        Unit("Dreadnought", 140, "Elites", "Space Marines"),
        Unit("Venerable Dreadnought", 160, "Elites", "Space Marines"),
        Unit("Sternguard Veterans", 100, "Elites", "Space Marines", min_size=5, max_size=10),
        Unit("Vanguard Veterans", 120, "Elites", "Space Marines", min_size=5, max_size=10),
        Unit("Apothecary", 50, "Elites", "Space Marines", special_rules=["Narthecium"]),
        # Fast Attack
        Unit("Assault Squad", 120, "Fast Attack", "Space Marines", min_size=5, max_size=10),
        Unit("Land Speeder", 80, "Fast Attack", "Space Marines"),
        Unit("Attack Bike", 40, "Fast Attack", "Space Marines"),
        Unit("Inceptor Squad", 110, "Fast Attack", "Space Marines", min_size=3, max_size=6),
        # Heavy Support
        Unit("Predator", 130, "Heavy Support", "Space Marines"),
        Unit("Devastator Squad", 120, "Heavy Support", "Space Marines", min_size=5, max_size=10),
        Unit("Hellblaster Squad", 110, "Heavy Support", "Space Marines", min_size=5, max_size=10),
        Unit("Eliminator Squad", 75, "Heavy Support", "Space Marines", min_size=3, max_size=6),
    ],
    "Orks": [
        # HQ
        Unit("Warboss", 70, "HQ", "Orks", special_rules=["Waaagh!"]),
        Unit("Big Mek", 60, "HQ", "Orks", special_rules=["Kustom Force Field"]),
        Unit("Weirdboy", 50, "HQ", "Orks", special_rules=["Warp Powers"]),
        Unit("Painboy", 40, "HQ", "Orks", special_rules=["Grot Orderly"]),
        # Troops
        Unit("Boyz", 60, "Troops", "Orks", min_size=10, max_size=30),
        Unit("Gretchin", 30, "Troops", "Orks", min_size=10, max_size=30),
        Unit("Beast Snagga Boyz", 100, "Troops", "Orks", min_size=10, max_size=20),
        # Elites
        Unit("Nobz", 100, "Elites", "Orks", min_size=5, max_size=10),
        Unit("Meganobz", 150, "Elites", "Orks", min_size=3, max_size=10),
        Unit("Kommandos", 80, "Elites", "Orks", min_size=5, max_size=15),
        Unit("Tankbustas", 90, "Elites", "Orks", min_size=5, max_size=15),
        Unit("Burna Boyz", 70, "Elites", "Orks", min_size=5, max_size=15),
        # Fast Attack
        Unit("Stormboyz", 80, "Fast Attack", "Orks", min_size=5, max_size=20),
        Unit("Warbikers", 120, "Fast Attack", "Orks", min_size=3, max_size=12),
        Unit("Squighog Boyz", 110, "Fast Attack", "Orks", min_size=3, max_size=9),
        Unit("Deffkoptas", 60, "Fast Attack", "Orks", min_size=1, max_size=6),
        # Heavy Support
        Unit("Lootas", 100, "Heavy Support", "Orks", min_size=5, max_size=15),
        Unit("Deff Dread", 100, "Heavy Support", "Orks"),
        Unit("Killa Kans", 80, "Heavy Support", "Orks", min_size=1, max_size=6),
        Unit("Mek Gunz", 50, "Heavy Support", "Orks", min_size=1, max_size=6),
    ],
    "Eldar": [
        # HQ
        Unit("Farseer", 90, "HQ", "Eldar", special_rules=["Runes of Fate"]),
        Unit("Autarch", 70, "HQ", "Eldar", special_rules=["Path of Command"]),
        Unit("Warlock", 40, "HQ", "Eldar", special_rules=["Runes of Battle"]),
        Unit("Spiritseer", 60, "HQ", "Eldar", special_rules=["Runes of Battle"]),
        # Troops
        Unit("Guardian Defenders", 80, "Troops", "Eldar", min_size=10, max_size=20),
        Unit("Rangers", 70, "Troops", "Eldar", min_size=5, max_size=10),
        Unit("Dire Avengers", 70, "Troops", "Eldar", min_size=5, max_size=10),
        # Elites
        Unit("Wraithguard", 200, "Elites", "Eldar", min_size=5, max_size=10),
        Unit("Howling Banshees", 100, "Elites", "Eldar", min_size=5, max_size=10),
        Unit("Striking Scorpions", 90, "Elites", "Eldar", min_size=5, max_size=10),
        Unit("Fire Dragons", 100, "Elites", "Eldar", min_size=5, max_size=10),
        Unit("Wraithblades", 180, "Elites", "Eldar", min_size=5, max_size=10),
        # Fast Attack
        Unit("Swooping Hawks", 90, "Fast Attack", "Eldar", min_size=5, max_size=10),
        Unit("Vypers", 60, "Fast Attack", "Eldar"),
        Unit("Shining Spears", 120, "Fast Attack", "Eldar", min_size=3, max_size=6),
        Unit("Warp Spiders", 100, "Fast Attack", "Eldar", min_size=5, max_size=10),
        # Heavy Support
        Unit("Falcon", 130, "Heavy Support", "Eldar"),
        Unit("Fire Prism", 150, "Heavy Support", "Eldar"),
        Unit("Wraithlord", 120, "Heavy Support", "Eldar"),
        Unit("Dark Reapers", 100, "Heavy Support", "Eldar", min_size=5, max_size=10),
    ],
    "Chaos Space Marines": [
        # HQ
        Unit("Chaos Lord", 80, "HQ", "Chaos Space Marines", special_rules=["Dark Apostle"]),
        Unit("Sorcerer", 90, "HQ", "Chaos Space Marines", special_rules=["Dark Hereticus"]),
        Unit("Dark Apostle", 70, "HQ", "Chaos Space Marines", special_rules=["Dark Zealotry"]),
        # Troops
        Unit("Chaos Space Marines", 100, "Troops", "Chaos Space Marines", min_size=5, max_size=10),
        Unit("Cultists", 50, "Troops", "Chaos Space Marines", min_size=10, max_size=20),
        Unit("Khorne Berzerkers", 120, "Troops", "Chaos Space Marines", min_size=5, max_size=10),
        # Elites
        Unit("Chosen", 120, "Elites", "Chaos Space Marines", min_size=5, max_size=10),
        Unit("Possessed", 140, "Elites", "Chaos Space Marines", min_size=5, max_size=10),
        Unit("Terminators", 200, "Elites", "Chaos Space Marines", min_size=3, max_size=10),
        # Fast Attack
        Unit("Raptors", 100, "Fast Attack", "Chaos Space Marines", min_size=5, max_size=10),
        Unit("Bikers", 80, "Fast Attack", "Chaos Space Marines", min_size=3, max_size=9),
        # Heavy Support
        Unit("Havocs", 100, "Heavy Support", "Chaos Space Marines", min_size=5, max_size=10),
        Unit("Obliterators", 180, "Heavy Support", "Chaos Space Marines", min_size=1, max_size=3),
    ]
}

# Хранилище армий пользователей
user_armies: Dict[int, Army] = {}


# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        user_id = update.message.from_user.id
        welcome_text = """
🎖️ **Добро пожаловать в Warhammer Army Builder!** 🎖️

Я помогу вам создать армию для Warhammer 40k по поинтам.

**Доступные команды:**
/help - Показать все команды
/newarmy <фракция> <поинты> - Создать новую армию
/listarmy - Показать текущую армию
/addunit <юнит> [количество] - Добавить юнит в армию
/removeunit <юнит> - Удалить юнит из армии
/units <фракция> - Показать доступные юниты фракции
/points - Показать информацию о поинтах
/stats - Подробная статистика армии
/export - Экспорт армии в текстовом формате
/clear - Очистить армию

**Доступные фракции:**
• Space Marines
• Orks  
• Eldar
• Chaos Space Marines

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

/points - Информация о поинтах

/stats - Подробная статистика армии

/export - Экспорт армии в текстовом формате

/clear - Очистить армию

**Фракции:** Space Marines, Orks, Eldar, Chaos Space Marines
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')

async def newarmy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and context.args:
        if update.message.from_user is None:
            await update.message.reply_text("Ошибка: не удалось определить пользователя.")
            return
        user_id = update.message.from_user.id
        
        if len(context.args) < 2:
            await update.message.reply_text("Использование: /newarmy <фракция> <поинты>\nПример: /newarmy Space Marines 2000")
            return
        
        faction = " ".join(context.args[:-1])
        try:
            points = int(context.args[-1])
        except ValueError:
            await update.message.reply_text("Поинты должны быть числом!")
            return
        
        if faction not in UNITS_DATABASE:
            available_factions = ", ".join(UNITS_DATABASE.keys())
            await update.message.reply_text(f"Фракция '{faction}' не найдена. Доступные: {available_factions}")
            return
        
        if points < 500 or points > 3000:
            await update.message.reply_text("Поинты должны быть от 500 до 3000!")
            return
        
        user_armies[user_id] = Army(faction, points)
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
        
        # Поиск юнита
        unit = None
        for faction_units in UNITS_DATABASE.values():
            for u in faction_units:
                if u.name.lower() == unit_name.lower() and u.faction == army.faction:
                    unit = u
                    break
            if unit:
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
        
        if faction not in UNITS_DATABASE:
            available_factions = ", ".join(UNITS_DATABASE.keys())
            await update.message.reply_text(f"Фракция '{faction}' не найдена. Доступные: {available_factions}")
            return
        
        text = f"**{faction} - Доступные юниты:**\n\n"
        
        categories = {}
        for unit in UNITS_DATABASE[faction]:
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

# Message handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message_type: str = update.message.chat.type
        user_message: str = update.message.text if update.message.text is not None else ""
        
        print(f"Message type: ({update.message.chat.id}) in {message_type}: '{user_message}'")
        
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
    app.add_handler(CommandHandler("points", points_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("clear", clear_command))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    # Error handler
    app.add_error_handler(error)
    
    print("Polling...")
    app.run_polling(poll_interval=3)