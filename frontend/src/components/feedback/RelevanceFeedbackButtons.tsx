import React, { useEffect, useState } from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';

interface RelevanceFeedbackButtonsProps {
  disabled?: boolean;
  targetId: string;
  /**
   * Submit a vote. Called with true (relevant) or false (not relevant).
   */
  onSubmit: (relevant: boolean) => Promise<void>;
  /**
   * Retract the current vote. Called when the user clicks the already-selected
   * button (toggle off). Optional — if omitted the second click is ignored.
   */
  onRetract?: () => Promise<void>;
}

export const RelevanceFeedbackButtons: React.FC<RelevanceFeedbackButtonsProps> = ({
  disabled = false,
  targetId,
  onSubmit,
  onRetract,
}) => {
  const [selected, setSelected] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setSelected(null);
    setBusy(false);
  }, [targetId]);

  const handleClick = async (relevant: boolean) => {
    if (busy) return;
    setBusy(true);
    try {
      if (selected === relevant) {
        // Same button clicked again → retract.
        if (onRetract) {
          await onRetract();
          setSelected(null);
        }
        return;
      }
      await onSubmit(relevant);
      setSelected(relevant);
    } finally {
      setBusy(false);
    }
  };

  const baseClass = 'inline-flex h-8 w-8 items-center justify-center rounded-full border transition-colors disabled:cursor-not-allowed disabled:opacity-50';

  const upTitle = selected === true ? 'Undo relevant vote' : 'Mark as relevant';
  const downTitle = selected === false ? 'Undo not-relevant vote' : 'Mark as not relevant';

  return (
    <div className="flex items-center gap-1.5" aria-label="Relevance feedback">
      <button
        type="button"
        title={upTitle}
        aria-label={upTitle}
        aria-pressed={selected === true}
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
        title={downTitle}
        aria-label={downTitle}
        aria-pressed={selected === false}
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
