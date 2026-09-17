import { apiGet } from '@/lib/api/client';
import type { DemoChildProfile } from '@/lib/api/types';

export function fetchDemoChildProfile(): Promise<DemoChildProfile> {
  return apiGet<DemoChildProfile>('/api/v1/demo/child-profile');
}
