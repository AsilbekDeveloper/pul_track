// Lightweight client-side i18n (uz / en / ru) + dark/light theme.
// No build step — translations are applied by walking [data-i18n] attributes.

const LANG_KEY = "pt_lang";
const THEME_KEY = "pt_theme";

const DICT = {
  uz: {
    app_name: "PulTrack", app_tagline: "Biznes moliya",
    nav_overview: "Umumiy", nav_transactions: "Tranzaksiyalar", nav_analytics: "Analitika",
    nav_categories: "Kategoriyalar", nav_budgets: "Byudjet", nav_logout: "Chiqish →",

    login_title: "Dashboard'ga kiring",
    login_sub: "Telegram akkountingiz bilan kiring — faqat o'z ma'lumotlaringizni ko'rasiz.",
    login_bot_missing: "Bot username config.js da sozlanmagan",
    login_dev_label: "Lokal test (dev-login)",
    login_dev_button: "Kirish",
    login_dev_hint: "Demo ma'lumot uchun id = 1",

    ov_title: "Umumiy ko'rinish",
    ov_kpi_income: "Bu oy · Daromad", ov_kpi_expense: "Bu oy · Xarajat", ov_kpi_net: "Bu oy · Sof foyda",
    ov_vs_last: "o'tgan oyga nisbatan", ov_no_last: "o'tgan oy ma'lumoti yo'q",
    ov_quick_add: "Tez qo'shish", ov_expense: "Xarajat", ov_income: "Daromad",
    ov_amount_ph: "Summa (so'm)", ov_category_ph: "Kategoriya (ixtiyoriy)", ov_note_ph: "Izoh (ixtiyoriy)",
    ov_add_btn: "Qo'shish", ov_recent: "So'nggi tranzaksiyalar", ov_see_all: "Barchasini ko'rish →",
    ov_no_tx: "Hali tranzaksiya yo'q", ov_added: "Qo'shildi ✅", ov_enter_amount: "Summani kiriting",
    ov_over_budget: "limitdan oshdi!", ov_near_budget: "limitga yaqinlashyapti", ov_budget_word: "byudjeti",
    ov_no_category: "Kategoriyasiz",

    tx_title: "Tranzaksiyalar", tx_search: "Qidiruv", tx_search_ph: "Izoh yoki kategoriya",
    tx_type: "Turi", tx_all: "Barchasi", tx_category: "Kategoriya", tx_from: "Dan", tx_to: "Gacha",
    tx_filter: "Filtrlash", tx_clear: "Tozalash", tx_col_date: "Sana", tx_col_type: "Turi",
    tx_col_category: "Kategoriya", tx_col_note: "Izoh", tx_col_amount: "Summa",
    tx_not_found: "Tranzaksiya topilmadi", tx_confirm_delete: "O'chirilsinmi?",
    tx_deleted: "O'chirildi 🗑", tx_saved: "Saqlandi ✅", tx_export: "CSV yuklab olish",
    tx_export_empty: "Eksport uchun ma'lumot yo'q",

    an_title: "Analitika", an_trend: "Daromad vs Xarajat (oxirgi 6 oy)", an_by_category: "Kategoriyalar bo'yicha",
    an_this_month: "Bu oy", an_last_month: "O'tgan oy", an_this_year: "Bu yil", an_all: "Umumiy",
    an_dist_table: "Taqsimot jadvali", an_no_data: "Ma'lumot yo'q",

    cat_title: "Kategoriyalar", cat_income: "Daromad kategoriyalari", cat_expense: "Xarajat kategoriyalari",
    cat_new_ph: "Yangi kategoriya", cat_standard: "standart", cat_empty: "Yo'q",
    cat_name_required: "Nom kiriting", cat_added: "Qo'shildi ✅", cat_deleted: "O'chirildi 🗑",

    bg_title: "Byudjet", bg_new: "Yangi byudjet belgilash", bg_month: "Oy", bg_category: "Kategoriya",
    bg_overall: "Umumiy (barcha xarajat)", bg_limit: "Limit (so'm)", bg_limit_ph: "masalan 2000000",
    bg_save: "Saqlash", bg_current: "Joriy oy byudjetlari", bg_none: "Bu oy uchun byudjet belgilanmagan",
    bg_over: "⚠️ Limitdan oshdi", bg_near: "⚠️ Limitga yaqinlashmoqda", bg_enter_limit: "Limitni kiriting",
    bg_saved: "Saqlandi ✅", bg_confirm_delete: "Byudjet o'chirilsinmi?", bg_deleted: "O'chirildi 🗑",

    common_refresh: "Yangilash", common_waking: "🌙 Server uyg'onmoqda (bepul tarif) — biroz kuting...",
    common_no_connection: "Serverga ulanib bo'lmadi", common_error: "Xatolik yuz berdi",
  },
  ru: {
    app_name: "PulTrack", app_tagline: "Финансы бизнеса",
    nav_overview: "Обзор", nav_transactions: "Транзакции", nav_analytics: "Аналитика",
    nav_categories: "Категории", nav_budgets: "Бюджет", nav_logout: "Выход →",

    login_title: "Войдите в дашборд",
    login_sub: "Войдите через Telegram — вы увидите только свои данные.",
    login_bot_missing: "Имя бота не задано в config.js",
    login_dev_label: "Локальный тест (dev-login)",
    login_dev_button: "Войти",
    login_dev_hint: "Для демо-данных id = 1",

    ov_title: "Обзор",
    ov_kpi_income: "Этот месяц · Доход", ov_kpi_expense: "Этот месяц · Расход", ov_kpi_net: "Этот месяц · Прибыль",
    ov_vs_last: "по сравнению с прошлым месяцем", ov_no_last: "нет данных за прошлый месяц",
    ov_quick_add: "Быстрое добавление", ov_expense: "Расход", ov_income: "Доход",
    ov_amount_ph: "Сумма (сум)", ov_category_ph: "Категория (необязательно)", ov_note_ph: "Заметка (необязательно)",
    ov_add_btn: "Добавить", ov_recent: "Последние транзакции", ov_see_all: "Смотреть все →",
    ov_no_tx: "Транзакций пока нет", ov_added: "Добавлено ✅", ov_enter_amount: "Введите сумму",
    ov_over_budget: "превышен лимит!", ov_near_budget: "приближается к лимиту", ov_budget_word: "бюджет",
    ov_no_category: "Без категории",

    tx_title: "Транзакции", tx_search: "Поиск", tx_search_ph: "Заметка или категория",
    tx_type: "Тип", tx_all: "Все", tx_category: "Категория", tx_from: "С", tx_to: "По",
    tx_filter: "Фильтр", tx_clear: "Очистить", tx_col_date: "Дата", tx_col_type: "Тип",
    tx_col_category: "Категория", tx_col_note: "Заметка", tx_col_amount: "Сумма",
    tx_not_found: "Транзакции не найдены", tx_confirm_delete: "Удалить?",
    tx_deleted: "Удалено 🗑", tx_saved: "Сохранено ✅", tx_export: "Скачать CSV",
    tx_export_empty: "Нет данных для экспорта",

    an_title: "Аналитика", an_trend: "Доход и расход (последние 6 месяцев)", an_by_category: "По категориям",
    an_this_month: "Этот месяц", an_last_month: "Прошлый месяц", an_this_year: "Этот год", an_all: "Всего",
    an_dist_table: "Таблица распределения", an_no_data: "Нет данных",

    cat_title: "Категории", cat_income: "Категории доходов", cat_expense: "Категории расходов",
    cat_new_ph: "Новая категория", cat_standard: "стандарт", cat_empty: "Нет",
    cat_name_required: "Введите название", cat_added: "Добавлено ✅", cat_deleted: "Удалено 🗑",

    bg_title: "Бюджет", bg_new: "Задать новый бюджет", bg_month: "Месяц", bg_category: "Категория",
    bg_overall: "Общий (все расходы)", bg_limit: "Лимит (сум)", bg_limit_ph: "например 2000000",
    bg_save: "Сохранить", bg_current: "Бюджеты текущего месяца", bg_none: "Бюджет на этот месяц не задан",
    bg_over: "⚠️ Лимит превышен", bg_near: "⚠️ Приближается к лимиту", bg_enter_limit: "Введите лимит",
    bg_saved: "Сохранено ✅", bg_confirm_delete: "Удалить бюджет?", bg_deleted: "Удалено 🗑",

    common_refresh: "Обновить", common_waking: "🌙 Сервер просыпается (бесплатный тариф) — подождите...",
    common_no_connection: "Не удалось подключиться к серверу", common_error: "Произошла ошибка",
  },
  en: {
    app_name: "PulTrack", app_tagline: "Business finance",
    nav_overview: "Overview", nav_transactions: "Transactions", nav_analytics: "Analytics",
    nav_categories: "Categories", nav_budgets: "Budget", nav_logout: "Logout →",

    login_title: "Sign in to the dashboard",
    login_sub: "Sign in with Telegram — you'll only see your own data.",
    login_bot_missing: "Bot username not configured in config.js",
    login_dev_label: "Local test (dev-login)",
    login_dev_button: "Sign in",
    login_dev_hint: "Use id = 1 for demo data",

    ov_title: "Overview",
    ov_kpi_income: "This month · Income", ov_kpi_expense: "This month · Expense", ov_kpi_net: "This month · Net",
    ov_vs_last: "vs. last month", ov_no_last: "no data for last month",
    ov_quick_add: "Quick add", ov_expense: "Expense", ov_income: "Income",
    ov_amount_ph: "Amount", ov_category_ph: "Category (optional)", ov_note_ph: "Note (optional)",
    ov_add_btn: "Add", ov_recent: "Recent transactions", ov_see_all: "See all →",
    ov_no_tx: "No transactions yet", ov_added: "Added ✅", ov_enter_amount: "Enter an amount",
    ov_over_budget: "over limit!", ov_near_budget: "approaching limit", ov_budget_word: "budget",
    ov_no_category: "No category",

    tx_title: "Transactions", tx_search: "Search", tx_search_ph: "Note or category",
    tx_type: "Type", tx_all: "All", tx_category: "Category", tx_from: "From", tx_to: "To",
    tx_filter: "Filter", tx_clear: "Clear", tx_col_date: "Date", tx_col_type: "Type",
    tx_col_category: "Category", tx_col_note: "Note", tx_col_amount: "Amount",
    tx_not_found: "No transactions found", tx_confirm_delete: "Delete this?",
    tx_deleted: "Deleted 🗑", tx_saved: "Saved ✅", tx_export: "Download CSV",
    tx_export_empty: "No data to export",

    an_title: "Analytics", an_trend: "Income vs Expense (last 6 months)", an_by_category: "By category",
    an_this_month: "This month", an_last_month: "Last month", an_this_year: "This year", an_all: "All time",
    an_dist_table: "Breakdown table", an_no_data: "No data",

    cat_title: "Categories", cat_income: "Income categories", cat_expense: "Expense categories",
    cat_new_ph: "New category", cat_standard: "default", cat_empty: "None",
    cat_name_required: "Enter a name", cat_added: "Added ✅", cat_deleted: "Deleted 🗑",

    bg_title: "Budget", bg_new: "Set a new budget", bg_month: "Month", bg_category: "Category",
    bg_overall: "Overall (all expenses)", bg_limit: "Limit", bg_limit_ph: "e.g. 2000000",
    bg_save: "Save", bg_current: "This month's budgets", bg_none: "No budget set for this month",
    bg_over: "⚠️ Over limit", bg_near: "⚠️ Approaching limit", bg_enter_limit: "Enter a limit",
    bg_saved: "Saved ✅", bg_confirm_delete: "Delete this budget?", bg_deleted: "Deleted 🗑",

    common_refresh: "Refresh", common_waking: "🌙 Server is waking up (free tier) — please wait...",
    common_no_connection: "Could not connect to the server", common_error: "Something went wrong",
  },
};

