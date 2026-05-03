# Dev image. Build context is the monorepo root so npm workspaces can resolve
# `@orbiteus/ui` (PR 10 / ADR-0016).
FROM node:20-alpine

WORKDIR /app

# Copy workspace manifests first for cacheable npm install.
COPY package.json package-lock.json ./
COPY admin-ui/package.json ./admin-ui/
COPY portal-ui/package.json ./portal-ui/
COPY packages ./packages

RUN npm install --include=dev

# Source mounted as a volume in docker-compose dev profile.
COPY admin-ui ./admin-ui

WORKDIR /app/admin-ui

EXPOSE 3000
CMD ["npm", "run", "dev"]
