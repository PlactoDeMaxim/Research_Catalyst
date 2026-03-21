import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      {
        source: "/editor",
        destination: "/editor-v2",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
