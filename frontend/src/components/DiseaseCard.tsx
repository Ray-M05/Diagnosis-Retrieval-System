import React from 'react';
import { Disease } from '../data/diseases';
import { Link2 } from 'lucide-react';
import { motion } from 'motion/react';

interface DiseaseCardProps {
  disease: Disease;
}

export const DiseaseCard: React.FC<DiseaseCardProps> = ({ disease }) => {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col gap-4"
    >
      <div>
        <h3 className="text-xl font-bold text-gray-900 leading-tight">
          {disease.name}
        </h3>
        <p className="text-sm text-gray-500 mt-2 leading-relaxed">
          {disease.description}
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {disease.symptoms.map((symptom) => (
          <span
            key={symptom}
            className="px-3 py-1 bg-indigo-50 text-indigo-600 rounded-full text-[13px] font-medium border border-indigo-100/50"
          >
            {symptom}
          </span>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-50 flex items-center gap-2">
        <Link2 className="w-4 h-4 text-gray-400" />
        <a 
          href={disease.sourceUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-xs font-medium text-gray-400 hover:text-indigo-600 transition-colors flex items-center gap-1"
        >
          Source: {disease.source}
        </a>
      </div>
    </motion.div>
  );
};
