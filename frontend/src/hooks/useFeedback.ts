import { useMemo, useState } from 'react';
import {
  refineSearch,
  retractRelevanceFeedback,
  submitRelevanceFeedback,
  type RefineSearchResponse,
} from '../api/client';

const SESSION_KEY = 'sri_dx_feedback_session_id';

function createSessionId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function getSessionId(): string {
  const existing = sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const next = createSessionId();
  sessionStorage.setItem(SESSION_KEY, next);
  return next;
}

export function useFeedback() {
  const sessionId = useMemo(getSessionId, []);
  const [voteCount, setVoteCount] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRefining, setIsRefining] = useState(false);

  const submit = async (args: {
    query: string;
    chunkId: string;
    docId: string;
    relevant: boolean;
  }) => {
    setIsSubmitting(true);
    try {
      await submitRelevanceFeedback({
        session_id: sessionId,
        query: args.query,
        chunk_id: args.chunkId,
        doc_id: args.docId,
        relevant: args.relevant,
      });
      setVoteCount((n) => n + 1);
    } finally {
      setIsSubmitting(false);
    }
  };

  const retract = async (args: {
    query: string;
    chunkId: string;
    docId: string;
  }) => {
    setIsSubmitting(true);
    try {
      await retractRelevanceFeedback({
        session_id: sessionId,
        query: args.query,
        chunk_id: args.chunkId,
        doc_id: args.docId,
      });
      setVoteCount((n) => Math.max(0, n - 1));
    } finally {
      setIsSubmitting(false);
    }
  };

  const refine = async (query: string, k = 10): Promise<RefineSearchResponse> => {
    setIsRefining(true);
    try {
      return await refineSearch({
        session_id: sessionId,
        query,
        k,
      });
    } finally {
      setIsRefining(false);
    }
  };

  const reset = () => {
    setVoteCount(0);
    setIsSubmitting(false);
    setIsRefining(false);
  };

  return {
    sessionId,
    hasFeedback: voteCount > 0,
    isSubmitting,
    isRefining,
    submit,
    retract,
    refine,
    reset,
  };
}
