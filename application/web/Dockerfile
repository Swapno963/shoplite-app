# =========================
# Build Stage
# =========================
FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm ci

COPY . .

RUN npm run build


# =========================
# Runtime Stage
# =========================
FROM nginx:1.30-alpine-slim

RUN apk upgrade --no-cache

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf
COPY default.conf /etc/nginx/conf.d/default.conf

# Copy built assets
COPY --from=build /app/dist /usr/share/nginx/html

# Create non-root user
RUN addgroup -S nginxuser && \
    adduser -S nginxuser -G nginxuser && \
    chown -R nginxuser:nginxuser \
        /usr/share/nginx/html \
        /var/cache/nginx \
        /var/run \
        /var/log/nginx

# Nginx listens on 8060 for non-root execution
RUN sed -i 's/listen 80;/listen 8060;/g' \
    /etc/nginx/conf.d/default.conf

USER nginxuser

EXPOSE 8060

HEALTHCHECK --interval=30s \
            --timeout=5s \
            --start-period=10s \
            --retries=3 \
    CMD wget --spider -q http://localhost:8060/ || exit 1

CMD ["nginx", "-g", "daemon off;"]