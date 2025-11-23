import { css, run } from 'uebersicht'

// =============================================================================
// === Конфигурация Панели Jafar ===
// =============================================================================
// 
// Ваши персональные размеры, которые мы определили.
//
const PANEL_WIDTH = "195px"; // Ширина левой рабочей зоны
const DEAD_ZONE_WIDTH = "51px"; // Ширина вертикальной мертвой полосы

// =============================================================================
// === Стили (Внешний вид) ===
// =============================================================================

// Основной контейнер панели
const Container = css`
  position: fixed;
  top: 0;
  left: 0;
  width: ${PANEL_WIDTH};
  height: 100%;
  background: rgba(20, 20, 25, 0.85); // Темный, полупрозрачный фон
  backdrop-filter: blur(20px); // Эффект размытия "за стеклом"
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  color: #f0f0f0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
  padding: 15px;
  box-sizing: border-box; // Чтобы padding не увеличивал ширину
  display: flex;
  flex-direction: column; // Элементы располагаются друг под другом
`

// Заголовок
const Title = css`
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 20px 0;
  text-align: center;
  color: #a78bfa; // Фиолетовый акцент
`

// Стили для кнопок
const Button = css`
  display: block;
  width: 100%;
  padding: 10px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.05);
  color: #e0e0e0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  text-align: left;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.2);
  }
`

// Разделитель
const Separator = css`
  height: 1px;
  width: 100%;
  background: rgba(255, 255, 255, 0.1);
  margin: 15px 0;
`

// Контейнер для отображения данных
const DataRow = css`
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 13px;
`

const DataLabel = css`
  color: #a0a0a0;
`

const DataValue = css`
  font-weight: 500;
  color: #ffffff;
`

const StatusValue = (status) => css`
  font-weight: 500;
  color: ${status === 'Active' ? '#4ade80' : '#f87171'}; // Зеленый или красный
`

// =============================================================================
// === Логика Виджета ===
// =============================================================================

// Эта команда будет выполняться для получения данных (пока не используется)
export const command = "echo '{\"status\": \"Ожидание\", \"gold_price\": \"2350.00\"}'";

// Частота обновления (пока не важна)
export const refreshFrequency = false; 

// Функция рендеринга. Она рисует все, что мы видим.
export const render = ({ output, error }) => {
  // В будущем 'output' будет содержать JSON с реальными данными
  // const data = JSON.parse(output);

  return (
    <div className={Container}>
      <div className={Title}>Jafar C&C</div>
      
      <div>
        <button className={Button}>
          🚀 Анализ Gold (atrade)
        </button>
        <button className={Button}>
          🧠 Анализ Gold (btrade)
        </button>
        <button className={Button}>
          📰 Новости
        </button>
      </div>

      <div className={Separator} />

      <div>
        <div className={DataRow}>
          <div className={DataLabel}>Статус Jafar:</div>
          <div className={StatusValue('Active')}>Ожидание</div>
        </div>
        <div className={DataRow}>
          <div className={DataLabel}>Режим:</div>
          <div className={DataValue}>Аналитик</div>
        </div>
      </div>

      <div className={Separator} />

      <div>
        <div className={DataRow}>
          <div className={DataLabel}>Gold (GC):</div>
          <div className={DataValue}>$2350.00</div>
        </div>
        <div className={DataRow}>
          <div className={DataLabel}>Oil (CL):</div>
          <div className={DataValue}>$85.50</div>
        </div>
        <div className={DataRow}>
          <div className={DataLabel}>S&P 500 (ES):</div>
          <div className={DataValue}>$5150.25</div>
        </div>
      </div>
      
      {/* Это пустой блок, чтобы прижать нижний элемент к низу */}
      <div style={{ flexGrow: 1 }} /> 

      <div className={DataRow} style={{ marginBottom: 0 }}>
        <div className={DataLabel}>Сессия:</div>
        <div className={DataValue}>New York</div>
      </div>

    </div>
  )
}
