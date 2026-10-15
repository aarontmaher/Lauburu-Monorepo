# Multi-stage Dockerfile for Lauburu Port 4000 Console (HTML Builder)
FROM dart:stable AS builder

WORKDIR /app
COPY pubspec.yaml ./
RUN dart pub get

COPY lib ./lib
# This script natively generates the index.html WebApp output
RUN dart run lib/main.dart

# Production Web Server
FROM nginx:alpine
COPY --from=builder /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/port_4000_flutter_rust/flutter_ui/build /usr/share/nginx/html 2>/dev/null || COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 4001
CMD ["nginx", "-g", "daemon off;"]
