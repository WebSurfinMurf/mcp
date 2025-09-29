# syntax=docker/dockerfile:1

FROM node:20-bookworm-slim AS base
WORKDIR /app
ENV NODE_ENV=production

# install python for stdio bridge execution
RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json* ./
RUN npm install --omit=dev || npm install --omit=dev

COPY src ./src

CMD ["node", "src/index.js"]
