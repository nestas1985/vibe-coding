/* ================================================
   app.js — Основная логика Beauty Mini App
   Навигация, рендер экранов, обработка событий.
   ================================================ */

/* ---------- TELEGRAM SDK ---------- */
const tg = window.Telegram?.WebApp || null;

/* ---------- СОСТОЯНИЕ ---------- */
const S = {
  screen:           'home',     // текущий экран
  history:          [],         // стек для кнопки «Назад»
  selectedService:  null,       // выбранная услуга (объект)
  selectedDate:     null,       // дата YYYY-MM-DD
  selectedTime:     null,       // время HH:MM
  clientName:       '',         // имя клиента (из Telegram или вручную)
  clientPhone:      '',         // телефон
  isMaster:         false,      // режим мастера
  viewClientId:     null,       // id клиента для карточки
  bookings:         [],         // все записи (localStorage)
  masterActiveDay:  null,       // выбранный день в расписании мастера
};

/* ---------- СТАРТ ---------- */
function init() {
  if (tg) {
    tg.ready();
    tg.expand();
    applyTelegramTheme();
    /* Имя из профиля Telegram */
    const user = tg.initDataUnsafe?.user;
    if (user?.first_name) S.clientName = user.first_name;
    /* Кнопка «Назад» Telegram */
    tg.BackButton.onClick(navigateBack);
  }

  /* Единый делегированный обработчик кликов */
  document.getElementById('screen').addEventListener('click', onClickDelegate);

  loadBookings();
  goTo('home');
}

/* ---------- ТЕМА TELEGRAM ---------- */
function applyTelegramTheme() {
  if (!tg?.themeParams) return;
  const t = tg.themeParams;
  const root = document.documentElement;
  const set = (k, v) => v && root.style.setProperty(k, v);

  set('--tg-theme-bg-color',           t.bg_color);
  set('--tg-theme-text-color',         t.text_color);
  set('--tg-theme-hint-color',         t.hint_color);
  set('--tg-theme-link-color',         t.link_color);
  set('--tg-theme-button-color',       t.button_color);
  set('--tg-theme-button-text-color',  t.button_text_color);
  set('--tg-theme-secondary-bg-color', t.secondary_bg_color);

  /* Автоопределение тёмной темы */
  if (t.bg_color) {
    const hex = t.bg_color.replace('#', '');
    const r = parseInt(hex.substr(0, 2), 16);
    const g = parseInt(hex.substr(2, 2), 16);
    const b = parseInt(hex.substr(4, 2), 16);
    if (r * 0.299 + g * 0.587 + b * 0.114 < 128) {
      document.body.classList.add('dark');
    }
  }
}

/* ---------- НАВИГАЦИЯ ---------- */
function goTo(name, dir = 'forward') {
  if (dir === 'forward' && S.screen !== name) {
    S.history.push(S.screen);
  }
  S.screen = name;

  const el = document.getElementById('screen');
  el.innerHTML = renderScreen(name);

  /* Анимация */
  const child = el.firstElementChild;
  if (child) {
    child.classList.add(dir === 'forward' ? 'slide-in-right' : 'slide-in-left');
    setTimeout(() => child.classList.remove('slide-in-right', 'slide-in-left'), 300);
  }

  /* Telegram BackButton */
  if (tg?.BackButton) {
    const noBack = name === 'home' || name === 'master-home' || S.history.length === 0;
    noBack ? tg.BackButton.hide() : tg.BackButton.show();
  }

  /* Scroll top */
  el.querySelector('.scroll-area')?.scrollTo(0, 0);

  haptic();
}

function navigateBack() {
  if (S.history.length === 0) return;
  const prev = S.history.pop();
  goTo(prev, 'back');
}

function haptic(type = 'light') {
  tg?.HapticFeedback?.impactOccurred(type);
}

/* ---------- ДЕЛЕГИРОВАНИЕ СОБЫТИЙ ---------- */
function onClickDelegate(e) {
  const el = e.target.closest('[data-a]');
  if (!el) return;
  haptic();
  const act  = el.dataset.a;
  const val  = el.dataset.v;
  const val2 = el.dataset.v2;
  dispatch(act, val, val2);
}

