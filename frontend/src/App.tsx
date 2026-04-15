import { useState, useCallback } from "react";
import { ChatWidget } from "./components/ChatWidget";

function isEmbedMode(): boolean {
  if (typeof window === "undefined") return false;
  const q = new URLSearchParams(window.location.search);
  if (q.get("embed") === "1" || q.get("embed") === "true") return true;
  return window.location.pathname.replace(/\/$/, "") === "/embed";
}

const SERVICES = [
  {
    title: "Монтаж котельной",
    items: ["Настенные котлы", "Напольные котлы", "Автоматизация котельных", "Тепловые насосы", "Ремонт и сервис"],
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.362 5.214A8.252 8.252 0 0112 21 8.25 8.25 0 016.038 7.048 8.287 8.287 0 009 9.6a8.983 8.983 0 013.361-6.867 8.21 8.21 0 003 2.48z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 18a3.75 3.75 0 00.495-7.467 5.99 5.99 0 00-1.925 3.546 5.974 5.974 0 01-2.133-1A3.75 3.75 0 0012 18z" />
      </svg>
    ),
  },
  {
    title: "Монтаж отопления",
    items: ["Радиаторы", "Тёплый пол", "Внутрипольные конвекторы", "Плинтусное отопление", "Тёплые стены"],
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
      </svg>
    ),
  },
  {
    title: "Водоснабжение",
    items: ["Водоснабжение дома", "Бурение скважин", "Монтаж кессона", "Водоочистка", "Обустройство скважин"],
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
      </svg>
    ),
  },
  {
    title: "Электричество",
    items: ["Электропроводка", "Электрика в деревянных домах", "Электрощиты", "Уличное освещение", "Видеонаблюдение"],
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
      </svg>
    ),
  },
  {
    title: "Канализация",
    items: ["Автономная канализация", "Ливневая канализация", "Монтаж септика", "Внутренняя и наружная", "Установка колец"],
    icon: (
      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17l-5.384 3.073A2.625 2.625 0 012.625 15.87V8.13a2.625 2.625 0 013.41-2.373l5.385 3.074m0 0l5.384-3.073A2.625 2.625 0 0120.375 8.13v7.74a2.625 2.625 0 01-3.41 2.373l-5.385-3.073m0 0L12 12.75" />
      </svg>
    ),
  },
];

const STEPS = [
  { num: "01", title: "Заявка на сайте", desc: "При первом звонке выясняем задачу. Подготавливаем инженерный расчёт." },
  { num: "02", title: "Бесплатный выезд", desc: "Направляем инженера на объект, чтобы лучше понять задачу." },
  { num: "03", title: "Инженерное решение", desc: "Составляем решение и презентуем его лично или по телефону." },
  { num: "04", title: "Смета и бюджет", desc: "Составляем смету и расчёт под ваш бюджет." },
  { num: "05", title: "Монтаж оборудования", desc: "Берём оборудование со склада и докупаем недостающее." },
  { num: "06", title: "Оплата по факту", desc: "Берём оплату только после того, как вам всё понравится." },
];

const STATS = [
  { value: "1912+", label: "Объектов смонтировано" },
  { value: "10+", label: "Лет на рынке" },
  { value: "12", label: "Бригад монтажников" },
  { value: "9", label: "Инженеров" },
];

