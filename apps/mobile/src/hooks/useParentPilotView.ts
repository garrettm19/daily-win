import { useEffect, useState } from 'react';

import { isParentPilotView, subscribePilotView } from '@/lib/pilotView';

export function useParentPilotView(): boolean {
  const [enabled, setEnabled] = useState(isParentPilotView);

  useEffect(() => {
    return subscribePilotView(() => {
      setEnabled(isParentPilotView());
    });
  }, []);

  return enabled;
}
