import ModelA from '@/components/ModelA'
import { propsSituatii } from '../date-financiare/surse'

export default function DateIdentificarePage() {
  return <ModelA {...propsSituatii('identificare')} />
}
