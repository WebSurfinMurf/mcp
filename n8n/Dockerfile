FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY src/ ./src/

# Make executable
RUN chmod +x src/index.js

# Run as node user
USER node

CMD ["node", "src/index.js"]
