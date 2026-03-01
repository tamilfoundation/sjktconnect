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

# Production defaults — NEXT_PUBLIC_* must be available at build time
ENV NEXT_PUBLIC_API_URL=https://sjktconnect-api-748286712183.asia-southeast1.run.app
ENV NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIzaSyAx7HROyUT0aAp8jNQ-oWUMZsllr3fwF4A
ENV NEXT_PUBLIC_GOOGLE_MAPS_MAP_ID=ce9504578e73fb7dd21b6704

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