function getLang() {
  return localStorage.getItem(LANG_KEY) || "uz";
}
function setLang(lang) {
  localStorage.setItem(LANG_KEY, lang);
  location.reload();
}
function t(key) {
  const lang = getLang();
  return (DICT[lang] && DICT[lang][key]) || DICT.uz[key] || key;
}

// Walks the DOM applying translations to [data-i18n] (textContent),
// [data-i18n-ph] (placeholder) and [data-i18n-title] (title attr).
function applyI18n(root = document) {
  root.querySelectorAll("[data-i18n]").forEach(el => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll("[data-i18n-ph]").forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  root.querySelectorAll("[data-i18n-title]").forEach(el => { el.title = t(el.dataset.i18nTitle); });
}

// ---- Theme (dark/light) ----
function getTheme() { return localStorage.getItem(THEME_KEY) || "light"; }
function applyTheme(theme) {
  document.documentElement.classList.toggle("dark", theme === "dark");
}
function toggleTheme() {
  const next = getTheme() === "dark" ? "light" : "dark";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
  document.querySelectorAll(".btn-theme-toggle").forEach(btn => {
    btn.textContent = next === "dark" ? "☀️" : "🌙";
  });
}

// Apply theme immediately (before paint) to avoid a light->dark flash.
applyTheme(getTheme());
