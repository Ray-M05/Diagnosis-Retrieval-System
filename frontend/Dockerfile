# ---- Stage 1: build --------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci

ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}

COPY . .
RUN npm run build

# ---- Stage 2: runtime -------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["sh", "-c", "echo '' && echo '  Frontend in http://localhost:3000' && echo '' && exec nginx -g 'daemon off;'"]
