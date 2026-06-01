/** @type {import('next').NextConfig} */
const nextConfig = {
  async redirects() {
    return [
      {
        source: '/Industrii%20-%20Imobiliare.html',
        destination: '/imobiliare',
        permanent: true,
      },
      {
        source: '/Industrii - Imobiliare.html',
        destination: '/imobiliare',
        permanent: true,
      },
    ];
  },
};
export default nextConfig;
