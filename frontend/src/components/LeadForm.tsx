import { useState } from "react";
import { defaultConfig } from "../utils/config";

interface LeadFormProps {
  onClose: () => void;
  sessionId: string;
}

export function LeadForm({ onClose, sessionId }: LeadFormProps) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const canSubmit = name.trim().length >= 2 && phone.trim().length >= 5;

  const formatPhone = (value: string) => {
    const digits = value.replace(/\D/g, "");
    if (digits.length === 0) return "";
    if (digits.length <= 1) return `+${digits}`;
    if (digits.length <= 4) return `+${digits.slice(0, 1)} ${digits.slice(1)}`;
    if (digits.length <= 7) return `+${digits.slice(0, 1)} ${digits.slice(1, 4)} ${digits.slice(4)}`;
    if (digits.length <= 9) return `+${digits.slice(0, 1)} ${digits.slice(1, 4)} ${digits.slice(4, 7)}-${digits.slice(7)}`;
    return `+${digits.slice(0, 1)} ${digits.slice(1, 4)} ${digits.slice(4, 7)}-${digits.slice(7, 9)}-${digits.slice(9, 11)}`;
  };

  const handlePhoneChange = (value: string) => {
    if (value === "") {
      setPhone("");
      return;
    }
    const digits = value.replace(/\D/g, "");
    if (digits.length <= 11) {
      setPhone(formatPhone(value));
    }
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setStatus("sending");

    try {
      const response = await fetch(`${defaultConfig.apiUrl}/api/leads/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          phone: phone.trim(),
          source: "chat_widget",
          session_id: sessionId,
        }),
      });

      if (response.ok) {
        setStatus("sent");
      } else {
        setStatus("error");
      }
    } catch {
      setStatus("error");
    }
  };

  if (status === "sent") {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-base font-semibold text-gray-800">Заявка отправлена!</p>
        <p className="text-sm text-gray-500 mt-2">
          Менеджер отдела продаж свяжется<br />с вами в ближайшее время
        </p>
        <button
          onClick={onClose}
          className="mt-6 px-6 py-2.5 text-sm bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors font-medium"
        >
          Вернуться в чат
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-4">
      <div className="mb-4">
        <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center mb-3">
          <svg className="w-6 h-6 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
        </div>
        <p className="text-base font-semibold text-gray-800">Оставить заявку</p>
        <p className="text-sm text-gray-500 mt-1">Менеджер перезвонит вам за 5 минут</p>
      </div>

      <div className="space-y-3 flex-1">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Ваше имя *</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Иван Петров"
            className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
            autoFocus
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Телефон *</label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => handlePhoneChange(e.target.value)}
            placeholder="+7 999 123-45-67"
            className="w-full px-3 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      <div className="mt-4 space-y-2">
        <button
          onClick={handleSubmit}
          disabled={!canSubmit || status === "sending"}
          className="w-full py-2.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-medium"
        >
          {status === "sending" ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
              Отправка...
            </span>
          ) : "Перезвоните мне"}
        </button>
        <button
          onClick={onClose}
          className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
        >
          Вернуться в чат
        </button>
      </div>

      {status === "error" && (
        <p className="text-xs text-red-500 mt-2 text-center">
          Ошибка отправки. Позвоните: +7 495 908-74-74
        </p>
      )}
    </div>
  );
}
