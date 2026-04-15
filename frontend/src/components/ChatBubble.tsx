interface ChatBubbleProps {
  isOpen: boolean;
  onClick: () => void;
}

export function ChatBubble({ isOpen, onClick }: ChatBubbleProps) {
  return (
    <button
      onClick={onClick}
      className="w-16 h-16 rounded-full bg-white shadow-lg hover:shadow-xl transition-all duration-200 flex items-center justify-center hover:scale-105 border border-gray-200"
      aria-label={isOpen ? "Закрыть чат" : "Открыть чат"}
    >
      {isOpen ? (
        <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6 text-brand-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      ) : (
        <img src="/logo-gk.png" alt="Чат с ГК Проект" className="w-14 h-14 rounded-full object-cover" />
      )}
    </button>
  );
}
