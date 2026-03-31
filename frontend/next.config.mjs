import pkg from './package.json' with { type: 'json' };

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_FRONTEND_VERSION: pkg.version,
  },
};

export default nextConfig;
