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
        className="px-3 py-1.5 text-xs bg-brand-600 text-white rounded-full hover:bg-brand-700 transition-colors whitespace-nowrap font-medium"
      >
        📞 Оставить заявку
      </button>
      {QUICK_REPLIES.map((text) => (
        <button
          key={text}
          onClick={() => onSelect(text)}
          className="px-3 py-1.5 text-xs bg-brand-50 text-brand-600 rounded-full border border-brand-200 hover:bg-brand-100 transition-colors whitespace-nowrap"
        >
          {text}
        </button>
      ))}
    </div>
  );
}
