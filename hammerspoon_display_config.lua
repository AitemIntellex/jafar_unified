-- === Мастер Мульти-Дисплеев (v3) ===
--
-- Горячие клавиши:
--   Hyper + Стрелка Влево/Вправо: Позиционировать окно на ТЕКУЩЕМ экране.
--   Hyper + 1: Переместить окно на ОСНОВНОЙ экран.
--   Hyper + 2: Переместить окно на ВТОРОЙ экран.
--   Hyper + 3: Переместить окно на ТРЕТИЙ экран (если есть).

-- 1. Определяем горячие клавиши
local hyper = {'ctrl', 'alt', 'cmd'} -- Это соответствует клавишам ⌃ + ⌥ + ⌘

-- 2. Ваши персональные настройки
local bottomDeadZoneHeight = 98  -- Высота нижней мертвой зоны
local leftZoneWidth = 195        -- Ширина левой рабочей зоны (или панели Übersicht)
local verticalDeadZoneWidth = 51 -- Ширина вертикальной мертвой полосы

-- 3. Функция для перемещения окна на УКАЗАННЫЙ экран
function moveWindowToScreen(screenIndex)
  local win = hs.window.focusedWindow()
  if not win then return end

  local screens = hs.screen.allScreens()
  local targetScreen = screens[screenIndex]

  if targetScreen then
    win:moveToScreen(targetScreen)
    -- После перемещения можно опционально развернуть окно в "безопасной" зоне
    local fullFrame = targetScreen:frame()
    local usableHeight = fullFrame.h - bottomDeadZoneHeight
    local usableFrame = {
        x = fullFrame.x,
        y = fullFrame.y,
        w = fullFrame.w,
        h = usableHeight
    }
    win:setFrame(usableFrame)
  else
    hs.alert("Экран #" .. screenIndex .. " не найден!")
  end
end

-- 4. Функция для позиционирования окна в ПРАВУЮ зону на ТЕКУЩЕМ экране
function moveWindowToRightZone()
  local win = hs.window.focusedWindow()
  if not win then return end

  local screen = win:screen()
  local fullFrame = screen:frame()
  local screenWidth = fullFrame.w
  local screenHeight = fullFrame.h

  local usableHeight = screenHeight - bottomDeadZoneHeight
  local rightZone = {
    x = fullFrame.x + leftZoneWidth + verticalDeadZoneWidth,
    y = fullFrame.y,
    w = screenWidth - leftZoneWidth - verticalDeadZoneWidth,
    h = usableHeight
  }

  win:setFrame(rightZone)
end

-- 5. Функция для позиционирования окна в ЛЕВУЮ зону на ТЕКУЩЕМ экране
function moveWindowToLeftZone()
  local win = hs.window.focusedWindow()
  if not win then return end

  local screen = win:screen()
  local fullFrame = screen:frame()
  local screenHeight = fullFrame.h

  local usableHeight = screenHeight - bottomDeadZoneHeight
  local leftZone = {
    x = fullFrame.x,
    y = fullFrame.y,
    w = leftZoneWidth,
    h = usableHeight
  }

  win:setFrame(leftZone)
end

-- 6. Привязываем ВСЕ функции к горячим клавишам
-- Позиционирование
hs.hotkey.bind(hyper, "right", moveWindowToRightZone)
hs.hotkey.bind(hyper, "left", moveWindowToLeftZone)

-- Перемещение между экранами
hs.hotkey.bind(hyper, "1", function() moveWindowToScreen(1) end)
hs.hotkey.bind(hyper, "2", function() moveWindowToScreen(2) end)
hs.hotkey.bind(hyper, "3", function() moveWindowToScreen(3) end) -- Будет работать, только если есть 3-й экран

-- Уведомление о том, что конфиг загружен
hs.notify.new({title="Hammerspoon", informativeText="Мастер Мульти-Дисплеев (v3) загружен!"}):send()