function dispatch(act, v, v2) {
  switch (act) {
    /* Навигация клиента */
    case 'services':    goTo('services');     break;
    case 'my-bookings': goTo('my-bookings');  break;
    case 'home':        goHome();             break;
    case 'back':        navigateBack();       break;

    /* Выбор услуги */
    case 'pick-service':  pickService(v);     break;
    case 'quick-book':    quickBook(v);       break; /* выбрать и сразу перейти к времени */
    case 'next-datetime': nextDatetime();     break;

    /* Выбор даты/времени */
    case 'pick-date':  pickDate(v);   break;
    case 'pick-time':  pickTime(v);   break;
    case 'next-confirm': nextConfirm(); break;

    /* Подтверждение */
    case 'submit':     submitBooking(); break;

    /* Мои записи */
    case 'cancel-booking': openCancelSheet(v); break;
    case 'cancel-confirm': confirmCancel(v);   break;
    case 'cancel-close':   closeSheet();       break;
    case 'rebook':         rebookService(v);   break;

    /* Режим мастера */
    case 'toggle-master': toggleMaster();       break;
    case 'm-tab':          switchTab(v);        break;
    case 'view-client':    viewClient(v);       break;
    case 'add-booking':    goTo('master-add');  break;
    case 'master-day':     masterPickDay(v);    break;
    case 'submit-manual':  submitManual();      break;
    case 'save-notes':     saveNotes(v);        break;

    default: break;
  }
}

/* ---------- ДЕЙСТВИЯ КЛИЕНТА ---------- */

function goHome() {
  S.history = [];
  goTo(S.isMaster ? 'master-home' : 'home', 'back');
}

function toggleMaster() {
  S.isMaster = !S.isMaster;
  S.history  = [];
  goTo(S.isMaster ? 'master-home' : 'home');
}

/* -- Шаг 1: выбор услуги -- */
function pickService(id) {
  S.selectedService = SERVICES.find(s => s.id === parseInt(id)) || null;

  /* Обновляем карточки без перерендера */
  document.querySelectorAll('.service-card').forEach(card => {
    const sel = card.dataset.v === id;
    card.classList.toggle('selected', sel);
    const ch = card.querySelector('.check-circle');
    if (ch) ch.textContent = sel ? '✓' : '';
  });

  /* Активируем кнопку */
  const btn = document.querySelector('[data-a="next-datetime"]');
  if (btn) btn.disabled = false;
}

function nextDatetime() {
  if (!S.selectedService) return;
  S.selectedDate = null;
  S.selectedTime = null;
  goTo('datetime');
}

/* Выбрать услугу с главного экрана и сразу перейти к выбору времени */
function quickBook(id) {
  S.selectedService = SERVICES.find(s => s.id === parseInt(id)) || null;
  S.selectedDate    = null;
  S.selectedTime    = null;
  if (S.selectedService) goTo('datetime');
}

/* -- Шаг 2: дата и время -- */
function pickDate(date) {
  S.selectedDate = date;
  S.selectedTime = null;

  document.querySelectorAll('.date-pill').forEach(p => {
    p.classList.toggle('selected', p.dataset.v === date);
  });

  /* Перерисовываем только сетку слотов */
  const grid = document.querySelector('.time-grid');
  if (grid) grid.innerHTML = buildTimeSlots(date);

  updateDatetimeBtn();
}

function pickTime(time) {
  S.selectedTime = time;
  document.querySelectorAll('.time-slot:not(.busy)').forEach(s => {
    s.classList.toggle('selected', s.dataset.v === time);
  });
  updateDatetimeBtn();
}

function updateDatetimeBtn() {
  const btn = document.querySelector('[data-a="next-confirm"]');
  if (btn) btn.disabled = !(S.selectedDate && S.selectedTime);
}

function nextConfirm() {
  if (!S.selectedDate || !S.selectedTime) return;
  goTo('confirm');
}

/* -- Шаг 3: подтверждение -- */
function submitBooking() {
  const nameEl  = document.getElementById('inp-name');
  const phoneEl = document.getElementById('inp-phone');

  const name  = nameEl?.value.trim()  || S.clientName;
  const phone = phoneEl?.value.trim() || '';

  if (!name || !phone) {
    haptic('error');
    /* Подсветка пустых полей */
    if (nameEl  && !nameEl.value.trim())  nameEl.style.borderColor  = 'var(--danger)';
    if (phoneEl && !phoneEl.value.trim()) phoneEl.style.borderColor = 'var(--danger)';
    return;
  }

  S.clientName  = name;
  S.clientPhone = phone;

  const booking = {
    id:          'u' + Date.now(),
    clientName:  name,
    clientPhone: phone,
    serviceId:   S.selectedService.id,
    date:        S.selectedDate,
    time:        S.selectedTime,
    status:      'active',
    isClient:    true,
    createdAt:   new Date().toISOString(),
  };

  S.bookings.push(booking);
  saveBookings();

  haptic('success');
  goTo('success');
}

