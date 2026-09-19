import { useEffect, useState } from 'react';

import {
  type BackendStatus,
  getBackendStatus,
  subscribeBackendStatus,
} from '@/lib/api/backendStatus';

export function useBackendStatus(): BackendStatus {
  const [status, setStatus] = useState<BackendStatus>(getBackendStatus);

  useEffect(() => subscribeBackendStatus(setStatus), []);

  return status;
}
