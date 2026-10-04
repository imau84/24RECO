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
            { source: '/Rapoarte%20-%20Alegeri%20Locale%202024.html', destination: '/rapoarte/alegeri-locale-2024', permanent: true },
            { source: '/Rapoarte - Alegeri Locale 2024.html', destination: '/rapoarte/alegeri-locale-2024', permanent: true },
            { source: '/Institutii%20publice%20-%20Ministerul%20Educatiei.html', destination: '/institutii/educatie', permanent: true },
            { source: '/Institutii publice - Ministerul Educatiei.html', destination: '/institutii/educatie', permanent: true },
            // Execuție bugetară și Datorie publică sunt acum tab-uri pe pagina Ministerului Finanțelor
            { source: '/institutii-publice/ministerul-finantelor/executie-bugetara', destination: '/institutii-publice/ministerul-finantelor', permanent: true },
            { source: '/institutii-publice/ministerul-finantelor/datorie-publica', destination: '/institutii-publice/ministerul-finantelor', permanent: true },
                ];
    },
};
export default nextConfig;