/* -- Отмена записи -- */
function openCancelSheet(id) {
  const sheet = document.createElement('div');
  sheet.className = 'cancel-sheet';
  sheet.id = 'cancel-sheet';
  const b = S.bookings.find(b => b.id === id);
  const svc = b ? getService(b.serviceId) : null;

  sheet.innerHTML = `
    <div class="cancel-inner">
      <p class="cancel-title">Отменить запись?</p>
      <p class="cancel-sub">${svc ? svc.name : 'Запись'} · ${b ? formatDate(b.date) + ', ' + b.time : ''}</p>
      <button class="btn btn-primary" style="background:var(--danger)" data-a="cancel-confirm" data-v="${id}">Да, отменить</button>
      <button class="btn btn-ghost" data-a="cancel-close">Нет, оставить</button>
    </div>
  `;

  document.body.appendChild(sheet);
}

function confirmCancel(id) {
  const b = S.bookings.find(b => b.id === id);
  if (b) b.status = 'cancelled';
  saveBookings();
  closeSheet();
  haptic('medium');
  goTo('my-bookings');
}

function closeSheet() {
  document.getElementById('cancel-sheet')?.remove();
}

function rebookService(serviceId) {
  S.selectedService = SERVICES.find(s => s.id === parseInt(serviceId)) || null;
  S.selectedDate    = null;
  S.selectedTime    = null;
  goTo('datetime');
}

/* ---------- ДЕЙСТВИЯ МАСТЕРА ---------- */

function switchTab(tab) {
  goTo('master-' + tab);
}

function viewClient(clientId) {
  S.viewClientId = parseInt(clientId);
  goTo('master-client');
}

function masterPickDay(date) {
  S.masterActiveDay = date;
  document.querySelectorAll('.date-pill').forEach(p => {
    p.classList.toggle('selected', p.dataset.v === date);
  });
  /* Перерисовать тайм-лайн */
  const tl = document.querySelector('.timeline');
  if (tl) tl.innerHTML = buildTimeline(date);
}

function submitManual() {
  const name  = document.getElementById('m-name')?.value.trim();
  const phone = document.getElementById('m-phone')?.value.trim();
  const svcId = parseInt(document.getElementById('m-service')?.value);
  const date  = document.getElementById('m-date')?.value;
  const time  = document.getElementById('m-time')?.value;

  if (!name || !phone || !svcId || !date || !time) {
    haptic('error');
    return;
  }

  S.bookings.push({
    id:         'm' + Date.now(),
    clientName: name,
    clientPhone: phone,
    serviceId:  svcId,
    date,
    time,
    status:     'active',
    isClient:   false,
  });
  saveBookings();
  haptic('success');
  goTo('master-schedule');
}

function saveNotes(clientId) {
  const ta = document.getElementById('notes-ta');
  if (!ta) return;
  const key = 'notes_' + clientId;
  localStorage.setItem(key, ta.value);
  haptic('medium');
  /* Визуальная обратная связь */
  const btn = document.querySelector('[data-a="save-notes"]');
  if (btn) { btn.textContent = 'Сохранено ✓'; setTimeout(() => { btn.textContent = 'Сохранить заметки'; }, 1500); }
}

/* ---------- ХРАНИЛИЩЕ ---------- */
function loadBookings() {
  try {
    const saved = localStorage.getItem('beauty_bookings');
    S.bookings = saved ? JSON.parse(saved) : [];
    if (!S.bookings.length) {
      S.bookings = getDemoBookings();
      saveBookings();
    }
  } catch (_) {
    S.bookings = getDemoBookings();
  }
}

function saveBookings() {
  localStorage.setItem('beauty_bookings', JSON.stringify(S.bookings));
}

/* ---------- УТИЛИТЫ ---------- */

function getService(id) {
  return SERVICES.find(s => s.id === parseInt(id));
}

function formatDate(str) {
  const d = new Date(str + 'T12:00:00');
  const days   = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
  const months = ['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'];
  return `${days[d.getDay()]}, ${d.getDate()} ${months[d.getMonth()]}`;
}

function formatDuration(min) {
  if (min < 60) return `${min} мин`;
  const h = Math.floor(min / 60), m = min % 60;
  return m ? `${h} ч ${m} мин` : `${h} ч`;
}

function formatPrice(p) {
  return p.toLocaleString('ru-RU') + ' ₽';
}

function today() {
  return new Date().toISOString().split('T')[0];
}

function getDates(count = 14) {
  const days   = ['Вс','Пн','Вт','Ср','Чт','Пт','Сб'];
  const result = [];
  for (let i = 0; i < count; i++) {
    const d = new Date();
    d.setDate(d.getDate() + i);
    result.push({
      str:      d.toISOString().split('T')[0],
      day:      days[d.getDay()],
      num:      d.getDate(),
      weekend:  d.getDay() === 0 || d.getDay() === 6,
    });
  }
  return result;
}