export default function App() {
  const [chatOpen, setChatOpen] = useState(false);
  const openChat = useCallback(() => setChatOpen(true), []);

  if (isEmbedMode()) {
    return <ChatWidget />;
  }

  return (
    <div className="min-h-screen bg-white text-gray-900">
      {/* NAV */}
      <nav className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-gray-100 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <a href="https://gkproject.ru" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2">
            <img src="/logo-gk.png" alt="ГК Проект" className="h-11 w-auto" />
          </a>
          <div className="flex items-center gap-4 sm:gap-6">
            <a href="https://gkproject.ru" target="_blank" rel="noopener noreferrer" className="text-sm text-gray-500 hover:text-brand-600 transition-colors hidden md:inline">
              gkproject.ru
            </a>
            <a href="tel:+74959087474" className="text-brand-600 font-semibold text-sm hover:text-brand-500 transition-colors">
              +7 495 908-74-74
            </a>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <section className="relative overflow-hidden bg-gradient-to-br from-brand-600 via-brand-700 to-brand-800 text-white">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-10 left-10 w-72 h-72 bg-white rounded-full blur-3xl" />
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-accent-400 rounded-full blur-3xl" />
        </div>
        <div className="relative max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="inline-block bg-accent-400/20 text-accent-400 text-xs font-semibold px-3 py-1 rounded-full mb-6 border border-accent-400/30">
            Скидка 15% при заказе под ключ
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight max-w-3xl mb-6">
            Инженерные системы для частных домов и&nbsp;предприятий
          </h1>
          <p className="text-lg sm:text-xl text-brand-200 max-w-2xl mb-8 leading-relaxed">
            Котельные, отопление, водоснабжение, электрика, канализация.
            Проектирование и монтаж под ключ в Москве и области.
          </p>
          <button
            onClick={openChat}
            className="inline-flex items-center justify-center gap-2 px-8 py-3.5 bg-accent-400 hover:bg-accent-500 text-white font-semibold rounded-lg transition-colors text-sm shadow-lg shadow-accent-400/30"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Задать вопрос
          </button>
        </div>
      </section>

      {/* ADVANTAGES */}
      <section className="py-12 sm:py-16 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {[
              { icon: "👷", title: "Команда профессионалов", desc: "12 бригад, 9 инженеров, 2 проектировщика" },
              { icon: "🛡️", title: "Гарантия до 10 лет", desc: "Работа по договору с гарантией на оборудование" },
              { icon: "📋", title: "Работаем по СНиП", desc: "Регламентированные работы одобрены производителями" },
              { icon: "💰", title: "Без предоплат", desc: "С фиксацией цены и сроков исполнения" },
            ].map((item) => (
              <div key={item.title} className="bg-white p-5 sm:p-6 rounded-xl shadow-sm border border-gray-100 hover:shadow-md transition-shadow">
                <span className="text-2xl mb-3 block">{item.icon}</span>
                <h3 className="font-semibold text-brand-600 text-sm sm:text-base mb-1">{item.title}</h3>
                <p className="text-xs sm:text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SERVICES */}
      <section className="py-12 sm:py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-10 sm:mb-14">
            <h2 className="text-2xl sm:text-3xl font-bold text-brand-600 mb-3">
              Монтируем, проектируем, снабжаем
            </h2>
            <p className="text-gray-500 text-sm sm:text-base">Делаем под ключ — от проекта до сдачи</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
            {SERVICES.map((s) => (
              <div
                key={s.title}
                className="group bg-white border border-gray-100 rounded-xl p-6 hover:border-brand-300 hover:shadow-lg transition-all"
              >
                <div className="w-12 h-12 bg-accent-50 text-accent-400 rounded-lg flex items-center justify-center mb-4 group-hover:bg-accent-400 group-hover:text-white transition-colors">
                  {s.icon}
                </div>
                <h3 className="font-bold text-lg text-gray-900 mb-3">{s.title}</h3>
                <ul className="space-y-1.5">
                  {s.items.map((it) => (
                    <li key={it} className="text-sm text-gray-500 flex items-start gap-2">
                      <span className="text-accent-400 mt-0.5">•</span>
                      {it}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {/* AI-консультант CTA */}
            <div className="bg-gradient-to-br from-brand-600 to-brand-700 rounded-xl p-6 text-white flex flex-col justify-between">
              <div>
                <div className="w-12 h-12 bg-white/15 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <h3 className="font-bold text-lg mb-2">AI-консультант</h3>
                <p className="text-brand-200 text-sm leading-relaxed mb-4">
                  Задайте вопрос по инженерным системам прямо сейчас — AI-помощник ответит на основе базы знаний компании
                </p>
              </div>
              <p className="text-xs text-brand-300">
                Нажмите на кнопку чата справа внизу →
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW WE WORK */}
      <section className="py-12 sm:py-20 bg-gray-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-brand-600 text-center mb-10 sm:mb-14">
            Как мы работаем
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
            {STEPS.map((step) => (
              <div key={step.num} className="bg-white rounded-xl p-6 border border-gray-100 hover:shadow-md transition-shadow">
                <span className="text-3xl font-bold text-accent-400 block mb-3">{step.num}</span>
                <h3 className="font-semibold text-gray-900 mb-2">{step.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="py-12 sm:py-16 bg-brand-600 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-center">
            {STATS.map((s) => (
              <div key={s.label}>
                <div className="text-3xl sm:text-4xl font-bold mb-1">{s.value}</div>
                <div className="text-brand-200 text-sm">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-12 sm:py-20">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-brand-600 mb-4">
            Нужна консультация?
          </h2>
          <p className="text-gray-500 mb-8 text-sm sm:text-base">
            Оставьте контактные данные, и наш менеджер свяжется с вами в ближайшее время.
            Или задайте вопрос AI-консультанту — кнопка чата справа внизу.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <a
              href="https://gkproject.ru/contacts/"
              target="_blank"
              rel="noopener noreferrer"
              className="px-8 py-3 bg-brand-600 hover:bg-brand-700 text-white font-semibold rounded-lg transition-colors text-sm shadow-lg"
            >
              Оставить заявку
            </a>
            <a
              href="tel:+74959087474"
              className="px-8 py-3 border border-brand-200 text-brand-600 hover:bg-brand-50 font-medium rounded-lg transition-colors text-sm"
            >
              +7 495 908-74-74
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-brand-800 text-brand-300 py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2">
            <img src="/logo-gk.png" alt="ГК Проект" className="h-7 w-auto" />
            <span>© {new Date().getFullYear()} ООО «ГК Проект» — Инженерные системы под ключ</span>
          </div>
          <div className="flex items-center gap-4">
            <span>Москва, Хлебозаводский пр-д, 7 стр. 9</span>
            <a href="mailto:info@gkproject.ru" className="hover:text-white transition-colors">info@gkproject.ru</a>
          </div>
        </div>
      </footer>

      <ChatWidget externalOpen={chatOpen} onOpenChange={setChatOpen} />
    </div>
  );
}
