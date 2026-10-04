import type { Topic } from '@/components/ModelA'
import { temeDinJson, type Tema } from '@/components/temeDinJson'
import data from '@/data/energie/date.json'

/* Un tab pentru fiecare sursă a datelor (Eurostat, Ember, Comisia Europeană, OPCOM), 15 statistici.
   src/data/energie/date.json e actualizat lunar de scripts/fetch_energie.py (GitHub Actions). */

export const energieTopics = (accent: string): Topic[] => temeDinJson(data as unknown as Record<string, Tema>, accent)