function getTimeSlots() {
  const s = [];
  for (let h = 9; h <= 19; h++) {
    s.push(`${String(h).padStart(2,'0')}:00`);
    if (h < 19) s.push(`${String(h).padStart(2,'0')}:30`);
  }
  return s;
}

/* Детерминированное определение занятого слота (демо) */
function isSlotBusy(dateStr, timeStr) {
  if (S.bookings.some(b => b.date === dateStr && b.time === timeStr && b.status === 'active')) return true;
  const seed = parseInt((dateStr.replace(/-/g,'') + timeStr.replace(':','')).slice(-5));
  return seed % 5 === 0;
}

function groupByCategory(arr) {
  return arr.reduce((acc, s) => {
    (acc[s.category] = acc[s.category] || []).push(s);
    return acc;
  }, {});
}

function getClientActiveBookings() {
  const t = today();
  return S.bookings.filter(b => b.isClient && b.status === 'active' && b.date >= t)
                   .sort((a, b) => (a.date + a.time).localeCompare(b.date + b.time));
}

function getClientPastBookings() {
  const t = today();
  return S.bookings.filter(b => b.isClient && (b.status !== 'active' || b.date < t))
                   .sort((a, b) => (b.date + b.time).localeCompare(a.date + a.time));
}

function getTodayBookings() {
  return S.bookings.filter(b => b.date === today() && b.status === 'active')
                   .sort((a, b) => a.time.localeCompare(b.time));
}

function getBookingsForDay(dateStr) {
  return S.bookings.filter(b => b.date === dateStr && b.status === 'active')
                   .sort((a, b) => a.time.localeCompare(b.time));
}

/* ---------- СТРОИТЕЛИ HTML-ЧАСТЕЙ ---------- */

function buildDateStrip(selectedDate) {
  return getDates(14).map(d => `
    <button class="date-pill${d.str === selectedDate ? ' selected' : ''}${d.weekend ? ' weekend' : ''}"
      data-a="pick-date" data-v="${d.str}">
      <span class="date-day">${d.day}</span>
      <span class="date-num">${d.num}</span>
    </button>
  `).join('');
}

function buildTimeSlots(dateStr) {
  if (!dateStr) return '<p style="padding:16px;color:var(--hint);font-size:14px">Сначала выберите дату ↑</p>';
  return getTimeSlots().map(t => {
    const busy = isSlotBusy(dateStr, t);
    const sel  = t === S.selectedTime;
    return `<button class="time-slot${busy ? ' busy' : ''}${sel ? ' selected' : ''}"
      ${busy ? 'disabled' : ''} data-a="pick-time" data-v="${t}">${t}</button>`;
  }).join('');
}

function buildTimeline(dateStr) {
  const bookings = getBookingsForDay(dateStr);
  const hours = ['9:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00'];

  return hours.map(h => {
    const b = bookings.find(b => {
      const bh = b.time.replace(':00','').replace(':30','');
      return b.time === h || (h.replace(':00','') === bh);
    });
    const svc = b ? getService(b.serviceId) : null;
    return `
      <div class="tl-row">
        <div class="tl-time">${h}</div>
        <div class="tl-slot">
          ${b && svc ? `
            <div class="tl-booking" data-a="view-client" data-v="1">
              <div class="tl-name">${b.clientName}</div>
              <div class="tl-service">${svc.name} · ${formatDuration(svc.duration)}</div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  }).join('');
}

function buildMasterTabs(active) {
  const tabs = [
    { id: 'home',     icon: '🏠', label: 'Главная' },
    { id: 'schedule', icon: '📅', label: 'Расписание' },
    { id: 'clients',  icon: '👥', label: 'Клиенты' },
    { id: 'services', icon: '💅', label: 'Услуги' },
  ];
  return `
    <nav class="master-tabs">
      ${tabs.map(t => `
        <button class="m-tab${t.id === active ? ' active' : ''}" data-a="m-tab" data-v="${t.id}">
          <span class="m-tab-icon">${t.icon}</span>
          ${t.label}
        </button>
      `).join('')}
    </nav>
  `;
}

/* ---------- РЕНДЕР ЭКРАНОВ ---------- */

function renderScreen(name) {
  const screens = {
    'home':            renderHome,
    'services':        renderServices,
    'datetime':        renderDatetime,
    'confirm':         renderConfirm,
    'success':         renderSuccess,
    'my-bookings':     renderMyBookings,
    'master-home':     renderMasterHome,
    'master-schedule': renderMasterSchedule,
    'master-add':      renderMasterAdd,
    'master-client':   renderMasterClient,
    'master-services': renderMasterServices,
    'master-clients':  renderMasterClients,
  };
  return (screens[name] || renderHome)();
}

