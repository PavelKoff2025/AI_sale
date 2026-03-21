import { defaultConfig } from "../utils/config";

interface HeaderProps {
  onClose: () => void;
  onLeadClick?: () => void;
}

export function Header({ onClose, onLeadClick }: HeaderProps) {
  return (
    <div className="bg-blue-600 text-white px-4 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-xs font-bold">
          ГК
        </div>
        <div>
          <h3 className="font-semibold text-sm">{defaultConfig.title}</h3>
          <p className="text-xs text-blue-200">{defaultConfig.subtitle}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        {onLeadClick && (
          <button
            onClick={onLeadClick}
            className="px-2.5 py-1 text-xs bg-white/20 hover:bg-white/30 rounded-full transition-colors flex items-center gap-1.5"
            aria-label="Оставить заявку"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
            Заявка
          </button>
        )}
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-blue-700 rounded transition-colors"
          aria-label="Закрыть чат"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
