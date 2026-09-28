import { fetchDemoProgress, fetchDemoSession, fetchNextWinState } from '@/lib/api/demo';
import { hapticSuccess } from '@/lib/haptics';
import { shouldHoldPresentedWin } from '@/lib/homePresentation';
import { shouldPollPreparation } from '@/lib/homeState';
import {
  PARENT_ERRORS,
  describeCaughtError,
  type ApiErrorKind,
} from '@/lib/api/parentErrors';
import type {
  DemoChildProfile,
  DemoDailyWin,
  DemoProgress,
  DemoSession,
  NextWinState,
} from '@/lib/api/types';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useFocusEffect } from 'expo-router';

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
  const [nextWin, setNextWin] = useState<NextWinState | null>(null);
  const [progress, setProgress] = useState<DemoProgress | null>(null);
  const [pendingReady, setPendingReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorKind, setErrorKind] = useState<ApiErrorKind | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const generationRef = useRef(0);
  const lastPrepStatus = useRef<string | null>(null);
  const heldWinRef = useRef<DemoDailyWin | null>(null);
  const screenHeldRef = useRef(true);

  const applyWin = useCallback((incoming: DemoDailyWin | null, promote: boolean) => {
    const hold = shouldHoldPresentedWin({
      presentedWinId: heldWinRef.current?.id ?? null,
      incomingWinId: incoming?.id ?? null,
      screenHeld: screenHeldRef.current && !promote,
    });
    if (hold) {
      setPendingReady(true);
      return;
    }
    heldWinRef.current = incoming;
    setDailyWin(incoming);
    setPendingReady(false);
  }, []);

  const load = useCallback(
    (showLoading: boolean, promote = false) => {
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
          const [state, nextProgress] = await Promise.all([
            nextProfile === null ? Promise.resolve(null) : fetchNextWinState(),
            nextProfile === null
              ? Promise.resolve(null)
              : fetchDemoProgress().catch(() => null),
          ]);
          if (generation !== generationRef.current) {
            return;
          }
          setSession(nextSession);
          setProfile(nextProfile);
          const incoming = state?.daily_win ?? null;
          const wouldHold = shouldHoldPresentedWin({
            presentedWinId: heldWinRef.current?.id ?? null,
            incomingWinId: incoming?.id ?? null,
            screenHeld: screenHeldRef.current && !promote,
          });
          if (
            lastPrepStatus.current === 'generating' &&
            state?.preparation_status === 'ready' &&
            incoming &&
            !wouldHold
          ) {
            hapticSuccess();
          }
          lastPrepStatus.current = state?.preparation_status ?? null;
          setNextWin(state);
          applyWin(incoming, promote);
          if (nextProgress) {
            setProgress(nextProgress);
          }
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
          setSession((current) => current ?? null);
        })
        .finally(() => {
          if (generation === generationRef.current) {
            setLoading(false);
          }
        });
    },
    [applyWin],
  );

  useFocusEffect(
    useCallback(() => {
      screenHeldRef.current = true;
      load(false, true);
      return () => {
        screenHeldRef.current = false;
      };
    }, [load]),
  );

  useEffect(() => {
    if (!shouldPollPreparation(nextWin?.preparation_status)) {
      return undefined;
    }
    const handle = setInterval(() => {
      load(false, false);
    }, 2000);
    return () => clearInterval(handle);
  }, [load, nextWin?.preparation_status]);

  const retry = useCallback(() => {
    load(true, true);
  }, [load]);

  const forgetDailyWin = useCallback(() => {
    heldWinRef.current = null;
    setDailyWin(null);
    setNextWin(null);
    setPendingReady(false);
    setProgress(null);
    setError(null);
    setErrorKind(null);
    setErrorCode(null);
  }, []);

  const refresh = useCallback(() => {
    load(false, true);
  }, [load]);

  const rememberDailyWin = useCallback((win: DemoDailyWin) => {
    heldWinRef.current = win;
    setDailyWin(win);
    setPendingReady(false);
  }, []);

  return {
    session,
    profile,
    dailyWin,
    nextWin,
    progress,
    pendingReady,
    error,
    errorKind,
    errorCode,
    loading,
    retry,
    refresh,
    forgetDailyWin,
    rememberDailyWin,
  };
}
