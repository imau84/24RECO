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
    '/institutii/bnr',
    '/institutii/casa-pensii',
    '/institutii-publice/ministerul-finantelor/executie-bugetara',
    '/institutii-publice/ministerul-finantelor/datorie-publica',
    '/rapoarte/date-identificare',
    '/rapoarte/date-financiare',
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
