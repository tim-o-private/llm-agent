# Stage 1: Build the React application
FROM node:20-alpine AS builder

WORKDIR /app
# Copy pnpm lockfile and workspace config first for better caching
COPY pnpm-lock.yaml ./
COPY pnpm-workspace.yaml ./

# Copy package.json files for root and webApp
COPY package.json ./
COPY webApp/package.json ./webApp/

# Install pnpm
RUN npm install -g pnpm

# Install dependencies
# This will install dependencies for the entire workspace, then filter for webApp
RUN pnpm install --frozen-lockfile

# Copy the rest of the webApp source code
COPY webApp/ ./webApp/

# Build-time args for Vite (provided by fly.toml [build.args] from Fly secrets)
# These are public values baked into the JS bundle — not truly secret.
ARG VITE_API_BASE_URL
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

# Build the webApp (clarity-frontend)
RUN VITE_API_BASE_URL="${VITE_API_BASE_URL}" \
    VITE_SUPABASE_URL="${VITE_SUPABASE_URL}" \
    VITE_SUPABASE_ANON_KEY="${VITE_SUPABASE_ANON_KEY}" \
    pnpm --filter clarity-frontend build

# Stage 2: Serve the static files with Nginx
FROM nginx:stable-alpine

# Copy built assets from the builder stage
COPY --from=builder /app/webApp/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY webApp/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"] 