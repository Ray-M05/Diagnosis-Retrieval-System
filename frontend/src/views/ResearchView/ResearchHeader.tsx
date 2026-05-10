import React from 'react';
import { Search, X, Filter, Loader2 } from 'lucide-react';

interface ResearchHeaderProps {
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  handleSearch: (e: React.FormEvent) => void;
  handleClear: () => void;
  isSearching: boolean;
}

export const ResearchHeader: React.FC<ResearchHeaderProps> = ({
  searchTerm,
  setSearchTerm,
  handleSearch,
  handleClear,
  isSearching,
}) => {
  return (
    <header className="bg-white border-b border-gray-100 p-4 md:px-8 flex flex-col gap-4 shrink-0 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-0.5">
          <h1 className="text-xl md:text-2xl font-extrabold text-gray-900 tracking-tight leading-none">
            Encuentra información de salud <br className="hidden md:block" />
            <span className="bg-clip-text bg-linear-to-r from-indigo-600 to-blue-500 text-lg md:text-xl">
              por síntomas.
            </span>
          </h1>
          <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
            <Filter className="w-3 h-3 text-indigo-400" /> SRI-DX Support Engine
          </p>
        </div>

        <form onSubmit={handleSearch} className="relative group max-w-lg w-full">
          <div className="relative">
            <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none transition-transform group-focus-within:scale-105">
              <Search className="h-4 w-4 text-gray-400 group-focus-within:text-indigo-500" />
            </div>
            <textarea
              rows={1}
              className="w-full pl-11 pr-24 py-3 bg-gray-50 border border-gray-100 rounded-2xl focus:outline-none focus:ring-4 focus:ring-indigo-500/10 focus:border-indigo-500 transition-all text-sm font-medium placeholder:text-gray-400 resize-none overflow-y-auto max-h-32 leading-5"
              placeholder="Ingrese síntomas clínicos..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch(e as unknown as React.FormEvent);
                }
              }}
            />
            <div className="absolute top-2 right-2 flex items-center gap-1.5">
              {searchTerm && (
                <button
                  type="button"
                  onClick={handleClear}
                  className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
              <button
                type="submit"
                disabled={isSearching || !searchTerm.trim()}
                className="px-4 py-1.5 bg-indigo-600 text-white text-[10px] font-bold rounded-xl hover:bg-indigo-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all shadow-md shadow-indigo-100 cursor-pointer"
              >
                {isSearching ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'BUSCAR'}
              </button>
            </div>
          </div>
        </form>
      </div>
    </header>
  );
};
