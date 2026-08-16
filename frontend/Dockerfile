# Frontend, containerized as a static build served by nginx (finding
# #11 — previously dev-server-only, with "no production deployment wiring"
# explicitly called out as unstarted in the README's Roadmap).
#
# Build from frontend/:
#   docker build -t tm-search-frontend .
# Or use docker-compose.yml at the repo root.
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
