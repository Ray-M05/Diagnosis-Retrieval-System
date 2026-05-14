import React, { useState } from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';

interface RelevanceFeedbackButtonsProps {
  disabled?: boolean;
  onSubmit: (relevant: boolean) => Promise<void>;
}

export const RelevanceFeedbackButtons: React.FC<RelevanceFeedbackButtonsProps> = ({
  disabled = false,
  onSubmit,
}) => {
  const [selected, setSelected] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  const handleClick = async (relevant: boolean) => {
    setBusy(true);
    try {
      await onSubmit(relevant);
      setSelected(relevant);
    } finally {
      setBusy(false);
    }
  };

  const baseClass = 'inline-flex h-8 w-8 items-center justify-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50';

  return (
    <div className="flex items-center gap-1.5" aria-label="Relevance feedback">
      <button
        type="button"
        title="Relevante"
        aria-label="Marcar como relevante"
        disabled={disabled || busy}
        onClick={() => handleClick(true)}
        className={`${baseClass} ${
          selected === true
            ? 'border-green-200 bg-green-50 text-green-700'
            : 'border-gray-200 text-gray-400 hover:border-green-200 hover:text-green-700'
        }`}
      >
        <ThumbsUp className="h-4 w-4" />
      </button>
      <button
        type="button"
        title="No relevante"
        aria-label="Marcar como no relevante"
        disabled={disabled || busy}
        onClick={() => handleClick(false)}
        className={`${baseClass} ${
          selected === false
            ? 'border-red-200 bg-red-50 text-red-700'
            : 'border-gray-200 text-gray-400 hover:border-red-200 hover:text-red-700'
        }`}
      >
        <ThumbsDown className="h-4 w-4" />
      </button>
    </div>
  );
};
