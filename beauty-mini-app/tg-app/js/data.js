/* ================================================
   data.js — Данные приложения
   Хочешь изменить контент — редактируй этот файл.
   Здесь: профиль мастера, услуги, портфолио, демо-клиенты.
   ================================================ */

/* ---------- TELEGRAM БОТ ---------- */
/* Замени username на реальный @username бота из @BotFather */
const BOT = {
  username: 'your_beauty_bot',
};

/* ---------- ПРОФИЛЬ МАСТЕРА ---------- */
const MASTER = {
  name:          'Анна Смирнова',
  specialty:     'Мастер ногтевого сервиса',
  emoji:         '💅',
  /* Фото мастера — Unsplash, реальная девушка */
  photo:         'https://images.unsplash.com/photo-1508214751196-bcfd4ca60f91?w=300&h=300&fit=crop&crop=face&q=85',
  rating:        4.9,
  reviewsCount:  127,
  clientsCount:  83,
  workingHours:  '10:00 – 20:00',
  address:       'ул. Невский пр., 14, СПб',
};

/* ---------- УСЛУГИ ---------- */
/* id уникальный, duration в минутах */
const SERVICES = [
  { id: 1, category: 'Маникюр',  name: 'Классический',   price: 1500, duration: 60,  emoji: '💅' },
  { id: 2, category: 'Маникюр',  name: 'Гель-лак',        price: 2200, duration: 90,  emoji: '✨' },
  { id: 3, category: 'Маникюр',  name: 'Наращивание',     price: 3500, duration: 120, emoji: '💎' },
  { id: 4, category: 'Педикюр',  name: 'Классический',   price: 2500, duration: 90,  emoji: '🌸' },
  { id: 5, category: 'Педикюр',  name: 'Аппаратный',      price: 3000, duration: 90,  emoji: '⚡' },
  { id: 6, category: 'Брови',    name: 'Коррекция',       price: 800,  duration: 30,  emoji: '🎨' },
  { id: 7, category: 'Брови',    name: 'Окрашивание',     price: 600,  duration: 20,  emoji: '🖌️' },
  { id: 8, category: 'Брови',    name: 'Коррекция + окрашивание', price: 1200, duration: 45, emoji: '🌟' },
];

/* ---------- ПОРТФОЛИО ---------- */
/* Реальные фото ногтей, скачаны локально в images/ */
const PORTFOLIO = [
  { photo: 'images/nail1.jpg', label: 'Гель-лак' },
  { photo: 'images/nail2.jpg', label: 'Наращивание' },
  { photo: 'images/nail3.jpg', label: 'Французский' },
  { photo: 'images/nail4.jpg', label: 'Омбре' },
  { photo: 'images/nail5.jpg', label: 'Дизайн' },
  { photo: 'images/nail6.jpg', label: 'Нюд' },
];

/* ---------- ДЕМО-КЛИЕНТЫ (режим мастера) ---------- */
const DEMO_CLIENTS = [
  {
    id: 1,
    name: 'Мария Петрова',
    phone: '+7 916 234 56 78',
    emoji: '👩',
    visits: 7,
    since: 'март 2025',
    notes: 'Короткая длина. Аллергия на акрил. Любит пастельные тона.',
    history: [
      { date: '2025-05-15', serviceId: 2, price: 2200 },
      { date: '2025-04-20', serviceId: 1, price: 1500 },
      { date: '2025-03-25', serviceId: 2, price: 2200 },
    ],
  },
  {
    id: 2,
    name: 'Светлана Козлова',
    phone: '+7 903 456 78 90',
    emoji: '👱‍♀️',
    visits: 3,
    since: 'апрель 2025',
    notes: 'Нюдовые оттенки, пастель. Предпочитает миндальную форму.',
    history: [
      { date: '2025-05-20', serviceId: 4, price: 2500 },
      { date: '2025-04-28', serviceId: 2, price: 2200 },
    ],
  },
  {
    id: 3,
    name: 'Елена Новикова',
    phone: '+7 925 678 90 12',
    emoji: '👩‍🦰',
    visits: 12,
    since: 'январь 2025',
    notes: 'Постоянный клиент. Любит чёрно-белые дизайны. Ногти средней длины.',
    history: [
      { date: '2025-05-28', serviceId: 1, price: 1500 },
      { date: '2025-04-30', serviceId: 2, price: 2200 },
      { date: '2025-04-02', serviceId: 1, price: 1500 },
    ],
  },
];

/* ---------- ДЕМО-ЗАПИСИ ---------- */
/* Генерирует несколько записей вокруг текущей даты */
function getDemoBookings() {
  const fmt = (offset = 0) => {
    const d = new Date();
    d.setDate(d.getDate() + offset);
    return d.toISOString().split('T')[0];
  };

  return [
    /* Записи мастера на сегодня */
    { id: 'd1', clientName: 'Мария Петрова',    serviceId: 2, date: fmt(0),  time: '10:00', status: 'active',    isClient: false },
    { id: 'd2', clientName: 'Светлана Козлова', serviceId: 4, date: fmt(0),  time: '14:00', status: 'active',    isClient: false },
    { id: 'd3', clientName: 'Елена Новикова',   serviceId: 1, date: fmt(0),  time: '17:00', status: 'active',    isClient: false },
    /* Записи на завтра */
    { id: 'd4', clientName: 'Анастасия Волкова', serviceId: 2, date: fmt(1), time: '11:00', status: 'active',    isClient: false },
    { id: 'd5', clientName: 'Ирина Соколова',    serviceId: 6, date: fmt(1), time: '15:30', status: 'active',    isClient: false },
    /* Прошлая запись клиента (для «Моих записей») */
    { id: 'd6', clientName: 'Вы',                serviceId: 2, date: fmt(-7), time: '12:00', status: 'done',     isClient: true },
  ];
}