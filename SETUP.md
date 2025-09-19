# Настройка Warhammer Army Builder Bot

## Шаг 1: Получение токена бота


1. Откройте Telegram и найдите бота [@BotFather](https://t.me/BotFather)
2. Отправьте команду `/newbot`
3. Введите имя для вашего бота (например: "Warhammer Army Builder")
4. Введите username для бота (например: "warhammer_army_builder_bot")
5. Скопируйте полученный токен

## Шаг 2: Настройка токена

1. Откройте файл `main.py`
2. Найдите строку:
   ```python
   TOKEN: Final = "8493597534:AAHNuyfSW3SjUrtQmSNZyVTamzEnGlDUvbw"
   ```
3. Замените токен на ваш:
   ```python
   TOKEN: Final = "YOUR_BOT_TOKEN_HERE"
   ```

## Шаг 3: Установка зависимостей

```bash
pip install -r requirements.txt
```

## Шаг 4: Запуск бота

```bash
python main.py
```

Вы должны увидеть:
```
Starting bot...
Polling...
```

## Шаг 5: Тестирование

1. Найдите вашего бота в Telegram по username
2. Отправьте команду `/start`
3. Попробуйте создать армию:
   ```
   /newarmy Space Marines 2000
   /addunit Captain 1
   /listarmy
   ```

## Возможные проблемы

### Ошибка с токеном
```
telegram.error.Unauthorized: Unauthorized
```
**Решение:** Проверьте правильность токена

### Ошибка с версией Python
```
AttributeError: 'Updater' object has no attribute '_Updater__polling_cleanup_cb'
```
**Решение:** Обновите python-telegram-bot:
```bash
pip install python-telegram-bot==21.0.1
```

### Бот не отвечает
**Решение:** 
1. Проверьте, что бот запущен
2. Проверьте интернет-соединение
3. Убедитесь, что токен правильный

## Команды для тестирования

```
/start
/newarmy Space Marines 2000
/addunit Captain 1
/addunit Tactical Squad 10
/addunit Dreadnought 1
/listarmy
/stats
/export
/points
/units Space Marines
/help
```

## Остановка бота

Нажмите `Ctrl+C` в терминале для остановки бота.

## Логи

Бот выводит логи в консоль. Вы увидите сообщения о полученных командах и ошибках.

## Поддержка

Если у вас возникли проблемы:
1. Проверьте версию Python (должна быть 3.8+)
2. Убедитесь, что все зависимости установлены
3. Проверьте правильность токена
4. Запустите тесты: `python test_bot.py`
