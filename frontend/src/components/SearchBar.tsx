import React, { useRef, useEffect } from 'react';
import { Search, X, Loader2, Globe, MapPin } from 'lucide-react';

/**
 * Search modifiers. Independent flags so the user can combine Web + Positioning.
 * 'standard' is the absence of all modifiers.
 */
export type SearchBarModifier = 'web' | 'positioned';
export interface SearchBarModifiers {
  web: boolean;
  positioned: boolean;
}

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onClear: () => void;
  isLoading?: boolean;
  placeholder?: string;
  submitLabel?: string;
  /** Show Web / Positioning toggle buttons */
  showModeToggles?: boolean;
  /** Show the Positioning toggle (defaults to true when showModeToggles is on). */
  showPositioningToggle?: boolean;
  modifiers?: SearchBarModifiers;
  onModifierToggle?: (modifier: SearchBarModifier) => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChange,
  onSubmit,
  onClear,
  isLoading = false,
  placeholder = 'Enter symptoms...',
  submitLabel = 'Search',
  showModeToggles = false,
  showPositioningToggle = true,
  modifiers = { web: false, positioned: false },
  onModifierToggle,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <form
      onSubmit={onSubmit}
      className="w-full bg-white border border-gray-200 rounded-3xl shadow-xl shadow-gray-200/50 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500 transition-all"
    >
      {/* Input row */}
      <div className="flex items-start gap-3 px-5 pt-4 pb-3">
        <Search className="h-5 w-5 text-gray-400 group-focus-within:text-indigo-500 mt-0.5 shrink-0 transition-colors" />
        <textarea
          ref={textareaRef}
          rows={1}
          className="flex-1 bg-transparent resize-none outline-none text-base placeholder:text-gray-400 leading-snug overflow-hidden"
          style={{ maxHeight: '200px' }}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {value && (
          <button
            type="button"
            onClick={onClear}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors mt-0.5 shrink-0"
            aria-label="Clear"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Bottom toolbar */}
      <div className="flex items-center justify-between px-4 pb-3 pt-1 border-t border-gray-100">
        {/* Mode toggles */}
        <div className="flex items-center gap-2">
          {showModeToggles && onModifierToggle && (
            <>
              <button
                type="button"
                onClick={() => onModifierToggle('web')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border cursor-pointer ${
                  modifiers.web
                    ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                    : 'bg-white border-gray-200 text-gray-500 hover:border-blue-300 hover:text-blue-600'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                Web
              </button>
              {showPositioningToggle && (
                <button
                  type="button"
                  onClick={() => onModifierToggle('positioned')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all border cursor-pointer ${
                    modifiers.positioned
                      ? 'bg-indigo-600 border-indigo-600 text-white shadow-sm'
                      : 'bg-white border-gray-200 text-gray-500 hover:border-indigo-300 hover:text-indigo-600'
                  }`}
                >
                  <MapPin className="w-3.5 h-3.5" />
                  Positioning
                </button>
              )}
            </>
          )}
        </div>

        {/* Submit */}
        <button
          type="submit"
          disabled={isLoading || !value.trim()}
          className="px-5 py-1.5 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-md shadow-indigo-100 cursor-pointer"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : submitLabel}
        </button>
      </div>
    </form>
  );
};
