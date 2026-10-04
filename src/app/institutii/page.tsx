import { redirect } from 'next/navigation'

/* Paginile instituțiilor (BNR, Casa de Pensii, Min. Educației, Min. Finanțe) sunt listate pe homepage. */
export default function InstitutiiPage() {
  redirect('/#institutii')
}
