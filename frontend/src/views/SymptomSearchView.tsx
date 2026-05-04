import React, { useState } from 'react';
import { Search, X, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { DiseaseCard } from '../components/DiseaseCard';
import { searchDiseases } from '../api/client';
import type { Disease } from '../types';

export const SymptomSearchView: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<Disease[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    setError(null);

    try {
      const diseases = await searchDiseases(searchTerm.trim(), 10);
      setResults(diseases);
    } catch (err) {
      setError(String(err));
      setResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleClear = () => {
    setSearchTerm('');
    setResults(null);
    setError(null);
  };

  return (
    <div className="flex flex-col gap-10">
      {/* Search Form */}
      <form onSubmit={handleSearch} className="relative group max-w-2xl w-full mx-auto space-y-4">
        <div className="relative">
          <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none transition-transform group-focus-within:scale-110">
            <Search className="h-5 w-5 text-gray-400 group-focus-within:text-indigo-500" />
          </div>
          <input
            type="text"
            className="w-full pl-14 pr-32 py-5 bg-white border border-gray-200 rounded-3xl shadow-xl shadow-gray-200/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all text-lg placeholder:text-gray-400"
            placeholder="Enter symptoms (e.g. fever, cough...)"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <div className="absolute inset-y-0 right-3 flex items-center gap-2">
            {searchTerm && (
              <button
                type="button"
                onClick={handleClear}
                className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Clear search"
              >
                <X className="h-5 w-5" />
              </button>
            )}
            <button
              type="submit"
              disabled={isSearching || !searchTerm.trim()}
              className="px-6 py-2.5 bg-indigo-600 text-white font-semibold rounded-2xl hover:bg-indigo-700 disabled:bg-gray-200 disabled:cursor-not-allowed transition-all flex items-center gap-2 shadow-lg shadow-indigo-100 cursor-pointer"
            >
              {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
            </button>
          </div>
        </div>
      </form>

      {/* Error */}
      {error && (
        <div className="max-w-2xl mx-auto w-full bg-red-50 border border-red-200 text-red-700 text-sm rounded-2xl px-5 py-4">
          {error}
        </div>
      )}

      {/* Results */}
      <AnimatePresence mode="wait">
        {isSearching ? (
          <motion.div
            key="loading"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex flex-col items-center justify-center py-20 gap-4"
          >
            <div className="relative">
              <div className="w-12 h-12 border-4 border-indigo-100 rounded-full" />
              <div className="w-12 h-12 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin absolute inset-0" />
            </div>
            <p className="text-gray-500 font-medium animate-pulse">Processing medical data...</p>
          </motion.div>
        ) : results !== null ? (
          <motion.div
            key="results"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            <div className="flex justify-between items-center px-2">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                Search Results
                <span className="text-sm font-normal text-gray-400 bg-gray-100 px-2.5 py-0.5 rounded-full">
                  {results.length} found
                </span>
              </h2>
            </div>

            {results.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {results.map((disease) => (
                  <DiseaseCard key={disease.id} disease={disease} />
                ))}
              </div>
            ) : (
              <div className="text-center py-20 bg-white rounded-3xl border border-dashed border-gray-200">
                <Search className="w-8 h-8 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900">No results found</h3>
                <p className="text-gray-500 max-w-xs mx-auto mt-2">
                  Try different symptoms or check your connection to the backend.
                </p>
              </div>
            )}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  );
};
