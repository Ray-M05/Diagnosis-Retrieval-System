import React, { useState } from 'react';
import { Search, Info, X, HeartPulse, Loader2 } from 'lucide-react';
import { diseases, Disease } from './data/diseases';
import { DiseaseCard } from './components/DiseaseCard';
import { motion, AnimatePresence } from 'motion/react';

export default function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<Disease[] | null>(null);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setIsSearching(true);
    
    // Simulate data processing/searching delay
    setTimeout(() => {
      const lowerSearch = searchTerm.toLowerCase();
      const filtered = diseases.filter(
        (disease) =>
          disease.name.toLowerCase().includes(lowerSearch) ||
          disease.symptoms.some((s) => s.toLowerCase().includes(lowerSearch))
      );
      setResults(filtered);
      setIsSearching(false);
    }, 800);
  };

  const handleClear = () => {
    setSearchTerm('');
    setResults(null);
  };

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col items-center px-4 py-12 md:py-24">
      <div className="w-full max-w-4xl mx-auto flex flex-col gap-10">
        
        {/* Header Section */}
        <header className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 rounded-full text-sm font-semibold mb-2">
            <HeartPulse className="w-4 h-4" />
            <span>Symptom Search Assistant</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 tracking-tight leading-tight">
            Find health information <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">
              by symptoms.
            </span>
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            Search for conditions by name or symptoms to retrieve information and cited sources.
          </p>
        </header>

        {/* Search Form Section */}
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
                  aria-label="Clean search"
                  title="Clean search"
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

        {/* Updated Disclaimer Section */}
        <div className="bg-amber-50 border border-amber-100 p-5 rounded-2xl flex items-start gap-4 max-w-2xl mx-auto shadow-sm">
          <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-900 leading-relaxed font-medium">
            <span className="font-bold text-amber-800 uppercase tracking-wide block mb-1">Important:</span>
            This is a Differential Diagnosis Support system and does not replace professional medical care. 
            Its function is to retrieve information and cite sources; all clinical decisions must be made with health professionals.
          </p>
        </div>

        {/* Results Section */}
        <main className="space-y-6">
          <AnimatePresence mode='wait'>
            {isSearching ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center py-20 gap-4"
              >
                <div className="relative">
                  <div className="w-12 h-12 border-4 border-indigo-100 rounded-full"></div>
                  <div className="w-12 h-12 border-4 border-indigo-600 rounded-full border-t-transparent animate-spin absolute inset-0"></div>
                </div>
                <p className="text-gray-500 font-medium animate-pulse">Processing medical data...</p>
              </motion.div>
            ) : results !== null ? (
              <motion.div
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
                    <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Search className="w-8 h-8 text-gray-300" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900">No results found</h3>
                    <p className="text-gray-500 max-w-xs mx-auto mt-2">
                      Try searching for different symptoms or check the spelling.
                    </p>
                  </div>
                )}
              </motion.div>
            ) : null}
          </AnimatePresence>
        </main>

        <footer className="mt-12 text-center text-gray-400 text-sm border-t border-gray-100 pt-8">
          <p>© 2026 Medical Symptom Assistant. For educational purposes only.</p>
        </footer>
      </div>
    </div>
  );
}
