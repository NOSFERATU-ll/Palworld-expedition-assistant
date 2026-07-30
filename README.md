# Palworld Expedition Assistant

A Windows desktop utility that automates the repetitive Pal Expedition Station routine in **Palworld** single-player.

**English** · [Русский](#русский)

> This is an external automation tool, not an in-game mod. It does not modify Palworld files or save data.

## Features

- Selects an expedition and assigns Pals automatically.
- Starts the expedition, advances it through a temporary Windows time-zone change, and restores the original time zone afterward.
- Collects rewards and repeats the cycle as many times as requested.
- Global hotkeys: **F6** to start and **F8** to stop.
- Automatic relative time-zone jumps based on the user's current Windows time zone.
- Russian and English application interface with instant **RU / EN** switching.
- Mouse-wheel navigation through the expedition list.
- Attempts to restore the original Windows time zone even after an error or emergency stop.

## Requirements

The current version is tested with:

- Windows 10 or Windows 11;
- `1920×1080` display resolution;
- Windows display scaling set to `100%`;
- Palworld running in **Borderless Windowed** mode;
- the character standing in front of the Pal Expedition Station with the `F` interaction prompt available.

The utility requests administrator privileges because Windows requires them for changing the system time zone and reliably handling global input.

## Installation

1. Open the **Releases** section of this repository.
2. Download the latest `.exe` file.
3. Launch the application and approve the administrator prompt.
4. Select an expedition, a relative time jump, the number of repetitions, and the delay after starting.
5. Return to Palworld, stand in front of the Expedition Station, and press **F6**.

Press **F8** at any time to request an emergency stop.

## Time-zone jumps

Instead, it calculates a destination time zone relative to the user's current Windows zone.

For example, selecting `+2 hours` finds an installed Windows time zone that is currently two hours ahead, including daylight-saving-time differences, and restores the original zone after the expedition cycle.

## Antivirus and SmartScreen notices

The application is distributed as an unsigned executable and performs actions that security software often treats cautiously: global hotkeys, simulated mouse and keyboard input, and system time-zone changes. Windows SmartScreen or antivirus software may therefore display a warning.

The complete source code and GitHub Actions build workflow are available in this repository for inspection.

## Important notes

- Intended for single-player use.
- Do not move the mouse or use the keyboard while an automation step is running unless stopping with **F8**.
- Test a new configuration with one repetition first.
- Game updates or interface changes may temporarily break visual detection.
- Use the program at your own risk.

## Running from source

1. Install Python 3.11.
2. Run `install.bat`.
3. Start the application with `run_venv.bat`.

## Disclaimer

This is an unofficial fan-made utility and is not affiliated with or endorsed by Pocketpair. Palworld and its related trademarks belong to their respective owners.

---

# Русский

**Palworld Expedition Assistant** — внешняя Windows-утилита, которая автоматизирует повторяющиеся действия в Центре экспедиций Палов в одиночной игре **Palworld**.

> Это не внутриигровой мод. Программа не изменяет файлы Palworld и сохранения.

## Возможности

- Выбирает экспедицию и автоматически назначает Палов.
- Запускает экспедицию, временно меняет часовой пояс Windows и затем возвращает исходный.
- Забирает награду и повторяет цикл заданное количество раз.
- Глобальные горячие клавиши: **F6** — запуск, **F8** — остановка.
- Автоматический подбор часового пояса относительно текущего пояса пользователя.
- Мгновенное переключение интерфейса **RU / EN**.
- Прокрутка списка экспедиций обычным колесом мыши.
- Аварийное восстановление исходного часового пояса при ошибке или остановке.

## Требования

Текущая версия проверена при следующих настройках:

- Windows 10 или Windows 11;
- разрешение экрана `1920×1080`;
- масштаб Windows `100%`;
- Palworld запущен в режиме **«Окно без рамки»**;
- персонаж стоит перед Центром экспедиций, а на экране доступна подсказка взаимодействия `F`.

Программа запрашивает права администратора, поскольку они нужны Windows для смены системного часового пояса и надёжной обработки глобального ввода.

## Установка и запуск

1. Открой раздел **Releases** в этом репозитории.
2. Скачай последний `.exe`-файл.
3. Запусти программу и подтверди запрос прав администратора.
4. Выбери экспедицию, временной сдвиг, количество повторений и паузу после старта.
5. Вернись в Palworld, встань перед Центром экспедиций и нажми **F6**.

Для аварийной остановки в любой момент нажми **F8**.

## Как работают часовые пояса

Она рассчитывает целевой пояс относительно текущего часового пояса Windows.

Например, при выборе `+2 часа` программа найдёт установленный в Windows пояс, который в данный момент находится на два часа впереди с учётом летнего времени, а после завершения цикла вернёт исходный пояс.

## Предупреждения антивируса и SmartScreen

Программа распространяется как неподписанный `.exe` и выполняет действия, к которым защитное ПО относится настороженно: использует глобальные горячие клавиши, имитирует ввод мыши и клавиатуры и меняет системный часовой пояс. Поэтому Windows SmartScreen или антивирус могут показать предупреждение.

Исходный код и workflow сборки GitHub Actions полностью доступны в этом репозитории для проверки.

## Важно

- Утилита предназначена для одиночной игры.
- Во время автоматизации не двигай мышь и не используй клавиатуру, кроме остановки через **F8**.
- Новую настройку сначала проверяй с одним повторением.
- Обновления игры и изменения интерфейса могут временно нарушить распознавание.
- Используй программу на свой риск.

## Запуск из исходников

1. Установи Python 3.11.
2. Запусти `install.bat`.
3. После установки запускай приложение через `run_venv.bat`.

## Отказ от ответственности

Это неофициальная фанатская утилита, не связанная с Pocketpair и не одобренная компанией. Palworld и связанные с игрой товарные знаки принадлежат их владельцам.
