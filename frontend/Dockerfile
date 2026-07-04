FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# Build the application
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Production defaults — NEXT_PUBLIC_* must be available at build time.
# The Maps API key was previously baked in as an ENV literal. Post-audit
# 2026-07-01: accept it as a build arg so it can be rotated without
# committing a new value. Deploy with:
#   gcloud run deploy sjktconnect-web ... \
#     --set-build-env-vars NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=<key>
# For local builds the arg can be passed via `docker build --build-arg`.
ARG NEXT_PUBLIC_GOOGLE_MAPS_API_KEY
ENV NEXT_PUBLIC_API_URL=https://api.tamilschool.org
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=${NEXT_PUBLIC_GOOGLE_MAPS_API_KEY}
ENV NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID=ce9504578e73fb7dd21b6704

RUN if [ -z "$NEXT_PUBLIC_GOOGLE_MAPS_API_KEY" ]; then \
      echo "ERROR: NEXT_PUBLIC_GOOGLE_MAPS_API_KEY build arg is required" >&2; \
      exit 1; \
    fi
RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=8080

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public

# Set the correct permission for prerender cache
RUN mkdir .next
RUN chown nextjs:nodejs .next

# Automatically leverages output traces to reduce image size
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

CMD ["node", "server.js"]
