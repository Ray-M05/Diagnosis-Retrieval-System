import React, { useState } from 'react';
import { HeartPulse, Info, Search, Stethoscope } from 'lucide-react';
import { SymptomSearchView } from './views/SymptomSearchView';
import { ClinicalRAGView } from './views/ClinicalRAGView';

type Tab = 'search' | 'rag';

export default function App() {
  const [tab, setTab] = useState<Tab>('search');

  return (
    <div className="min-h-screen bg-gray-50/50 flex flex-col items-center px-4 py-12 md:py-24">
      <div className="w-full max-w-4xl mx-auto flex flex-col gap-10">

        {/* Header */}
        <header className="text-center space-y-4">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 rounded-full text-sm font-semibold mb-2">
            <HeartPulse className="w-4 h-4" />
            <span>Clinical Decision Support</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-gray-900 tracking-tight leading-tight">
            Find health information <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-blue-500">
              by symptoms.
            </span>
          </h1>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            Search for conditions by name or symptoms, or run a full clinical RAG with a patient chart.
          </p>
        </header>

        {/* Tab switcher */}
        <div className="flex gap-2 max-w-sm mx-auto bg-gray-100 p-1 rounded-2xl w-full">
          <button
            onClick={() => setTab('search')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              tab === 'search'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Search className="w-4 h-4" />
            Symptom Search
          </button>
          <button
            onClick={() => setTab('rag')}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
              tab === 'rag'
                ? 'bg-white text-indigo-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Stethoscope className="w-4 h-4" />
            Clinical RAG
          </button>
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-50 border border-amber-100 p-5 rounded-2xl flex items-start gap-4 max-w-2xl mx-auto shadow-sm w-full">
          <Info className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
          <p className="text-xs text-amber-900 leading-relaxed font-medium">
            <span className="font-bold text-amber-800 uppercase tracking-wide block mb-1">Important:</span>
            This is a Differential Diagnosis Support system and does not replace professional medical care.
            Its function is to retrieve information and cite sources; all clinical decisions must be made
            with health professionals.
          </p>
        </div>

        {/* Active view */}
        <main>
          {tab === 'search' ? <SymptomSearchView /> : <ClinicalRAGView />}
        </main>

        <footer className="mt-12 text-center text-gray-400 text-sm border-t border-gray-100 pt-8">
          <p>© 2026 SRI-DX Clinical Retrieval System. For educational and research purposes only.</p>
        </footer>
      </div>
    </div>
  );
}
