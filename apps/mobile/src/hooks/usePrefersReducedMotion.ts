import { useEffect, useState } from 'react';
import { AccessibilityInfo } from 'react-native';

export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const subscription = AccessibilityInfo.addEventListener(
      'reduceMotionChanged',
      setReduced,
    );
    void AccessibilityInfo.isReduceMotionEnabled().then(setReduced);
    return () => {
      subscription.remove();
    };
  }, []);

  return reduced;
}
