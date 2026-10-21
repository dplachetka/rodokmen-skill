# Image pro vlastní server: `npm run kontejner` (Podman). Plné názvy obrazů – Podman krátké názvy bez dotazu nedoplní.
# Soubor se jmenuje Dockerfile, protože ho tak hledá CapRover (captain-definition); Podman ho čte stejně.
FROM docker.io/library/node:24-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM docker.io/library/nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
