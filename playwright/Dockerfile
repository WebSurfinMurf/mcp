# Use Official Microsoft Playwright Image for maximum compatibility
FROM mcr.microsoft.com/playwright:v1.45.0-jammy

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json ./

# Install dependencies
RUN npm install --production

# Copy application files
COPY server.js ./

# Set production environment
ENV NODE_ENV=production
ENV PORT=8080

# Create output directories with proper permissions
RUN mkdir -p /tmp/playwright-output && \
    chown -R pwuser:pwuser /tmp/playwright-output && \
    chown -R pwuser:pwuser /app

# Switch to non-root user (provided by Microsoft image)
USER pwuser

# Expose port
EXPOSE 8080

# Health check using node (no external dependencies)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD node -e "require('http').get('http://localhost:8080/health', (r) => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

# Start the service
CMD ["node", "server.js"]