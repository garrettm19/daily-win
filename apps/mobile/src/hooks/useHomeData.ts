import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';

import {
  fetchDemoChildProfile,
  fetchLatestDemoDailyWin,
} from '@/lib/api/demo';
import type { DemoChildProfile, DemoDailyWin } from '@/lib/api/types';

function errorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message;
  }
  return 'The Daily Win API could not complete this request.';
}

export function useHomeData() {
  const [profile, setProfile] = useState<DemoChildProfile | null>(null);
  const [dailyWin, setDailyWin] = useState<DemoDailyWin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const generationRef = useRef(0);

  const load = useCallback((showLoading: boolean) => {
    const generation = ++generationRef.current;
    if (showLoading) {
      setLoading(true);
      setError(null);
    }
    void Promise.all([fetchDemoChildProfile(), fetchLatestDemoDailyWin()])
      .then(([nextProfile, nextDailyWin]) => {
        if (generation !== generationRef.current) {
          return;
        }
        setProfile(nextProfile);
        setDailyWin(nextDailyWin);
      })
      .catch((caught: unknown) => {
        if (generation !== generationRef.current) {
          return;
        }
        setProfile(null);
        setDailyWin(null);
        setError(errorMessage(caught));
      })
      .finally(() => {
        if (generation === generationRef.current) {
          setLoading(false);
        }
      });
  }, []);

  useFocusEffect(
    useCallback(() => {
      load(false);
    }, [load]),
  );

  const retry = useCallback(() => {
    load(true);
  }, [load]);

  return {
    profile,
    dailyWin,
    error,
    loading,
    retry,
    rememberDailyWin: setDailyWin,
  };
}
