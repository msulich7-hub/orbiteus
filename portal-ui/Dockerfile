# Dev image. Build context is the monorepo root (npm workspaces: admin-ui + portal-ui).
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY admin-ui/package.json ./admin-ui/
COPY portal-ui/package.json ./portal-ui/

RUN npm install --include=dev

COPY portal-ui ./portal-ui

WORKDIR /app/portal-ui

EXPOSE 3001
CMD ["npm", "run", "dev"]
