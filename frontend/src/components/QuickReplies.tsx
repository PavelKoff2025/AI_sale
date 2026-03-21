interface QuickRepliesProps {
  onSelect: (text: string) => void;
  onLeadClick: () => void;
  visible: boolean;
}

const QUICK_REPLIES = [
  "Какие услуги?",
  "Сколько стоит монтаж?",
  "Как вы работаете?",
  "Гарантии",
  "Примеры работ",
];

export function QuickReplies({ onSelect, onLeadClick, visible }: QuickRepliesProps) {
  if (!visible) return null;

  return (
    <div className="px-3 pb-2 flex flex-wrap gap-1.5">
      <button
        onClick={onLeadClick}
        className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded-full hover:bg-blue-700 transition-colors whitespace-nowrap font-medium"
      >
        📞 Оставить заявку
      </button>
      {QUICK_REPLIES.map((text) => (
        <button
          key={text}
          onClick={() => onSelect(text)}
          className="px-3 py-1.5 text-xs bg-blue-50 text-blue-700 rounded-full border border-blue-200 hover:bg-blue-100 transition-colors whitespace-nowrap"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
