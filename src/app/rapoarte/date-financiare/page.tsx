import ModelA from '@/components/ModelA'
import { propsSituatii } from './surse'

export default function DateFinanciarePage() {
  return <ModelA {...propsSituatii('financiare')} />
}
