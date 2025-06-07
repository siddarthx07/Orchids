/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Configure allowed dev origins for cross-origin requests
  allowedDevOrigins: [
    '127.0.0.1', // For browser preview
    'localhost'  // For local development
  ]
};

module.exports = nextConfig;