/* ====== ЭКРАН 01: Профиль мастера ====== */
function renderHome() {
  const preview = SERVICES.slice(0, 3);
  return `
    <div class="screen">
      <div class="header">
        <div class="header-side"></div>
        <span class="header-title">${MASTER.name.split(' ')[0]}</span>
        <div class="header-side right">
          <button class="mode-pill" data-a="toggle-master">💼 Мастер</button>
        </div>
      </div>

      <div class="scroll-area">
        <!-- Профиль -->
        <div class="master-hero">
          <!-- Аватар: сначала загружаем фото, если не грузится — показываем эмодзи -->
          <div class="avatar-photo">
            <img src="${MASTER.photo}" alt="${MASTER.name}"
              onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
            <div class="avatar avatar-hidden">${MASTER.emoji}</div>
          </div>
          <h1 class="master-name">${MASTER.name}</h1>
          <p class="master-spec">${MASTER.specialty}</p>
          <div class="rating-row">
            <span class="stars">★★★★★</span>
            <span class="rating-v">${MASTER.rating}</span>
            <span class="rating-d">·</span>
            <span class="rating-d">${MASTER.reviewsCount} отзывов</span>
          </div>
        </div>

        <!-- Портфолио: CSS-витрины, грузятся всегда -->
        <div class="section">
          <p class="section-title">Портфолио</p>
          <div class="portfolio-grid">
            ${PORTFOLIO.map(p => `
              <div class="portfolio-cell ${p.cssClass}">
                <div class="portfolio-overlay"></div>
                <span class="portfolio-label">${p.label}</span>
              </div>
            `).join('')}
          </div>
        </div>

        <!-- Услуги превью: нажал — сразу переходит к выбору времени -->
        <div class="section">
          <p class="section-title">Услуги</p>
          ${preview.map(s => `
            <div class="service-row" data-a="quick-book" data-v="${s.id}">
              <span class="service-row-name">${s.emoji} ${s.name}</span>
              <span class="service-row-price">${formatPrice(s.price)}</span>
            </div>
          `).join('')}
          <button class="link-btn" data-a="services">Все услуги →</button>
        </div>
        <div class="spacer"></div>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="services">Записаться</button>
        <button class="btn btn-ghost" data-a="my-bookings">Мои записи</button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 02: Выбор услуги ====== */
function renderServices() {
  const groups = groupByCategory(SERVICES);
  return `
    <div class="screen">
      <div class="header">
        <div class="header-side">
          <button class="header-btn" data-a="back">← Назад</button>
        </div>
        <span class="header-title">Услуги</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        ${Object.entries(groups).map(([cat, items]) => `
          <p class="category-label">${cat}</p>
          <div style="margin: 0 16px 16px">
            ${items.map(s => {
              const sel = S.selectedService?.id === s.id;
              return `
                <div class="service-card${sel ? ' selected' : ''}" data-a="pick-service" data-v="${s.id}">
                  <span class="service-emoji">${s.emoji}</span>
                  <div class="service-info">
                    <div class="service-name">${s.name}</div>
                    <div class="service-meta">${formatDuration(s.duration)}</div>
                  </div>
                  <div class="service-right">
                    <span class="service-price">${formatPrice(s.price)}</span>
                    <div class="check-circle">${sel ? '✓' : ''}</div>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        `).join('')}
        <div class="spacer"></div>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="next-datetime" ${S.selectedService ? '' : 'disabled'}>
          Выбрать время
        </button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 03: Дата и время ====== */
function renderDatetime() {
  const s = S.selectedService;
  return `
    <div class="screen">
      <div class="header">
        <div class="header-side">
          <button class="header-btn" data-a="back">← Назад</button>
        </div>
        <span class="header-title">Выберите время</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        <!-- Напоминание о выбранной услуге -->
        ${s ? `<div class="chip">${s.emoji} ${s.name} · ${formatPrice(s.price)}</div>` : ''}

        <!-- Дата -->
        <div class="section" style="padding-bottom:12px">
          <p class="section-title">Дата</p>
        </div>
        <div class="date-wrap">
          <div class="date-strip">
            ${buildDateStrip(S.selectedDate)}
          </div>
        </div>

        <!-- Время -->
        <div class="section" style="padding: 16px 0 10px 16px">
          <p class="section-title">Время ${S.selectedDate ? '· ' + formatDate(S.selectedDate) : ''}</p>
        </div>
        <div class="time-grid">
          ${buildTimeSlots(S.selectedDate)}
        </div>
        <div class="spacer"></div>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="next-confirm" ${(S.selectedDate && S.selectedTime) ? '' : 'disabled'}>
          Подтвердить
        </button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 04: Подтверждение ====== */
function renderConfirm() {
  const s = S.selectedService;
  return `
    <div class="screen">
      <div class="header">
        <div class="header-side">
          <button class="header-btn" data-a="back">← Назад</button>
        </div>
        <span class="header-title">Подтверждение</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        <div style="padding: 8px 16px 16px">
          <!-- Сводка записи -->
          <div class="card" style="margin-bottom:20px">
            <div class="card-row">
              <span class="card-icon">💅</span>
              <span class="card-label">${s?.name}</span>
              <span class="card-value accent">${formatPrice(s?.price || 0)}</span>
            </div>
            <div class="card-row">
              <span class="card-icon">📅</span>
              <span class="card-label">${formatDate(S.selectedDate)}</span>
              <span class="card-value">${S.selectedTime}</span>
            </div>
            <div class="card-row">
              <span class="card-icon">⏱</span>
              <span class="card-label">Длительность</span>
              <span class="card-value">${formatDuration(s?.duration || 0)}</span>
            </div>
            <div class="card-row">
              <span class="card-icon">📍</span>
              <span class="card-label">${MASTER.address}</span>
            </div>
          </div>
        </div>

        <!-- Данные клиента -->
        <div class="field-group">
          <label class="field-label">Ваше имя</label>
          <input id="inp-name" class="field-input" type="text" placeholder="Имя" value="${S.clientName}" autocomplete="given-name">
        </div>
        <div class="field-group">
          <label class="field-label">Телефон</label>
          <input id="inp-phone" class="field-input" type="tel" placeholder="+7 000 000-00-00" value="${S.clientPhone}" autocomplete="tel">
        </div>

        <p style="font-size:12px;color:var(--hint);padding:0 16px 20px;line-height:1.5">
          Напомним за 24 часа и за 2 часа до визита через бота.
        </p>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="submit">Записаться</button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 04а: Успех ====== */
function renderSuccess() {
  const s = S.selectedService;
  return `
    <div class="screen fade-in">
      <div class="success-body">
        <div class="success-icon">🎉</div>
        <h1 class="success-title">Вы записаны!</h1>

        <div class="success-card">
          <div class="sc-row"><span>💅</span><span>${s?.name}</span></div>
          <div class="sc-row"><span>📅</span><span>${formatDate(S.selectedDate)}, ${S.selectedTime}</span></div>
          <div class="sc-row"><span>💰</span><span>${formatPrice(s?.price || 0)}</span></div>
          <div class="sc-row"><span>📍</span><span>${MASTER.address}</span></div>
        </div>

        <p class="success-note">
          Напомним за 24 часа и за 2 часа до визита через Telegram-бота.
        </p>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="my-bookings">Мои записи</button>
        <button class="btn btn-ghost" data-a="home">На главную</button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 05: Мои записи ====== */
function renderMyBookings() {
  const active = getClientActiveBookings();
  const past   = getClientPastBookings();

  return `
    <div class="screen">
      <div class="header">
        <div class="header-side">
          <button class="header-btn" data-a="back">← Назад</button>
        </div>
        <span class="header-title">Мои записи</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        <!-- Предстоящие -->
        <div class="section">
          <p class="section-title">Предстоящие</p>
          ${active.length ? active.map(b => {
            const s = getService(b.serviceId);
            return `
              <div class="booking-card">
                <div class="bc-date">${formatDate(b.date)} · ${b.time}</div>
                <div class="bc-service">${s?.emoji || '💅'} ${s?.name}</div>
                <div class="bc-meta">${formatPrice(s?.price || 0)} · ${formatDuration(s?.duration || 0)}</div>
                <div class="bc-actions">
                  <button class="btn-danger-ghost" data-a="cancel-booking" data-v="${b.id}">Отменить</button>
                </div>
              </div>
            `;
          }).join('') : `
            <div class="empty">
              <div class="empty-icon">📋</div>
              <p class="empty-title">Нет записей</p>
              <p class="empty-sub">У вас пока нет предстоящих записей.</p>
            </div>
          `}
        </div>

        <!-- История -->
        ${past.length ? `
          <div class="section">
            <p class="section-title">История</p>
            ${past.map(b => {
              const s = getService(b.serviceId);
              return `
                <div class="booking-card">
                  <div class="bc-date" style="color:var(--hint)">${formatDate(b.date)} · ${b.time}</div>
                  <div class="bc-service">${s?.emoji || '💅'} ${s?.name}</div>
                  <div class="bc-meta">${formatPrice(s?.price || 0)}</div>
                  <div class="bc-actions">
                    <button class="btn btn-secondary" style="height:40px;font-size:14px;width:auto;padding:0 16px"
                      data-a="rebook" data-v="${b.serviceId}">Записаться снова</button>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        ` : ''}

        <div class="spacer"></div>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="home">Записаться</button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 06: Дашборд мастера ====== */
function renderMasterHome() {
  const todayB = getTodayBookings();
  const total  = todayB.reduce((s, b) => s + (getService(b.serviceId)?.price || 0), 0);
  const h = new Date().getHours();
  const greeting = h < 12 ? 'Доброе утро' : h < 18 ? 'Добрый день' : 'Добрый вечер';

  return `
    <div class="screen">
      <div class="header">
        <div class="header-side"></div>
        <span class="header-title">Главная</span>
        <div class="header-side right">
          <button class="mode-pill" data-a="toggle-master">👤 Выход</button>
        </div>
      </div>

      <div class="scroll-area">
        <div class="greeting">
          <div class="greeting-name">${greeting}, ${MASTER.name.split(' ')[0]}! 👋</div>
          <div class="greeting-sub">${new Date().toLocaleDateString('ru-RU', {weekday:'long', day:'numeric', month:'long'})}</div>
        </div>

        <!-- Статистика -->
        <div class="stats-row">
          <div class="stat-card accent-card">
            <div class="stat-num">${todayB.length}</div>
            <div class="stat-label">записей сегодня</div>
          </div>
          <div class="stat-card">
            <div class="stat-num">${formatPrice(total)}</div>
            <div class="stat-label">выручка дня</div>
          </div>
        </div>

        <!-- Записи сегодня -->
        <div class="section" style="padding-bottom:6px">
          <p class="section-title">Сегодня</p>
        </div>
        ${todayB.length ? todayB.map(b => {
          const s = getService(b.serviceId);
          return `
            <div class="master-booking-row" data-a="view-client" data-v="1">
              <div class="time-badge">${b.time}</div>
              <div class="mbr-info">
                <div class="mbr-name">${b.clientName}</div>
                <div class="mbr-service">${s?.name}</div>
              </div>
              <div class="mbr-price">${formatPrice(s?.price || 0)}</div>
            </div>
          `;
        }).join('') : `
          <div class="empty" style="padding:32px 24px">
            <div class="empty-icon">🌙</div>
            <p class="empty-title">Записей нет</p>
            <p class="empty-sub">Сегодня свободный день</p>
          </div>
        `}
        <div class="spacer"></div>
      </div>

      ${buildMasterTabs('home')}
    </div>
  `;
}

/* ====== ЭКРАН 07: Расписание мастера ====== */
function renderMasterSchedule() {
  const activeDay = S.masterActiveDay || today();

  return `
    <div class="screen">
      <div class="header">
        <div class="header-side"></div>
        <span class="header-title">Расписание</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        <!-- Полоса дней -->
        <div class="date-wrap" style="padding-top:8px">
          <div class="date-strip">
            ${getDates(7).map(d => `
              <button class="date-pill${d.str === activeDay ? ' selected' : ''}${d.weekend ? ' weekend' : ''}"
                data-a="master-day" data-v="${d.str}">
                <span class="date-day">${d.day}</span>
                <span class="date-num">${d.num}</span>
              </button>
            `).join('')}
          </div>
        </div>

        <div style="padding:16px 16px 8px">
          <p class="section-title">Записи · ${formatDate(activeDay)}</p>
        </div>

        <!-- Тайм-лайн -->
        <div class="timeline">
          ${buildTimeline(activeDay)}
        </div>
        <div style="height:80px"></div>
      </div>

      <!-- Кнопка добавить -->
      <button class="fab" data-a="add-booking">+</button>

      ${buildMasterTabs('schedule')}
    </div>
  `;
}

/* ====== ЭКРАН 08: Добавить запись (мастер) ====== */
function renderMasterAdd() {
  const t = today();
  return `
    <div class="screen">
      <div class="header">
        <div class="header-side">
          <button class="header-btn" data-a="back">← Назад</button>
        </div>
        <span class="header-title">Новая запись</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area" style="padding-top:8px">
        <div class="field-group">
          <label class="field-label">Имя клиента</label>
          <input id="m-name" class="field-input" type="text" placeholder="Мария Петрова" autocomplete="name">
        </div>
        <div class="field-group">
          <label class="field-label">Телефон</label>
          <input id="m-phone" class="field-input" type="tel" placeholder="+7 916 000 00 00" autocomplete="tel">
        </div>
        <div class="field-group">
          <label class="field-label">Услуга</label>
          <select id="m-service" class="field-input" style="appearance:none;-webkit-appearance:none">
            <option value="">Выбрать услугу...</option>
            ${SERVICES.map(s => `<option value="${s.id}">${s.name} — ${formatPrice(s.price)}</option>`).join('')}
          </select>
        </div>
        <div class="field-group">
          <label class="field-label">Дата</label>
          <input id="m-date" class="field-input" type="date" value="${t}" min="${t}">
        </div>
        <div class="field-group">
          <label class="field-label">Время</label>
          <select id="m-time" class="field-input" style="appearance:none;-webkit-appearance:none">
            ${getTimeSlots().map(t => `<option value="${t}">${t}</option>`).join('')}
          </select>
        </div>
        <div class="spacer"></div>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="submit-manual">Создать запись</button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 09: Карточка клиента ====== */
function renderMasterClient() {
  const c = DEMO_CLIENTS.find(c => c.id === S.viewClientId) || DEMO_CLIENTS[0];
  const savedNotes = localStorage.getItem('notes_' + c.id) || c.notes;

  return `
    <div class="screen">
      <div class="header">
        <div class="header-side">
          <button class="header-btn" data-a="back">← Назад</button>
        </div>
        <span class="header-title">Клиент</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        <div class="client-hero">
          <div class="client-avatar">${c.emoji}</div>
          <div class="client-name">${c.name}</div>
          <div class="client-stats">${c.visits} визитов · с ${c.since}</div>
        </div>

        <!-- Контакт -->
        <div class="section">
          <p class="section-title">Контакты</p>
          <div class="card">
            <div class="card-row">
              <span class="card-icon">📞</span>
              <span class="card-label">${c.phone}</span>
            </div>
          </div>
        </div>

        <!-- Заметки -->
        <div class="section">
          <p class="section-title">Заметки</p>
          <textarea id="notes-ta" class="field-textarea" placeholder="Предпочтения, аллергии...">${savedNotes}</textarea>
          <div style="margin-top:8px">
            <button class="btn btn-secondary" style="height:44px;font-size:14px" data-a="save-notes" data-v="${c.id}">
              Сохранить заметки
            </button>
          </div>
        </div>

        <!-- История -->
        <div class="section">
          <p class="section-title">История визитов</p>
          <div class="card">
            ${c.history.map(h => {
              const s = getService(h.serviceId);
              return `
                <div class="card-row">
                  <div class="history-left">
                    <div class="h-date">${formatDate(h.date)}</div>
                    <div class="h-service">${s?.name}</div>
                  </div>
                  <span class="h-price">${formatPrice(h.price)}</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <div class="spacer"></div>
      </div>

      <div class="bottom-bar">
        <button class="btn btn-primary" data-a="add-booking">Записать снова</button>
      </div>
    </div>
  `;
}

/* ====== ЭКРАН 10: Управление услугами ====== */
function renderMasterServices() {
  const groups = groupByCategory(SERVICES);

  return `
    <div class="screen">
      <div class="header">
        <div class="header-side"></div>
        <span class="header-title">Услуги</span>
        <div class="header-side right">
          <button class="header-btn">+ Добавить</button>
        </div>
      </div>

      <div class="scroll-area">
        ${Object.entries(groups).map(([cat, items]) => `
          <p class="category-label">${cat}</p>
          <div style="margin: 0 16px 16px">
            ${items.map(s => `
              <div class="manage-card">
                <span style="font-size:22px">${s.emoji}</span>
                <div class="manage-info">
                  <div class="manage-name">${s.name}</div>
                  <div class="manage-meta">${formatDuration(s.duration)}</div>
                </div>
                <span class="manage-price">${formatPrice(s.price)}</span>
                <button class="edit-btn">✏️</button>
              </div>
            `).join('')}
          </div>
        `).join('')}
        <div class="spacer"></div>
      </div>

      ${buildMasterTabs('services')}
    </div>
  `;
}

/* ====== СПИСОК КЛИЕНТОВ ====== */
function renderMasterClients() {
  return `
    <div class="screen">
      <div class="header">
        <div class="header-side"></div>
        <span class="header-title">Клиенты</span>
        <div class="header-side right"></div>
      </div>

      <div class="scroll-area">
        <div class="section" style="padding-top:16px">
          ${DEMO_CLIENTS.map(c => `
            <div class="master-booking-row" style="margin:0 0 8px;background:var(--secondary-bg);border-radius:var(--r-lg)"
              data-a="view-client" data-v="${c.id}">
              <div class="avatar-sm">${c.emoji}</div>
              <div class="mbr-info">
                <div class="mbr-name">${c.name}</div>
                <div class="mbr-service">${c.visits} визитов · с ${c.since}</div>
              </div>
              <span style="color:var(--hint);font-size:20px">›</span>
            </div>
          `).join('')}
        </div>
        <div class="spacer"></div>
      </div>

      ${buildMasterTabs('clients')}
    </div>
  `;
}

/* ---------- ЗАПУСК ---------- */
window.addEventListener('DOMContentLoaded', init);
