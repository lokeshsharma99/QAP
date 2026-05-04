FROM node:20-alpine AS base

# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

# Copy source
COPY . .

# Build-time public env vars (baked into client-side JS by Next.js)
# NEXT_PUBLIC_AGENTOS_URL  = external API URL (ngrok / devtunnel / localhost)
ARG NEXT_PUBLIC_AGENTOS_URL=http://localhost:8000
ENV NEXT_PUBLIC_AGENTOS_URL=${NEXT_PUBLIC_AGENTOS_URL}

# Build
RUN pnpm build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=base /app/.next/standalone ./
COPY --from=base /app/.next/static ./.next/static
COPY --from=base /app/public* ./public/

USER nextjs

EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
