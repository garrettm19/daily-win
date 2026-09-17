import { useCallback, useEffect, useRef, useState } from 'react';

import { fetchDemoChildProfile } from '@/lib/api/demo';
import type { DemoChildProfile } from '@/lib/api/types';

function errorMessage(caught: unknown): string {
  if (caught instanceof Error) {
    return caught.message;
  }
  return 'The child profile could not be loaded from the server.';
}

export function useDemoChildProfile() {
  const [profile, setProfile] = useState<DemoChildProfile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const generationRef = useRef(0);

  useEffect(() => {
    const generation = ++generationRef.current;

    void fetchDemoChildProfile()
      .then((nextProfile) => {
        if (generation !== generationRef.current) {
          return;
        }
        setProfile(nextProfile);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (generation !== generationRef.current) {
          return;
        }
        setProfile(null);
        setError(errorMessage(caught));
      })
      .finally(() => {
        if (generation === generationRef.current) {
          setLoading(false);
        }
      });

    return () => {
      generationRef.current += 1;
    };
  }, []);

  const retry = useCallback(() => {
    const generation = ++generationRef.current;
    setLoading(true);
    setError(null);
    void fetchDemoChildProfile()
      .then((nextProfile) => {
        if (generation !== generationRef.current) {
          return;
        }
        setProfile(nextProfile);
        setError(null);
      })
      .catch((caught: unknown) => {
        if (generation !== generationRef.current) {
          return;
        }
        setProfile(null);
        setError(errorMessage(caught));
      })
      .finally(() => {
        if (generation === generationRef.current) {
          setLoading(false);
        }
      });
  }, []);

  return { profile, error, loading, retry };
}
