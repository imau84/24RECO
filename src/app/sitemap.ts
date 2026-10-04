import type { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const base = 'https://24reco.com'

  const routes = [
    '',                                                              // Acasă
    '/comert',
    '/imobiliare',
    '/transport',
    '/industrii/agricultura',
    '/industrii/industrie',
    '/industrii/turism',
    '/industrii/it-comunicatii',
    '/industrii/finante',
    '/industrii/energie',
    '/institutii/bnr',
    '/institutii/casa-pensii',
    '/institutii/educatie',
    '/institutii-publice/ministerul-finantelor',
    '/rapoarte/date-identificare',
    '/rapoarte/date-financiare',
    '/rapoarte/alegeri-locale-2024',
    '/despre',
    '/metodologie',
    '/surse',
    '/contact',
  ]

  return routes.map((path) => ({
    url: `${base}${path}`,
    lastModified: new Date(),
    changeFrequency: 'monthly',
    priority: path === '' ? 1 : 0.7,
  }))
}
