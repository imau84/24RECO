/** @type {import('next').NextConfig} */
const nextConfig = {
    async redirects() {
          return [
            { source: '/Industrii%20-%20Imobiliare.html', destination: '/imobiliare', permanent: true },
            { source: '/Industrii - Imobiliare.html', destination: '/imobiliare', permanent: true },
            { source: '/Industrii%20-%20Constructii.html', destination: '/industrii/constructii', permanent: true },
            { source: '/Industrii - Constructii.html', destination: '/industrii/constructii', permanent: true },
            { source: '/Industrii%20-%20Transport.html', destination: '/transport', permanent: true },
            { source: '/Industrii - Transport.html', destination: '/transport', permanent: true },
            { source: '/Rapoarte%20-%20Situatii%20Financiare.html', destination: '/rapoarte/date-financiare', permanent: true },
            { source: '/Rapoarte - Situatii Financiare.html', destination: '/rapoarte/date-financiare', permanent: true },
                ];
    },
};
export default nextConfig;
