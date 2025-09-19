#!/usr/bin/env python3
"""
Тестовый скрипт для проверки функциональности Warhammer Army Builder Bot
"""

from main import Unit, Army, UNITS_DATABASE

def test_unit_creation():
    """Тест создания юнита"""
    print("🧪 Тестирование создания юнита...")
    captain = Unit("Captain", 80, "HQ", "Space Marines", special_rules=["Aura of Command"])
    assert captain.name == "Captain"
    assert captain.points == 80
    assert captain.category == "HQ"
    print("✅ Создание юнита работает корректно")

def test_army_creation():
    """Тест создания армии"""
    print("🧪 Тестирование создания армии...")
    army = Army("Space Marines", 2000)
    assert army.faction == "Space Marines"
    assert army.max_points == 2000
    assert army.total_points == 0
    assert army.remaining_points == 2000
    print("✅ Создание армии работает корректно")

def test_army_validation():
    """Тест валидации армии"""
    print("🧪 Тестирование валидации армии...")
    army = Army("Space Marines", 2000)
    
    # Получаем юнит из базы данных
    captain = None
    for unit in UNITS_DATABASE["Space Marines"]:
        if unit.name == "Captain":
            captain = unit
            break
    
    assert captain is not None, "Captain не найден в базе данных"
    
    # Тест добавления HQ юнита
    can_add, message = army.can_add_unit(captain, 1)
    assert can_add, f"Не удалось добавить Captain: {message}"
    
    # Тест добавления юнита
    success, message = army.add_unit(captain, 1)
    assert success, f"Не удалось добавить Captain: {message}"
    assert army.total_points == 80
    assert army.remaining_points == 1920
    print("✅ Валидация армии работает корректно")

def test_army_rules():
    """Тест правил армии"""
    print("🧪 Тестирование правил армии...")
    army = Army("Space Marines", 2000)
    
    # Получаем юниты
    tactical_squad = None
    for unit in UNITS_DATABASE["Space Marines"]:
        if unit.name == "Tactical Squad":
            tactical_squad = unit
            break
    
    assert tactical_squad is not None, "Tactical Squad не найден в базе данных"
    
    # Попытка добавить Troops без HQ должна провалиться
    can_add, message = army.can_add_unit(tactical_squad, 5)
    assert not can_add, "Должна быть ошибка при добавлении Troops без HQ"
    assert "HQ юнита" in message, f"Неожиданное сообщение об ошибке: {message}"
    print("✅ Правила армии работают корректно")

def test_database():
    """Тест базы данных юнитов"""
    print("🧪 Тестирование базы данных...")
    
    # Проверяем, что все фракции присутствуют
    expected_factions = ["Space Marines", "Orks", "Eldar", "Chaos Space Marines"]
    for faction in expected_factions:
        assert faction in UNITS_DATABASE, f"Фракция {faction} отсутствует в базе данных"
    
    # Проверяем количество юнитов
    total_units = sum(len(units) for units in UNITS_DATABASE.values())
    print(f"📊 Всего юнитов в базе данных: {total_units}")
    assert total_units > 50, f"Слишком мало юнитов в базе данных: {total_units}"
    
    # Проверяем структуру юнитов
    for faction, units in UNITS_DATABASE.items():
        for unit in units:
            assert unit.name, f"У юнита в {faction} отсутствует имя"
            assert unit.points > 0, f"У юнита {unit.name} в {faction} некорректные поинты: {unit.points}"
            assert unit.category in ["HQ", "Troops", "Elites", "Fast Attack", "Heavy Support", "Flyer", "Transport"], f"У юнита {unit.name} в {faction} некорректная категория: {unit.category}"
    
    print("✅ База данных работает корректно")

def main():
    """Запуск всех тестов"""
    print("🎖️ Запуск тестов Warhammer Army Builder Bot...\n")
    
    try:
        test_unit_creation()
        test_army_creation()
        test_army_validation()
        test_army_rules()
        test_database()
        
        print("\n🎉 Все тесты прошли успешно!")
        print("✅ Бот готов к работе!")
        
    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        raise

if __name__ == "__main__":
    main()

