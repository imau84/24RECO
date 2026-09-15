import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
    },
    sitemap: 'https://www.24reco.com/sitemap.xml',
    host: 'https://www.24reco.com',
  }
}
