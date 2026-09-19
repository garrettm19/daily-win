import { useCallback, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';

import { fetchDemoSession, fetchLatestDemoDailyWin } from '@/lib/api/demo';
import {
  PARENT_ERRORS,
  describeCaughtError,
  type ApiErrorKind,
} from '@/lib/api/parentErrors';
import type { DemoChildProfile, DemoDailyWin, DemoSession } from '@/lib/api/types';

function describeLoadError(caught: unknown): {
  message: string;
  kind: ApiErrorKind | null;
  code: string | null;
} {
  return describeCaughtError(caught, PARENT_ERRORS.load);
}

export function useHomeData() {
  const [session, setSession] = useState<DemoSession | null>(null);
  const [profile, setProfile] = useState<DemoChildProfile | null>(null);
  const [dailyWin, setDailyWin] = useState<DemoDailyWin | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const generationRef = useRef(0);

  const load = useCallback((showLoading: boolean) => {
    const generation = ++generationRef.current;
    if (showLoading) {
      setLoading(true);
      setError(null);
      setErrorKind(null);
      setErrorCode(null);
    }
    void fetchDemoSession()
      .then(async (nextSession) => {
        const nextProfile =
          nextSession.status === 'ready' ? nextSession.profile : null;
        const nextDailyWin =
          nextProfile === null ? null : await fetchLatestDemoDailyWin();
        if (generation !== generationRef.current) {
          return;
        }
        setSession(nextSession);
        setProfile(nextProfile);
        setDailyWin(nextDailyWin);
        setError(null);
        setErrorKind(null);
        setErrorCode(null);
      })
      .catch((caught: unknown) => {
        if (generation !== generationRef.current) {
          return;
        }
        const described = describeLoadError(caught);
        setError(described.message);
        setErrorKind(described.kind);
        setErrorCode(described.code);
        setSession((current) => {
          if (current) {
            return current;
          }
          return null;
        });
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

  const forgetDailyWin = useCallback(() => {
    setDailyWin(null);
    setError(null);
    setErrorKind(null);
    setErrorCode(null);
  }, []);

  const refresh = useCallback(() => {
    load(false);
  }, [load]);

  return {
    session,
    profile,
    dailyWin,
    error,
    errorKind,
    errorCode,
    loading,
    retry,
    refresh,
    forgetDailyWin,
    rememberDailyWin: setDailyWin,
  };
}
