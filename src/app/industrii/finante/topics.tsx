import type { Topic } from '@/components/ModelA'
import { temeDinJson, type Tema } from '@/components/temeDinJson'
import data from '@/data/finante/date.json'

/* 5 teme (Piața de capital, Bănci, Asigurări, Investiții financiare, Pensii private), 20 de statistici.
   src/data/finante/date.json e actualizat lunar de scripts/fetch_finante.py (GitHub Actions),
   care rulează pachetul scripts/financiara/ (Eurostat, BCE, BIS, BVB, ASF, EIOPA). */

export const finanteTopics = (accent: string): Topic[] => temeDinJson(data as unknown as Record<string, Tema>, accent)
