import React from 'react';
import { Filter } from 'lucide-react';
import { SearchBar } from '../../components/SearchBar';

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
        <div className="space-y-0.5 shrink-0">
          <h1 className="text-xl md:text-2xl font-extrabold text-gray-900 tracking-tight leading-none">
            Find health information <br className="hidden md:block" />
            <span className="bg-clip-text bg-linear-to-r from-indigo-600 to-blue-500 text-lg md:text-xl">
              by symptoms.
            </span>
          </h1>
          <p className="text-[9px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-1.5">
            <Filter className="w-3 h-3 text-indigo-400" /> SRI-DX Support Engine
          </p>
        </div>

        <div className="max-w-lg w-full">
          <SearchBar
            value={searchTerm}
            onChange={setSearchTerm}
            onSubmit={handleSearch}
            onClear={handleClear}
            isLoading={isSearching}
            placeholder="Enter clinical symptoms..."
            submitLabel="SEARCH"
          />
        </div>
      </div>
    </header>
  );
};
