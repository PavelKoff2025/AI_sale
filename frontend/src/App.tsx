import { ChatWidget } from "./components/ChatWidget";

/** Встраивание на gkproject.ru (Битрикс): iframe на URL с ?embed=1 или /embed/ */
function isEmbedMode(): boolean {
  if (typeof window === "undefined") return false;
  const q = new URLSearchParams(window.location.search);
  if (q.get("embed") === "1" || q.get("embed") === "true") return true;
  return window.location.pathname.replace(/\/$/, "") === "/embed";
}

export default function App() {
  if (isEmbedMode()) {
    return <ChatWidget />;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
              ГК
            </div>
            <div>
              <span className="font-bold text-gray-900">ГК Проект</span>
              <span className="text-xs text-gray-500 block">Инженерные системы под ключ</span>
            </div>
          </div>
          <a href="tel:+74959087474" className="text-blue-600 font-semibold text-sm hover:text-blue-800">
            +7 495 908-74-74
          </a>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Монтаж инженерных систем
          </h1>
          <p className="text-lg text-gray-600 max-w-2xl mx-auto">
            Котельные, отопление, водоснабжение, электрика, канализация.
            1912 объектов с 2015 года. Гарантия до 10 лет.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
          {[
            { title: "Без предоплат", desc: "Оплата по факту выполнения работ" },
            { title: "Гарантия до 10 лет", desc: "Работа по договору с фиксацией цены" },
            { title: "1912+ объектов", desc: "Частные дома и предприятия с 2015 года" },
          ].map((item) => (
            <div key={item.title} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
              <p className="text-sm text-gray-600">{item.desc}</p>
            </div>
          ))}
        </div>

        <div className="bg-blue-600 text-white rounded-2xl p-8 text-center">
          <h2 className="text-2xl font-bold mb-2">AI-консультант</h2>
          <p className="text-blue-100 mb-4">
            Нажмите на кнопку чата справа внизу, чтобы задать вопрос
          </p>
          <p className="text-sm text-blue-200">
            Ответы на основе базы знаний gkproject.ru
          </p>
        </div>
      </main>

      <ChatWidget />
    </div>
  );
}
