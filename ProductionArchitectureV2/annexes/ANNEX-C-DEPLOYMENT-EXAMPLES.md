# PATRIOT Trading System - Deployment Examples and Configurations

## 📋 Document Information

**Document ID**: ANNEX-C-DEPLOYMENT-EXAMPLES  
**Version**: 2.0  
**Date**: September 2025  
**Authors**: Solution Architecture Team, DevOps Team  
**Status**: Draft  

> **Cross-References:**  
> - Infrastructure: [../04-INFRASTRUCTURE.md](../04-INFRASTRUCTURE.md)  
> - Implementation Roadmap: [../06-IMPLEMENTATION-ROADMAP.md](../06-IMPLEMENTATION-ROADMAP.md)  
> - Component Specifications: [../03-COMPONENT-SPECIFICATIONS.md](../03-COMPONENT-SPECIFICATIONS.md)

---

## 🎯 Deployment Overview

This annex provides complete deployment configurations for the PATRIOT trading system across different environments (development, staging, production). All examples are production-ready and include security, monitoring, and scalability considerations.

### Environment Strategy

**Development**: Local Docker Compose for rapid development and testing  
**Staging**: Cloud-based replica of production for integration testing  
**Production**: High-availability deployment with clustering and redundancy  

---

## 🐳 Docker Compose Configurations

### Development Environment

#### docker-compose.dev.yml
```yaml
version: '3.8'

name: patriot-development

networks:
  patriot-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  patriot-external:
    driver: bridge

volumes:
  postgres_dev_data:
  redis_dev_data:
  kafka_dev_data:
  zookeeper_dev_data:

services:
  # API Gateway
  kong:
    image: kong:3.4-alpine
    hostname: kong
    container_name: patriot-kong-dev
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yml
      KONG_PROXY_ACCESS_LOG: /dev/stdout
      KONG_ADMIN_ACCESS_LOG: /dev/stdout
      KONG_PROXY_ERROR_LOG: /dev/stderr
      KONG_ADMIN_ERROR_LOG: /dev/stderr
      KONG_ADMIN_LISTEN: "0.0.0.0:8001"
      KONG_PROXY_LISTEN: "0.0.0.0:8000"
    ports:
      - "8000:8000"  # Proxy port
      - "8001:8001"  # Admin API port (dev only)
    volumes:
      - ./config/kong/dev/kong.yml:/etc/kong/kong.yml:ro
    networks:
      - patriot-external
      - patriot-internal
    depends_on:
      - user-command-service
      - user-query-service
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "kong", "health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Core Command Services
  user-command-service:
    build:
      context: ./services/user-command-service
      dockerfile: Dockerfile.dev
      target: development
    hostname: user-command-service
    container_name: patriot-user-cmd-dev
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://patriot:dev_password@postgres:5432/patriot_dev
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BROKERS=kafka:9092
      - JWT_SECRET=dev_jwt_secret_change_in_production
      - API_KEY_ENCRYPTION_KEY=dev_encryption_key_32_characters
      - LOG_LEVEL=DEBUG
      - PROMETHEUS_ENABLED=true
      - JAEGER_ENDPOINT=http://jaeger:14268/api/traces
    ports:
      - "3001:3000"  # Development port mapping
    volumes:
      - ./services/user-command-service/src:/app/src:ro
      - ./services/common:/app/common:ro
    networks:
      - patriot-internal
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka:
        condition: service_started
    restart: unless-stopped
    develop:
      watch:
        - action: sync
          path: ./services/user-command-service/src
          target: /app/src
        - action: rebuild
          path: ./services/user-command-service/package.json

  order-command-service:
    build:
      context: ./services/order-command-service
      dockerfile: Dockerfile.dev
    hostname: order-command-service
    container_name: patriot-order-cmd-dev
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://patriot:dev_password@postgres:5432/patriot_dev
      - REDIS_URL=redis://redis:6379/1
      - KAFKA_BROKERS=kafka:9092
      - RISK_ENGINE_URL=http://risk-engine:3000
      - BINANCE_API_URL=https://testnet.binancefuture.com
      - BYBIT_API_URL=https://api-testnet.bybit.com
      - LOG_LEVEL=DEBUG
    ports:
      - "3004:3000"
    volumes:
      - ./services/order-command-service/src:/app/src:ro
      - ./services/common:/app/common:ro
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka
      - risk-engine
    restart: unless-stopped

  # Query Services
  user-query-service:
    build:
      context: ./services/user-query-service
      dockerfile: Dockerfile.dev
    hostname: user-query-service
    container_name: patriot-user-query-dev
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://patriot_readonly:dev_password@postgres:5432/patriot_dev
      - REDIS_URL=redis://redis:6379/2
      - KAFKA_BROKERS=kafka:9092
      - LOG_LEVEL=DEBUG
    ports:
      - "3002:3000"
    volumes:
      - ./services/user-query-service/src:/app/src:ro
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka
    restart: unless-stopped

  portfolio-query-service:
    build:
      context: ./services/portfolio-query-service
      dockerfile: Dockerfile.dev
    hostname: portfolio-query-service
    container_name: patriot-portfolio-query-dev
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://patriot_readonly:dev_password@postgres:5432/patriot_dev
      - REDIS_URL=redis://redis:6379/3
      - KAFKA_BROKERS=kafka:9092
      - TIMESCALEDB_URL=postgresql://patriot:dev_password@postgres:5432/patriot_dev
      - LOG_LEVEL=DEBUG
    ports:
      - "3003:3000"
    volumes:
      - ./services/portfolio-query-service/src:/app/src:ro
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka
    restart: unless-stopped

  # Domain Services
  trading-engine:
    build:
      context: ./services/trading-engine
      dockerfile: Dockerfile.dev
    hostname: trading-engine
    container_name: patriot-trading-engine-dev
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://patriot:dev_password@postgres:5432/patriot_dev
      - KAFKA_BROKERS=kafka:9092
      - BINANCE_API_URL=https://testnet.binancefuture.com
      - BYBIT_API_URL=https://api-testnet.bybit.com
      - ORDER_LIFECYCLE_SERVICE_URL=http://order-lifecycle-service:3000
      - LOG_LEVEL=DEBUG
    volumes:
      - ./services/trading-engine/src:/app/src:ro
    networks:
      - patriot-internal
    depends_on:
      - kafka
      - postgres
    restart: unless-stopped

  risk-engine:
    build:
      context: ./services/risk-engine
      dockerfile: Dockerfile.dev
    hostname: risk-engine
    container_name: patriot-risk-engine-dev
    environment:
      - NODE_ENV=development
      - DATABASE_URL=postgresql://patriot:dev_password@postgres:5432/patriot_dev
      - REDIS_URL=redis://redis:6379/4
      - KAFKA_BROKERS=kafka:9092
      - LOG_LEVEL=DEBUG
    ports:
      - "3006:3000"
    volumes:
      - ./services/risk-engine/src:/app/src:ro
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka
    restart: unless-stopped

  order-lifecycle-service:
    build:
      context: ./services/order-lifecycle-service
      dockerfile: Dockerfile.dev
    hostname: order-lifecycle-service
    container_name: patriot-order-lifecycle-dev
    environment:
      - NODE_ENV=development
      - KAFKA_BROKERS=kafka:9092
      - REDIS_URL=redis://redis:6379/5
      - TRADING_ENGINE_URL=http://trading-engine:3000
      - LOG_LEVEL=DEBUG
    volumes:
      - ./services/order-lifecycle-service/src:/app/src:ro
    networks:
      - patriot-internal
    depends_on:
      - kafka
      - redis
      - trading-engine
    restart: unless-stopped

  # Data Services
  market-data-service:
    build:
      context: ./services/market-data-service
      dockerfile: Dockerfile.dev
    hostname: market-data-service
    container_name: patriot-market-data-dev
    environment:
      - NODE_ENV=development
      - KAFKA_BROKERS=kafka:9092
      - REDIS_URL=redis://redis:6379/6
      - BINANCE_WS_URL=wss://stream.binancefuture.com/ws
      - BYBIT_WS_URL=wss://stream-testnet.bybit.com/v5/public/linear
      - LOG_LEVEL=DEBUG
    volumes:
      - ./services/market-data-service/src:/app/src:ro
    networks:
      - patriot-internal
    depends_on:
      - kafka
      - redis
    restart: unless-stopped

  # Infrastructure Services
  postgres:
    image: timescale/timescaledb:latest-pg15
    hostname: postgres
    container_name: patriot-postgres-dev
    environment:
      POSTGRES_DB: patriot_dev
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD: dev_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8 --locale=en_US.UTF-8"
      TIMESCALEDB_TELEMETRY: "off"
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d:ro
      - ./database/dev-data:/dev-data:ro
      - ./config/postgres/dev/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: postgres -c 'config_file=/etc/postgresql/postgresql.conf'
    networks:
      - patriot-internal
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U patriot -d patriot_dev"]
      interval: 10s
      timeout: 5s
      retries: 5
    shm_size: 256MB

  redis:
    image: redis:7.2-alpine
    hostname: redis
    container_name: patriot-redis-dev
    command: >
      redis-server
      --appendonly yes
      --maxmemory 512mb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data
      - ./config/redis/dev/redis.conf:/etc/redis/redis.conf:ro
    networks:
      - patriot-internal
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    hostname: zookeeper
    container_name: patriot-zookeeper-dev
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_LOG4J_LOGGERS: "org.apache.zookeeper=WARN"
      ZOOKEEPER_LOG4J_ROOT_LOGLEVEL: "WARN"
    volumes:
      - zookeeper_dev_data:/var/lib/zookeeper/data
    networks:
      - patriot-internal
    restart: unless-stopped

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    hostname: kafka
    container_name: patriot-kafka-dev
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:9093
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_NUM_PARTITIONS: 6
      KAFKA_DEFAULT_REPLICATION_FACTOR: 1
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 1
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 1
      KAFKA_LOG4J_LOGGERS: "kafka.controller=WARN,kafka.producer.async.DefaultEventHandler=WARN,state.change.logger=WARN"
      KAFKA_LOG4J_ROOT_LOGLEVEL: "WARN"
    ports:
      - "9093:9093"  # External access
    volumes:
      - kafka_dev_data:/var/lib/kafka/data
    networks:
      - patriot-internal
    depends_on:
      - zookeeper
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Development & Monitoring Tools
  kafka-ui:
    image: provectuslabs/kafka-ui:latest
    hostname: kafka-ui
    container_name: patriot-kafka-ui-dev
    environment:
      KAFKA_CLUSTERS_0_NAME: "Development Cluster"
      KAFKA_CLUSTERS_0_BOOTSTRAPSERVERS: kafka:9092
      KAFKA_CLUSTERS_0_ZOOKEEPER: zookeeper:2181
    ports:
      - "8080:8080"
    networks:
      - patriot-internal
    depends_on:
      - kafka
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:v2.47.0
    hostname: prometheus
    container_name: patriot-prometheus-dev
    ports:
      - "9090:9090"
    volumes:
      - ./config/prometheus/dev/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./config/prometheus/dev/rules:/etc/prometheus/rules:ro
    networks:
      - patriot-internal
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
      - '--web.enable-admin-api'

  grafana:
    image: grafana/grafana:10.1.0
    hostname: grafana
    container_name: patriot-grafana-dev
    environment:
      GF_SECURITY_ADMIN_PASSWORD: dev_password
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_INSTALL_PLUGINS: "redis-datasource,kafka-datasource"
    ports:
      - "3000:3000"
    volumes:
      - ./config/grafana/dev/grafana.ini:/etc/grafana/grafana.ini:ro
      - ./config/grafana/dev/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./config/grafana/dev/datasources:/etc/grafana/provisioning/datasources:ro
    networks:
      - patriot-internal
    depends_on:
      - prometheus
    restart: unless-stopped

  jaeger:
    image: jaegertracing/all-in-one:1.49
    hostname: jaeger
    container_name: patriot-jaeger-dev
    environment:
      COLLECTOR_OTLP_ENABLED: "true"
    ports:
      - "14268:14268"  # jaeger-collector HTTP
      - "16686:16686"  # jaeger-query HTTP
    networks:
      - patriot-internal
    restart: unless-stopped

  # Database Administration
  adminer:
    image: adminer:4.8.1
    hostname: adminer
    container_name: patriot-adminer-dev
    environment:
      ADMINER_DEFAULT_SERVER: postgres
    ports:
      - "8081:8080"
    networks:
      - patriot-internal
    depends_on:
      - postgres
    restart: unless-stopped

  # Redis Administration
  redis-commander:
    image: rediscommander/redis-commander:latest
    hostname: redis-commander
    container_name: patriot-redis-commander-dev
    environment:
      REDIS_HOSTS: "local:redis:6379"
      HTTP_USER: admin
      HTTP_PASSWORD: dev_password
    ports:
      - "8082:8081"
    networks:
      - patriot-internal
    depends_on:
      - redis
    restart: unless-stopped
```

### Development Scripts

#### scripts/dev-setup.sh
```bash
#!/bin/bash
# Development environment setup script

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 Setting up PATRIOT Development Environment..."

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p {config/{kong,postgres,redis,prometheus,grafana}/{dev,staging,prod}
mkdir -p database/{init,migrations,seeds}
mkdir -p logs/dev
mkdir -p certs/dev

# Generate development certificates
if [[ ! -f "certs/dev/patriot-dev.crt" ]]; then
    echo "🔐 Generating development SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
        -keyout certs/dev/patriot-dev.key \\
        -out certs/dev/patriot-dev.crt \\
        -subj "/CN=localhost"
fi

# Create development environment file
if [[ ! -f ".env.dev" ]]; then
    echo "⚙️ Creating development environment file..."
    cat > .env.dev << 'EOF'
# PATRIOT Development Environment
NODE_ENV=development
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql://patriot:dev_password@localhost:5432/patriot_dev
DATABASE_READONLY_URL=postgresql://patriot_readonly:dev_password@localhost:5432/patriot_dev

# Redis
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BROKERS=localhost:9093

# Security (CHANGE IN PRODUCTION!)
JWT_SECRET=dev_jwt_secret_change_in_production_32chars
API_KEY_ENCRYPTION_KEY=dev_encryption_key_32_characters_long

# Exchange APIs (Testnet)
BINANCE_API_URL=https://testnet.binancefuture.com
BYBIT_API_URL=https://api-testnet.bybit.com

# Monitoring
PROMETHEUS_ENABLED=true
JAEGER_ENABLED=true
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# Development
HOT_RELOAD_ENABLED=true
DEBUG_SQL=true
MOCK_EXCHANGES=false
EOF
    echo "✅ Created .env.dev file"
fi

# Create Kong development configuration
echo "🦍 Setting up Kong configuration..."
cat > config/kong/dev/kong.yml << 'EOF'
_format_version: "3.0"
_transform: true

services:
  - name: user-command-service
    url: http://user-command-service:3000
    plugins:
      - name: prometheus
        config:
          per_consumer: true
      - name: cors
        config:
          origins: ["http://localhost:3000", "http://localhost:8080"]
          credentials: true

  - name: user-query-service
    url: http://user-query-service:3000
    plugins:
      - name: prometheus

  - name: order-command-service
    url: http://order-command-service:3000
    plugins:
      - name: prometheus
      - name: rate-limiting
        config:
          minute: 1000
          policy: redis
          redis_host: redis

routes:
  - name: user-commands
    service: user-command-service
    paths:
      - /api/v1/users
    methods:
      - GET
      - POST
      - PUT
      - DELETE

  - name: user-queries
    service: user-query-service
    paths:
      - /api/v1/users/query
    methods:
      - GET

  - name: order-commands
    service: order-command-service
    paths:
      - /api/v1/orders
    methods:
      - GET
      - POST
      - PUT
      - DELETE

plugins:
  - name: prometheus
    config:
      per_consumer: true
      status_code_metrics: true
      latency_metrics: true
EOF

# Create Prometheus development configuration
echo "📊 Setting up Prometheus configuration..."
cat > config/prometheus/dev/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "rules/*.yml"

scrape_configs:
  - job_name: 'patriot-services'
    static_configs:
      - targets:
          - 'user-command-service:3000'
          - 'user-query-service:3000'
          - 'order-command-service:3000'
          - 'portfolio-query-service:3000'
          - 'trading-engine:3000'
          - 'risk-engine:3000'
    scrape_interval: 10s
    metrics_path: /metrics

  - job_name: 'kong'
    static_configs:
      - targets: ['kong:8001']
    scrape_interval: 10s
    metrics_path: /metrics

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']
    scrape_interval: 30s
EOF

# Create database initialization script
echo "🗄️ Setting up database initialization..."
cat > database/init/01-init-dev.sql << 'EOF'
-- PATRIOT Development Database Initialization

-- Create additional users for development
CREATE USER patriot_readonly WITH PASSWORD 'dev_password';
CREATE USER patriot_monitor WITH PASSWORD 'dev_password';

-- Grant permissions
GRANT CONNECT ON DATABASE patriot_dev TO patriot_readonly;
GRANT CONNECT ON DATABASE patriot_dev TO patriot_monitor;
GRANT USAGE ON SCHEMA public TO patriot_readonly;
GRANT USAGE ON SCHEMA public TO patriot_monitor;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Development-specific settings
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 0;
SELECT pg_reload_conf();

-- Insert development seed data
INSERT INTO system_logs (log_level, message, created_at) VALUES
    ('INFO', 'Development environment initialized', NOW());
EOF

# Create development seed data
cat > database/seeds/dev-seed-data.sql << 'EOF'
-- Development seed data for PATRIOT system

-- Insert test exchanges
INSERT INTO exchanges (name, display_name, api_base_url, websocket_url, is_active, supports_futures) VALUES
    ('BINANCE', 'Binance Futures', 'https://testnet.binancefuture.com', 'wss://stream.binancefuture.com/ws', true, true),
    ('BYBIT', 'Bybit', 'https://api-testnet.bybit.com', 'wss://stream-testnet.bybit.com/v5/public/linear', true, true);

-- Insert test symbols
INSERT INTO symbols (symbol, base_asset, quote_asset, tick_size, step_size, min_quantity, is_active) VALUES
    ('BTCUSDT', 'BTC', 'USDT', 0.01, 0.001, 0.001, true),
    ('ETHUSDT', 'ETH', 'USDT', 0.01, 0.001, 0.001, true),
    ('ADAUSDT', 'ADA', 'USDT', 0.0001, 1, 1, true);

-- Insert test strategies
INSERT INTO strategies (name, description, strategy_type, risk_level, min_balance_usd, supported_symbols, supported_exchanges) VALUES
    ('Dev Scalping Strategy', 'Development scalping strategy for testing', 'SCALPING', 'MEDIUM', 1000, ARRAY['BTCUSDT', 'ETHUSDT'], ARRAY['BINANCE', 'BYBIT']),
    ('Dev Swing Strategy', 'Development swing strategy for testing', 'SWING', 'LOW', 5000, ARRAY['BTCUSDT'], ARRAY['BINANCE']);

-- Insert global risk parameters
INSERT INTO risk_parameters (parameter_type, parameter_name, parameter_value, parameter_unit) VALUES
    ('GLOBAL', 'max_position_size_usd', 10000.00, 'USD'),
    ('GLOBAL', 'max_daily_loss_percent', 10.00, '%'),
    ('GLOBAL', 'max_leverage', 5.00, 'ratio');

-- Log seed data insertion
INSERT INTO system_logs (log_level, message, created_at) VALUES
    ('INFO', 'Development seed data inserted', NOW());
EOF

# Pull and build images
echo "📦 Pulling and building Docker images..."
docker-compose -f docker-compose.dev.yml pull --quiet

# Start infrastructure services first
echo "🏗️ Starting infrastructure services..."
docker-compose -f docker-compose.dev.yml up -d postgres redis zookeeper kafka

# Wait for services to be ready
echo "⏳ Waiting for infrastructure services..."
timeout 60 bash -c 'until docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U patriot -d patriot_dev; do sleep 2; done'
timeout 60 bash -c 'until docker-compose -f docker-compose.dev.yml exec redis redis-cli ping; do sleep 2; done'
timeout 60 bash -c 'until docker-compose -f docker-compose.dev.yml exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092; do sleep 2; done'

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose -f docker-compose.dev.yml exec postgres psql -U patriot -d patriot_dev -f /dev-data/dev-seed-data.sql

# Start application services
echo "🚀 Starting application services..."
docker-compose -f docker-compose.dev.yml up -d

# Wait for all services to be healthy
echo "🏥 Performing health checks..."
timeout 120 bash -c 'until curl -f http://localhost:8000/health 2>/dev/null; do sleep 5; done'

echo "✅ Development environment setup complete!"
echo ""
echo "🌐 Available endpoints:"
echo "  API Gateway:         http://localhost:8000"
echo "  Kong Admin:          http://localhost:8001"
echo "  Grafana:            http://localhost:3000 (admin/dev_password)"
echo "  Prometheus:         http://localhost:9090"
echo "  Kafka UI:           http://localhost:8080"
echo "  Jaeger:             http://localhost:16686"
echo "  Adminer:            http://localhost:8081"
echo "  Redis Commander:    http://localhost:8082"
echo ""
echo "📋 To view logs: docker-compose -f docker-compose.dev.yml logs -f"
echo "🛑 To stop: docker-compose -f docker-compose.dev.yml down"
echo "🧹 To clean: docker-compose -f docker-compose.dev.yml down -v"
```

#### scripts/dev-test.sh
```bash
#!/bin/bash
# Development testing script

set -euo pipefail

echo "🧪 Running PATRIOT Development Tests..."

# Health check all services
echo "🏥 Checking service health..."
services=(
    "http://localhost:8000/health:API Gateway"
    "http://localhost:3001/health:User Command Service"
    "http://localhost:3002/health:User Query Service"
    "http://localhost:3004/health:Order Command Service"
    "http://localhost:9090/-/healthy:Prometheus"
    "http://localhost:3000/api/health:Grafana"
)

for service in "${services[@]}"; do
    url="${service%%:*}"
    name="${service##*:}"
    
    if curl -f "$url" &>/dev/null; then
        echo "✅ $name: healthy"
    else
        echo "❌ $name: unhealthy"
    fi
done

# Test database connectivity
echo "🗄️ Testing database connectivity..."
if docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U patriot -d patriot_dev &>/dev/null; then
    echo "✅ PostgreSQL: connected"
else
    echo "❌ PostgreSQL: connection failed"
fi

# Test Redis connectivity
echo "🔴 Testing Redis connectivity..."
if docker-compose -f docker-compose.dev.yml exec redis redis-cli ping | grep -q PONG; then
    echo "✅ Redis: connected"
else
    echo "❌ Redis: connection failed"
fi

# Test Kafka connectivity
echo "📨 Testing Kafka connectivity..."
if docker-compose -f docker-compose.dev.yml exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 &>/dev/null; then
    echo "✅ Kafka: connected"
else
    echo "❌ Kafka: connection failed"
fi

# Test basic API endpoints
echo "🌐 Testing API endpoints..."

# Test user registration
response=$(curl -s -w "%{http_code}" -X POST http://localhost:8000/api/v1/users \\
    -H "Content-Type: application/json" \\
    -d '{
        "telegram_id": 123456789,
        "username": "test_user_dev",
        "email": "test@example.com",
        "risk_profile": "MEDIUM"
    }' -o /tmp/user_response.json)

if [[ "$response" == "201" ]]; then
    echo "✅ User registration: success"
    user_id=$(jq -r '.user_id' /tmp/user_response.json)
else
    echo "❌ User registration: failed (HTTP $response)"
fi

# Test Kong metrics
if curl -f http://localhost:8001/metrics &>/dev/null; then
    echo "✅ Kong metrics: available"
else
    echo "❌ Kong metrics: unavailable"
fi

echo ""
echo "🏁 Development test completed!"
echo "View detailed logs: docker-compose -f docker-compose.dev.yml logs -f [service_name]"
```

### Staging Environment Configuration

#### docker-compose.staging.yml
```yaml
version: '3.8'

name: patriot-staging

networks:
  patriot-internal:
    driver: overlay
    encrypted: true
  patriot-external:
    driver: overlay
  monitoring:
    driver: overlay

configs:
  kong_config:
    file: ./config/kong/staging/kong.yml
  prometheus_config:
    file: ./config/prometheus/staging/prometheus.yml
  grafana_config:
    file: ./config/grafana/staging/grafana.ini

secrets:
  jwt_secret:
    external: true
  encryption_key:
    external: true
  postgres_password:
    external: true

services:
  # API Gateway (Load Balanced)
  kong:
    image: kong:3.4-alpine
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yml
      KONG_PROXY_LISTEN: "0.0.0.0:8000 ssl http2"
      KONG_SSL_CERT: /certs/staging.crt
      KONG_SSL_CERT_KEY: /certs/staging.key
      KONG_ADMIN_LISTEN: "127.0.0.1:8001"
      KONG_NGINX_WORKER_PROCESSES: "4"
      KONG_NGINX_HTTP_CLIENT_MAX_BODY_SIZE: "10m"
    ports:
      - "443:8000"
    configs:
      - source: kong_config
        target: /etc/kong/kong.yml
    volumes:
      - ./certs/staging:/certs:ro
    networks:
      - patriot-external
      - patriot-internal
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

  # Command Services (Scaled)
  user-command-service:
    image: patriot/user-command-service:${VERSION}
    environment:
      - NODE_ENV=staging
      - DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres:5432/patriot_staging
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BROKERS=kafka:9092
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - API_KEY_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
      - LOG_LEVEL=INFO
      - PROMETHEUS_ENABLED=true
      - JAEGER_ENDPOINT=http://jaeger:14268/api/traces
    secrets:
      - jwt_secret
      - encryption_key
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: any
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  order-command-service:
    image: patriot/order-command-service:${VERSION}
    environment:
      - NODE_ENV=staging
      - DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres:5432/patriot_staging
      - REDIS_URL=redis://redis:6379/1
      - KAFKA_BROKERS=kafka:9092
      - RISK_ENGINE_URL=http://risk-engine:3000
      - BINANCE_API_URL=https://testnet.binancefuture.com
      - BYBIT_API_URL=https://api-testnet.bybit.com
      - LOG_LEVEL=INFO
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 3  # Higher replica count for critical service
      resources:
        limits:
          memory: 1G
          cpus: '1'
        reservations:
          memory: 512M
          cpus: '0.5'

  # Database Cluster
  postgres:
    image: timescale/timescaledb-ha:pg15-latest
    environment:
      POSTGRES_DB: patriot_staging
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_REPLICA_USER: replicator
      POSTGRES_REPLICA_PASSWORD_FILE: /run/secrets/postgres_password
      TIMESCALEDB_TELEMETRY: "off"
    secrets:
      - postgres_password
    volumes:
      - postgres_staging_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d:ro
      - ./config/postgres/staging/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    command: postgres -c 'config_file=/etc/postgresql/postgresql.conf'
    networks:
      - patriot-internal
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U patriot -d patriot_staging"]
      interval: 30s
      timeout: 10s
      retries: 5

  postgres-replica:
    image: timescale/timescaledb-ha:pg15-latest
    environment:
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      PGUSER: postgres
      POSTGRES_PRIMARY_HOST: postgres
      POSTGRES_PRIMARY_PORT: 5432
      POSTGRES_REPLICA_USER: replicator
      POSTGRES_REPLICA_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
    networks:
      - patriot-internal
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 2G
          cpus: '1'
    depends_on:
      - postgres
    command: >
      bash -c "
        until pg_basebackup -h postgres -D /var/lib/postgresql/data -U replicator -v -P -R; do
          sleep 5
        done
        postgres
      "

  # Redis Cluster
  redis-master:
    image: redis:7.2-alpine
    command: >
      redis-server
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
      --requirepass ${REDIS_PASSWORD}
    networks:
      - patriot-internal
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.role == manager
      resources:
        limits:
          memory: 2.5G
          cpus: '1'
        reservations:
          memory: 1G
          cpus: '0.5'

  redis-replica:
    image: redis:7.2-alpine
    command: >
      redis-server
      --replicaof redis-master 6379
      --masterauth ${REDIS_PASSWORD}
      --requirepass ${REDIS_PASSWORD}
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
    networks:
      - patriot-internal
    depends_on:
      - redis-master
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2.5G
          cpus: '1'

  # Kafka Cluster
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_SERVERS: zookeeper:2888:3888
      ZOOKEEPER_SERVER_ID: 1
    networks:
      - patriot-internal
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 1G
          cpus: '0.5'

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
      KAFKA_NUM_PARTITIONS: 12
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 3
      KAFKA_TRANSACTION_STATE_LOG_MIN_ISR: 2
      KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR: 3
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_LOG_RETENTION_BYTES: 1073741824
      KAFKA_LOG_SEGMENT_BYTES: 268435456
    networks:
      - patriot-internal
    depends_on:
      - zookeeper
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1'

  # Monitoring Stack
  prometheus:
    image: prom/prometheus:v2.47.0
    configs:
      - source: prometheus_config
        target: /etc/prometheus/prometheus.yml
    volumes:
      - prometheus_staging_data:/prometheus
    networks:
      - monitoring
      - patriot-internal
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 2G
          cpus: '1'
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'

  grafana:
    image: grafana/grafana:10.1.0
    environment:
      GF_SECURITY_ADMIN_PASSWORD__FILE: /run/secrets/grafana_password
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SMTP_ENABLED: "true"
      GF_SMTP_HOST: smtp.mailgun.org:587
      GF_SMTP_USER: ${SMTP_USER}
      GF_SMTP_PASSWORD: ${SMTP_PASSWORD}
    configs:
      - source: grafana_config
        target: /etc/grafana/grafana.ini
    volumes:
      - grafana_staging_data:/var/lib/grafana
      - ./config/grafana/staging/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks:
      - monitoring
      - patriot-internal
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  # Log Management
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
      - xpack.security.enabled=false
    networks:
      - monitoring
    deploy:
      replicas: 1
      resources:
        limits:
          memory: 2G
          cpus: '1'

  logstash:
    image: docker.elastic.co/logstash/logstash:8.10.0
    volumes:
      - ./config/logstash/staging/pipeline:/usr/share/logstash/pipeline:ro
    networks:
      - monitoring
      - patriot-internal
    depends_on:
      - elasticsearch
    deploy:
      replicas: 1

  kibana:
    image: docker.elastic.co/kibana/kibana:8.10.0
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200
    networks:
      - monitoring
    depends_on:
      - elasticsearch
    deploy:
      replicas: 1

volumes:
  postgres_staging_data:
  redis_staging_data:
  kafka_staging_data:
  prometheus_staging_data:
  grafana_staging_data:
  elasticsearch_staging_data:
```

### Production Environment Configuration

#### docker-compose.prod.yml
```yaml
version: '3.8'

name: patriot-production

networks:
  patriot-internal:
    driver: overlay
    encrypted: true
    attachable: false
  patriot-external:
    driver: overlay
    attachable: false
  monitoring:
    driver: overlay
    encrypted: true
    attachable: false

configs:
  kong_config:
    external: true
  prometheus_config:
    external: true
  grafana_config:
    external: true
  nginx_config:
    external: true

secrets:
  jwt_secret:
    external: true
  encryption_key:
    external: true
  postgres_password:
    external: true
  redis_password:
    external: true
  ssl_cert:
    external: true
  ssl_key:
    external: true

services:
  # Load Balancer (NGINX)
  nginx:
    image: nginx:1.25-alpine
    ports:
      - "80:80"
      - "443:443"
    configs:
      - source: nginx_config
        target: /etc/nginx/nginx.conf
    secrets:
      - source: ssl_cert
        target: /etc/ssl/certs/patriot.crt
      - source: ssl_key
        target: /etc/ssl/private/patriot.key
    networks:
      - patriot-external
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      placement:
        constraints:
          - node.role == manager
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.25'

  # API Gateway Cluster
  kong:
    image: kong:3.4-alpine
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yml
      KONG_PROXY_LISTEN: "0.0.0.0:8000"
      KONG_ADMIN_LISTEN: "127.0.0.1:8001"
      KONG_NGINX_WORKER_PROCESSES: "auto"
      KONG_NGINX_HTTP_CLIENT_MAX_BODY_SIZE: "10m"
      KONG_LOG_LEVEL: "warn"
      KONG_PLUGINS: "bundled,prometheus"
    configs:
      - source: kong_config
        target: /etc/kong/kong.yml
    networks:
      - patriot-external  
      - patriot-internal
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 30s
        failure_action: rollback
        monitor: 60s
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3
        window: 120s
      resources:
        limits:
          memory: 1G
          cpus: '1'
        reservations:
          memory: 512M
          cpus: '0.5'
    healthcheck:
      test: ["CMD", "kong", "health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s

  # Command Services - Production Scale
  user-command-service:
    image: patriot/user-command-service:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres-primary:5432/patriot_prod
      - REDIS_URL=redis://redis-cluster:6379
      - KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
      - JWT_SECRET_FILE=/run/secrets/jwt_secret
      - API_KEY_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
      - LOG_LEVEL=WARN
      - PROMETHEUS_ENABLED=true
      - RATE_LIMIT_ENABLED=true
      - CIRCUIT_BREAKER_ENABLED=true
    secrets:
      - jwt_secret
      - encryption_key
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 4
      update_config:
        parallelism: 2
        delay: 30s
        failure_action: rollback
        monitor: 120s
      restart_policy:
        condition: any
        delay: 10s
        max_attempts: 3
      resources:
        limits:
          memory: 1G
          cpus: '1'
        reservations:
          memory: 512M
          cpus: '0.5'
      placement:
        max_replicas_per_node: 2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  order-command-service:
    image: patriot/order-command-service:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres-primary:5432/patriot_prod
      - REDIS_URL=redis://redis-cluster:6379
      - KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
      - RISK_ENGINE_URL=http://risk-engine:3000
      - BINANCE_API_URL=https://fapi.binance.com
      - BYBIT_API_URL=https://api.bybit.com
      - LOG_LEVEL=INFO
      - MAX_CONCURRENT_ORDERS=1000
      - ORDER_TIMEOUT_MS=30000
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 6  # Critical service - highest replica count
      update_config:
        parallelism: 2
        delay: 45s
        failure_action: rollback
      resources:
        limits:
          memory: 2G
          cpus: '2'
        reservations:
          memory: 1G
          cpus: '1'
      placement:
        max_replicas_per_node: 3

  # Query Services - Optimized for Read Load
  user-query-service:
    image: patriot/user-query-service:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://patriot_readonly:${POSTGRES_PASSWORD}@postgres-replica:5432/patriot_prod
      - REDIS_URL=redis://redis-cluster:6379
      - KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
      - CACHE_TTL=300
      - READ_PREFERENCE=secondary
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 4
      resources:
        limits:
          memory: 1G
          cpus: '1'
        reservations:
          memory: 512M
          cpus: '0.5'

  portfolio-query-service:
    image: patriot/portfolio-query-service:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://patriot_readonly:${POSTGRES_PASSWORD}@postgres-replica:5432/patriot_prod
      - TIMESCALEDB_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres-primary:5432/patriot_prod
      - REDIS_URL=redis://redis-cluster:6379
      - KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
      - CACHE_TTL=60
      - SNAPSHOT_REFRESH_INTERVAL=30
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 5  # High read load
      resources:
        limits:
          memory: 1.5G
          cpus: '1'

  # Domain Services
  trading-engine:
    image: patriot/trading-engine:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres-primary:5432/patriot_prod
      - KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
      - ORDER_LIFECYCLE_SERVICE_URL=http://order-lifecycle-service:3000
      - EXCHANGE_TIMEOUT_MS=5000
      - MAX_RETRY_ATTEMPTS=3
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 3  # Stateful service - controlled scaling
      update_config:
        parallelism: 1
        delay: 60s
      resources:
        limits:
          memory: 2G
          cpus: '1.5'

  risk-engine:
    image: patriot/risk-engine:${VERSION}
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres-primary:5432/patriot_prod
      - REDIS_URL=redis://redis-cluster:6379
      - KAFKA_BROKERS=kafka-1:9092,kafka-2:9092,kafka-3:9092
      - RISK_CALCULATION_INTERVAL=30
      - VAR_CONFIDENCE_LEVEL=0.95
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '2'
        reservations:
          memory: 1G
          cpus: '1'

  # Database Cluster (PostgreSQL + TimescaleDB)
  postgres-primary:
    image: timescale/timescaledb-ha:pg15-latest
    environment:
      POSTGRES_DB: patriot_prod
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_REPLICA_USER: replicator
      POSTGRES_REPLICA_PASSWORD_FILE: /run/secrets/postgres_password
      TIMESCALEDB_TELEMETRY: "off"
      POSTGRES_INITDB_ARGS: "--data-checksums"
    secrets:
      - postgres_password
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d:ro
      - ./config/postgres/prod/postgresql.conf:/etc/postgresql/postgresql.conf:ro
      - ./config/postgres/prod/pg_hba.conf:/etc/postgresql/pg_hba.conf:ro
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
      -c hba_file=/etc/postgresql/pg_hba.conf
    networks:
      - patriot-internal
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.postgres-primary == true
      resources:
        limits:
          memory: 8G
          cpus: '4'
        reservations:
          memory: 4G
          cpus: '2'
      restart_policy:
        condition: any
        delay: 10s
        max_attempts: 5
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U patriot -d patriot_prod"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  postgres-replica:
    image: timescale/timescaledb-ha:pg15-latest
    environment:
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      PGUSER: postgres
      POSTGRES_PRIMARY_HOST: postgres-primary
      POSTGRES_PRIMARY_PORT: 5432
      POSTGRES_REPLICA_USER: replicator
      POSTGRES_REPLICA_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_SYNCHRONOUS_COMMIT: "on"
      POSTGRES_MAX_WAL_SENDERS: 5
      POSTGRES_WAL_LEVEL: replica
    secrets:
      - postgres_password
    volumes:
      - postgres_replica_data:/var/lib/postgresql/data
    networks:
      - patriot-internal
    depends_on:
      - postgres-primary
    deploy:
      replicas: 2
      placement:
        constraints:
          - node.labels.postgres-replica == true
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
    command: >
      bash -c "
        until pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U replicator -v -P -R; do
          sleep 5
        done
        postgres -c hot_standby=on -c wal_level=replica
      "

  # Redis Cluster
  redis-cluster:
    image: redis:7.2-alpine
    command: >
      redis-server
      --cluster-enabled yes
      --cluster-config-file nodes.conf
      --cluster-node-timeout 5000
      --appendonly yes
      --maxmemory 4gb
      --maxmemory-policy allkeys-lru
      --requirepass ${REDIS_PASSWORD}
      --save 900 1
      --save 300 10
      --save 60 10000
    secrets:
      - redis_password
    networks:
      - patriot-internal
    deploy:
      replicas: 6  # 3 masters + 3 replicas
      endpoint_mode: dnsrr
      resources:
        limits:
          memory: 4.5G
          cpus: '1'
        reservations:
          memory: 2G
          cpus: '0.5'

  # Kafka Cluster (High Availability)
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
      ZOOKEEPER_INIT_LIMIT: 10
      ZOOKEEPER_SYNC_LIMIT: 5
      ZOOKEEPER_SERVERS: zookeeper:2888:3888
    networks:
      - patriot-internal
    deploy:
      replicas: 3
      placement:
        max_replicas_per_node: 1
      resources:
        limits:
          memory: 2G
          cpus: '1'

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"
      KAFKA_DEFAULT_REPLICATION_FACTOR: 3
      KAFKA_MIN_INSYNC_REPLICAS: 2
      KAFKA_NUM_NETWORK_THREADS: 8
      KAFKA_NUM_IO_THREADS: 8
      KAFKA_SOCKET_SEND_BUFFER_BYTES: 102400
      KAFKA_SOCKET_RECEIVE_BUFFER_BYTES: 102400
      KAFKA_SOCKET_REQUEST_MAX_BYTES: 104857600
      KAFKA_NUM_PARTITIONS: 12
      KAFKA_NUM_REPLICA_FETCHERS: 4
      KAFKA_REPLICA_FETCH_MAX_BYTES: 1048576
      KAFKA_LOG_RETENTION_HOURS: 168
      KAFKA_LOG_RETENTION_BYTES: 10737418240
      KAFKA_LOG_SEGMENT_BYTES: 1073741824
      KAFKA_LOG_CLEANUP_POLICY: "delete"
      KAFKA_COMPRESSION_TYPE: "snappy"
    networks:
      - patriot-internal
    depends_on:
      - zookeeper
    deploy:
      replicas: 3
      placement:
        max_replicas_per_node: 1
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'

volumes:
  postgres_primary_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /data/postgres-primary
  postgres_replica_data:
    driver: local
    driver_opts:
      type: none  
      o: bind
      device: /data/postgres-replica
  redis_cluster_data:
  kafka_data:
  prometheus_data:
  grafana_data:
  elasticsearch_data:
```

### Environment-Specific Configuration Files

#### config/kong/prod/kong.yml
```yaml
_format_version: "3.0"
_transform: true

services:
  - name: user-command-service
    url: http://user-command-service:3000
    connect_timeout: 5000
    write_timeout: 60000
    read_timeout: 60000
    retries: 3
    plugins:
      - name: prometheus
        config:
          per_consumer: true
          status_code_metrics: true
          latency_metrics: true
      - name: rate-limiting
        config:
          minute: 1000
          hour: 10000
          policy: redis
          redis_host: redis-cluster
          hide_client_headers: true
      - name: request-size-limiting
        config:
          allowed_payload_size: 10
      - name: cors
        config:
          origins: ["https://admin.patriot-trading.com"]
          credentials: true
          max_age: 3600

  - name: order-command-service
    url: http://order-command-service:3000
    connect_timeout: 2000
    write_timeout: 30000
    read_timeout: 30000
    retries: 5
    plugins:
      - name: prometheus
      - name: rate-limiting
        config:
          minute: 500  # Lower limit for critical service
          hour: 5000
          policy: redis
          redis_host: redis-cluster
      - name: request-termination
        config:
          status_code: 503
          message: "Service temporarily unavailable"
        enabled: false  # Enable during maintenance

routes:
  - name: user-management
    service: user-command-service
    paths:
      - /api/v1/users
    methods:
      - GET
      - POST
      - PUT
      - DELETE
    plugins:
      - name: ip-restriction
        config:
          allow: ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]

  - name: order-management
    service: order-command-service
    paths:
      - /api/v1/orders
    methods:
      - GET
      - POST
      - PUT
      - DELETE
    plugins:
      - name: response-ratelimiting
        config:
          limits:
            order_creation:
              minute: 100

plugins:
  - name: prometheus
    config:
      per_consumer: true
      status_code_metrics: true
      latency_metrics: true
      bandwidth_metrics: true

  - name: datadog
    config:
      host: datadog-agent
      port: 8125
      metrics:
        - name: request_count
          stat_type: counter
        - name: request_size
          stat_type: histogram
        - name: response_size
          stat_type: histogram

  - name: file-log
    config:
      path: /var/log/kong/access.log

upstreams:
  - name: user-command-upstream
    algorithm: round-robin
    healthchecks:
      active:
        healthy:
          interval: 30
          http_statuses: [200, 201, 202]
        unhealthy:
          interval: 30
          http_failures: 3
    targets:
      - target: user-command-service:3000
        weight: 100
```

#### config/postgres/prod/postgresql.conf
```conf
# PostgreSQL Production Configuration for PATRIOT
# Optimized for trading system workload

# Connection Settings
listen_addresses = '*'
port = 5432
max_connections = 300
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 128MB
maintenance_work_mem = 2GB

# Write-Ahead Logging
wal_level = replica
fsync = on
synchronous_commit = on
wal_sync_method = fdatasync
full_page_writes = on
wal_compression = on
wal_log_hints = on
wal_buffers = 64MB
wal_writer_delay = 200ms
commit_delay = 0
commit_siblings = 5

# Replication
max_wal_senders = 10
max_replication_slots = 10
hot_standby = on
hot_standby_feedback = on
wal_receiver_status_interval = 10s
wal_receiver_timeout = 60s
wal_retrieve_retry_interval = 5s

# Query Planner
random_page_cost = 1.1
effective_io_concurrency = 200
seq_page_cost = 1
cpu_tuple_cost = 0.01
cpu_index_tuple_cost = 0.005
cpu_operator_cost = 0.0025

# Checkpoints
checkpoint_timeout = 900s
checkpoint_completion_target = 0.9
checkpoint_flush_after = 256kB
checkpoint_warning = 30s
max_wal_size = 4GB
min_wal_size = 1GB

# Background Writer
bgwriter_delay = 200ms
bgwriter_lru_maxpages = 100
bgwriter_lru_multiplier = 2.0
bgwriter_flush_after = 512kB

# Autovacuum
autovacuum = on
autovacuum_max_workers = 6
autovacuum_naptime = 1min
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_threshold = 50
autovacuum_analyze_scale_factor = 0.05
autovacuum_freeze_max_age = 200000000
autovacuum_multixact_freeze_max_age = 400000000
autovacuum_vacuum_cost_delay = 2ms
autovacuum_vacuum_cost_limit = 400

# Logging
logging_collector = on
log_destination = 'stderr'
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_file_mode = 0640
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_temp_files = 0
log_autovacuum_min_duration = 0
log_error_verbosity = default
log_line_prefix = '[%t] %u@%d %p %r '
log_statement = 'ddl'

# Statistics
track_activities = on
track_counts = on
track_functions = pl
track_io_timing = on
stats_temp_directory = '/tmp/pg_stat_tmp'
shared_preload_libraries = 'timescaledb,pg_stat_statements'

# TimescaleDB
timescaledb.max_background_workers = 8
timescaledb.last_updated = '2023-08-01'

# Lock Management
deadlock_timeout = 1s
max_locks_per_transaction = 256
max_pred_locks_per_transaction = 64

# Memory
temp_buffers = 32MB
max_prepared_transactions = 100
huge_pages = try

# Networking
tcp_keepalives_idle = 600
tcp_keepalives_interval = 30
tcp_keepalives_count = 3
```

### Deployment Scripts

#### scripts/prod-deploy.sh
```bash
#!/bin/bash
# Production deployment script for PATRIOT trading system

set -euo pipefail

# Configuration
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT="${1:-production}"
VERSION="${2:-latest}"
STACK_NAME="patriot-${ENVIRONMENT}"

cd "$PROJECT_ROOT"

echo "🚀 Deploying PATRIOT Trading System to ${ENVIRONMENT}"
echo "📦 Version: ${VERSION}"
echo "🏗️ Stack: ${STACK_NAME}"

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
    echo "❌ Invalid environment. Use 'staging' or 'production'"
    exit 1
fi

# Check if running on swarm manager
if ! docker info --format '{{.Swarm.LocalNodeState}}' | grep -q active; then
    echo "❌ Docker Swarm must be active on manager node"
    exit 1
fi

# Pre-deployment validation
echo "🔍 Running pre-deployment validation..."

# Check required secrets
required_secrets=(
    "jwt_secret"
    "encryption_key"
    "postgres_password"
    "redis_password"
    "ssl_cert"
    "ssl_key"
)

for secret in "${required_secrets[@]}"; do
    if ! docker secret ls --format "{{.Name}}" | grep -q "^${secret}$"; then
        echo "❌ Missing required secret: ${secret}"
        exit 1
    fi
done

# Check required configs
required_configs=(
    "kong_config"
    "prometheus_config"
    "nginx_config"
)

for config in "${required_configs[@]}"; do
    if ! docker config ls --format "{{.Name}}" | grep -q "^${config}$"; then
        echo "❌ Missing required config: ${config}"
        exit 1
    fi
done

# Validate node labels for placement constraints
echo "🏷️ Validating node labels..."
postgres_primary_nodes=$(docker node ls --filter "label=postgres-primary=true" --format "{{.Hostname}}" | wc -l)
postgres_replica_nodes=$(docker node ls --filter "label=postgres-replica=true" --format "{{.Hostname}}" | wc -l)

if [[ $postgres_primary_nodes -lt 1 ]]; then
    echo "❌ No nodes labeled for postgres-primary"
    exit 1
fi

if [[ $postgres_replica_nodes -lt 1 ]]; then
    echo "❌ No nodes labeled for postgres-replica"
    exit 1
fi

# Check data directories exist
required_dirs=(
    "/data/postgres-primary"
    "/data/postgres-replica"
    "/data/backups"
    "/logs"
)

for dir in "${required_dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        echo "❌ Required directory missing: $dir"
        exit 1
    fi
done

echo "✅ Pre-deployment validation passed"

# Build and push images
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "🏗️ Building production images..."
    
    services=(
        "user-command-service"
        "user-query-service"
        "order-command-service"
        "portfolio-query-service"
        "trading-engine"
        "risk-engine"
        "order-lifecycle-service"
        "market-data-service"
    )
    
    for service in "${services[@]}"; do
        echo "Building ${service}:${VERSION}..."
        docker build \
            -t "patriot/${service}:${VERSION}" \
            -t "patriot/${service}:latest" \
            -f "services/${service}/Dockerfile.prod" \
            "services/${service}"
        
        # Push to registry (if configured)
        if [[ -n "${DOCKER_REGISTRY:-}" ]]; then
            docker tag "patriot/${service}:${VERSION}" "${DOCKER_REGISTRY}/patriot/${service}:${VERSION}"
            docker push "${DOCKER_REGISTRY}/patriot/${service}:${VERSION}"
        fi
    done
fi

# Deploy infrastructure first
echo "🏗️ Deploying infrastructure services..."

# Create overlay networks if they don't exist
networks=("patriot-internal" "patriot-external" "monitoring")
for network in "${networks[@]}"; do
    if ! docker network ls --format "{{.Name}}" | grep -q "^${network}$"; then
        echo "Creating network: ${network}"
        case $network in
            "patriot-internal")
                docker network create --driver overlay --encrypted "${network}"
                ;;
            "monitoring")
                docker network create --driver overlay --encrypted "${network}"
                ;;
            *)
                docker network create --driver overlay "${network}"
                ;;
        esac
    fi
done

# Deploy database cluster first
echo "🗄️ Deploying database cluster..."
docker stack deploy \
    --compose-file docker-compose.${ENVIRONMENT}.yml \
    --with-registry-auth \
    --prune \
    ${STACK_NAME}-db

# Wait for database to be ready
echo "⏳ Waiting for database cluster to be ready..."
timeout 300 bash -c '
    until docker service ps '${STACK_NAME}'-db_postgres-primary --format "{{.CurrentState}}" | grep -q "Running"; do
        echo "Waiting for postgres-primary..."
        sleep 10
    done
'

# Verify database connectivity
echo "🔌 Verifying database connectivity..."
max_attempts=30
attempt=0

while [[ $attempt -lt $max_attempts ]]; do
    if docker exec -it $(docker ps -q -f "name=${STACK_NAME}-db_postgres-primary") \
        pg_isready -U patriot -d patriot_${ENVIRONMENT} >/dev/null 2>&1; then
        echo "✅ Database is ready"
        break
    fi
    
    ((attempt++))
    echo "Database not ready, attempt $attempt/$max_attempts..."
    sleep 10
done

if [[ $attempt -eq $max_attempts ]]; then
    echo "❌ Database failed to become ready"
    exit 1
fi

# Deploy Redis cluster
echo "🔴 Deploying Redis cluster..."
docker stack deploy \
    --compose-file docker-compose.${ENVIRONMENT}.yml \
    --with-registry-auth \
    ${STACK_NAME}-redis

# Wait for Redis cluster
echo "⏳ Waiting for Redis cluster..."
timeout 180 bash -c '
    until docker service ps '${STACK_NAME}'-redis_redis-cluster --format "{{.CurrentState}}" | grep -q "Running"; do
        echo "Waiting for redis-cluster..."
        sleep 5
    done
'

# Deploy Kafka cluster
echo "📨 Deploying Kafka cluster..."
docker stack deploy \
    --compose-file docker-compose.${ENVIRONMENT}.yml \
    --with-registry-auth \
    ${STACK_NAME}-kafka

# Wait for Kafka cluster
echo "⏳ Waiting for Kafka cluster..."
timeout 240 bash -c '
    until docker service ps '${STACK_NAME}'-kafka_kafka --format "{{.CurrentState}}" | grep -q "Running"; do
        echo "Waiting for kafka..."
        sleep 10
    done
'

# Deploy application services
echo "🚀 Deploying application services..."
export VERSION="${VERSION}"

docker stack deploy \
    --compose-file docker-compose.${ENVIRONMENT}.yml \
    --with-registry-auth \
    --prune \
    ${STACK_NAME}

# Wait for services to be ready
echo "⏳ Waiting for application services..."
services=(
    "user-command-service"
    "user-query-service"
    "order-command-service"
    "portfolio-query-service"
    "trading-engine"
    "risk-engine"
)

for service in "${services[@]}"; do
    echo "Waiting for ${service}..."
    timeout 180 bash -c "
        until docker service ps ${STACK_NAME}_${service} --format '{{.CurrentState}}' | grep -q 'Running'; do
            sleep 10
        done
    "
done

# Verify API Gateway
echo "🦍 Verifying API Gateway..."
timeout 120 bash -c '
    until curl -f http://localhost/health >/dev/null 2>&1; do
        echo "Waiting for API Gateway..."
        sleep 5
    done
'

# Run database migrations
echo "🗄️ Running database migrations..."
migration_container=$(docker run -d \
    --network ${STACK_NAME}_patriot-internal \
    -e DATABASE_URL=postgresql://patriot:${POSTGRES_PASSWORD}@postgres-primary:5432/patriot_${ENVIRONMENT} \
    patriot/migration-runner:${VERSION} \
    npm run migrate:up
)

docker logs -f $migration_container
migration_exit_code=$(docker wait $migration_container)

if [[ $migration_exit_code -ne 0 ]]; then
    echo "❌ Database migrations failed"
    exit 1
fi

echo "✅ Database migrations completed successfully"

# Create Kafka topics
echo "📨 Creating Kafka topics..."
topics=(
    "user.events:12:3"
    "order.events:24:3"
    "portfolio.events:12:3"
    "market.data:24:3"
    "risk.events:6:3"
    "system.events:3:3"
)

kafka_container=$(docker ps -q -f "name=${STACK_NAME}_kafka" | head -1)

for topic_config in "${topics[@]}"; do
    IFS=':' read -r topic partitions replication <<< "$topic_config"
    
    echo "Creating topic: $topic (partitions: $partitions, replication: $replication)"
    docker exec $kafka_container kafka-topics --create \
        --bootstrap-server localhost:9092 \
        --topic "$topic" \
        --partitions "$partitions" \
        --replication-factor "$replication" \
        --if-not-exists \
        --config retention.ms=604800000 \
        --config compression.type=snappy
done

# Health check all services
echo "🏥 Running comprehensive health checks..."

# API endpoints
api_endpoints=(
    "http://localhost/api/v1/users/health:User Service"
    "http://localhost/api/v1/orders/health:Order Service"
    "http://localhost/api/v1/portfolio/health:Portfolio Service"
)

for endpoint_config in "${api_endpoints[@]}"; do
    IFS=':' read -r endpoint name <<< "$endpoint_config"
    
    if curl -f "$endpoint" >/dev/null 2>&1; then
        echo "✅ $name: healthy"
    else
        echo "❌ $name: unhealthy"
    fi
done

# Database health
if docker exec $(docker ps -q -f "name=${STACK_NAME}_postgres-primary") \
    psql -U patriot -d patriot_${ENVIRONMENT} -c "SELECT 1" >/dev/null 2>&1; then
    echo "✅ PostgreSQL: healthy"
else
    echo "❌ PostgreSQL: unhealthy"
fi

# Redis health
if docker exec $(docker ps -q -f "name=${STACK_NAME}_redis-cluster" | head -1) \
    redis-cli ping | grep -q PONG; then
    echo "✅ Redis: healthy"
else
    echo "❌ Redis: unhealthy"
fi

# Kafka health  
if docker exec $(docker ps -q -f "name=${STACK_NAME}_kafka" | head -1) \
    kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null 2>&1; then
    echo "✅ Kafka: healthy"
else
    echo "❌ Kafka: unhealthy"
fi

# Service scaling verification
echo "📊 Verifying service scaling..."
docker service ls --filter "name=${STACK_NAME}" --format "table {{.Name}}\t{{.Replicas}}\t{{.Image}}"

# Monitor deployment status
echo "📈 Monitoring deployment status..."
docker stack ps ${STACK_NAME} --no-trunc --format "table {{.Name}}\t{{.CurrentState}}\t{{.Error}}"

# Setup monitoring alerts
echo "🚨 Setting up monitoring alerts..."
if command -v prometheus >/dev/null 2>&1; then
    # Reload Prometheus configuration
    curl -X POST http://localhost:9090/-/reload 2>/dev/null || true
fi

# Final deployment verification
echo "🔍 Running final deployment verification..."

# Check all services are running
failed_services=()
for service in $(docker service ls --filter "name=${STACK_NAME}" --format "{{.Name}}"); do
    replicas=$(docker service ls --filter "name=$service" --format "{{.Replicas}}")
    if [[ ! "$replicas" =~ ^[1-9][0-9]*/[1-9][0-9]*$ ]] || [[ "$replicas" =~ 0/ ]]; then
        failed_services+=("$service")
    fi
done

if [[ ${#failed_services[@]} -gt 0 ]]; then
    echo "❌ The following services failed to deploy properly:"
    printf ' - %s\n' "${failed_services[@]}"
    echo "Check service logs: docker service logs <service_name>"
    exit 1
fi

# Log deployment success
echo "✅ PATRIOT Trading System deployed successfully!"
echo ""
echo "🌐 Environment: $ENVIRONMENT"
echo "📦 Version: $VERSION"
echo "🏗️ Stack: $STACK_NAME"
echo "⏰ Deployed at: $(date)"
echo ""
echo "📋 Service Status:"
docker service ls --filter "name=${STACK_NAME}" --format "table {{.Name}}\t{{.Replicas}}\t{{.Ports}}"
echo ""
echo "🔗 Access Points:"
echo "  API Gateway: https://api.patriot-trading.com"
echo "  Admin Panel: https://admin.patriot-trading.com"
echo "  Monitoring: https://monitoring.patriot-trading.com"
echo ""
echo "📊 Monitoring Commands:"
echo "  View logs: docker service logs -f ${STACK_NAME}_<service_name>"
echo "  Scale service: docker service scale ${STACK_NAME}_<service_name>=<replicas>"
echo "  Update service: docker service update ${STACK_NAME}_<service_name>"
echo "  Stack status: docker stack ps ${STACK_NAME}"
```

### Infrastructure Management

#### scripts/manage-cluster.sh
```bash
#!/bin/bash
# Cluster management script for PATRIOT trading system

set -euo pipefail

OPERATION="${1:-status}"
ENVIRONMENT="${2:-production}"
SERVICE="${3:-}"

echo "🔧 PATRIOT Cluster Management"
echo "Operation: $OPERATION"
echo "Environment: $ENVIRONMENT"

case "$OPERATION" in
    "status")
        echo "📊 Cluster Status"
        echo "=================="
        
        echo "🏗️ Stack Status:"
        docker stack ls
        echo ""
        
        echo "🔧 Service Status:"
        docker service ls --filter "name=patriot-${ENVIRONMENT}"
        echo ""
        
        echo "🖥️ Node Status:"
        docker node ls
        echo ""
        
        echo "📈 Resource Usage:"
        docker system df
        ;;
        
    "scale")
        if [[ -z "$SERVICE" ]]; then
            echo "❌ Service name required for scaling"
            echo "Usage: $0 scale <environment> <service> <replicas>"
            exit 1
        fi
        
        REPLICAS="${4:-}"
        if [[ -z "$REPLICAS" ]]; then
            echo "❌ Replica count required"
            exit 1
        fi
        
        echo "📈 Scaling ${SERVICE} to ${REPLICAS} replicas..."
        docker service scale "patriot-${ENVIRONMENT}_${SERVICE}=${REPLICAS}"
        ;;
        
    "update")
        if [[ -z "$SERVICE" ]]; then
            echo "❌ Service name required for update"
            exit 1
        fi
        
        VERSION="${4:-latest}"
        
        echo "🔄 Updating ${SERVICE} to version ${VERSION}..."
        docker service update \
            --image "patriot/${SERVICE}:${VERSION}" \
            --update-parallelism 1 \
            --update-delay 30s \
            --update-failure-action rollback \
            "patriot-${ENVIRONMENT}_${SERVICE}"
        ;;
        
    "rollback")
        if [[ -z "$SERVICE" ]]; then
            echo "❌ Service name required for rollback"
            exit 1
        fi
        
        echo "⏪ Rolling back ${SERVICE}..."
        docker service rollback "patriot-${ENVIRONMENT}_${SERVICE}"
        ;;
        
    "logs")
        if [[ -z "$SERVICE" ]]; then
            echo "❌ Service name required for logs"
            exit 1
        fi
        
        LINES="${4:-100}"
        
        echo "📋 Last ${LINES} log entries for ${SERVICE}:"
        docker service logs \
            --tail "$LINES" \
            --follow \
            "patriot-${ENVIRONMENT}_${SERVICE}"
        ;;
        
    "backup")
        echo "💾 Creating system backup..."
        
        # Database backup
        echo "Backing up PostgreSQL..."
        backup_name="patriot-${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
        
        docker exec -t $(docker ps -q -f "name=patriot-${ENVIRONMENT}_postgres-primary") \
            pg_dumpall -U patriot > "/backups/db-${backup_name}.sql"
        
        # Configuration backup
        echo "Backing up configurations..."
        tar -czf "/backups/config-${backup_name}.tar.gz" \
            config/ \
            docker-compose.${ENVIRONMENT}.yml
        
        echo "✅ Backup completed: ${backup_name}"
        ;;
        
    "restore")
        BACKUP_NAME="${4:-}"
        if [[ -z "$BACKUP_NAME" ]]; then
            echo "❌ Backup name required"
            exit 1
        fi
        
        echo "⚠️ This will restore the system from backup: $BACKUP_NAME"
        echo "⚠️ This operation cannot be undone!"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Restore cancelled"
            exit 0
        fi
        
        echo "🔄 Restoring from backup..."
        
        # Stop services
        docker stack rm "patriot-${ENVIRONMENT}"
        
        # Restore database
        docker exec -i $(docker ps -q -f "name=patriot-${ENVIRONMENT}_postgres-primary") \
            psql -U postgres < "/backups/db-${BACKUP_NAME}.sql"
        
        echo "✅ Restore completed"
        ;;
        
    "maintenance")
        MODE="${4:-on}"
        
        if [[ "$MODE" == "on" ]]; then
            echo "🚧 Enabling maintenance mode..."
            
            # Update Kong configuration to show maintenance page
            docker config create kong_maintenance_config config/kong/maintenance.yml
            docker service update \
                --config-rm kong_config \
                --config-add source=kong_maintenance_config,target=/etc/kong/kong.yml \
                "patriot-${ENVIRONMENT}_kong"
                
        else
            echo "✅ Disabling maintenance mode..."
            
            # Restore normal Kong configuration
            docker service update \
                --config-rm kong_maintenance_config \
                --config-add source=kong_config,target=/etc/kong/kong.yml \
                "patriot-${ENVIRONMENT}_kong"
        fi
        ;;
        
    "health")
        echo "🏥 Comprehensive Health Check"
        echo "============================="
        
        # Service health
        services=(
            "patriot-${ENVIRONMENT}_kong"
            "patriot-${ENVIRONMENT}_user-command-service"
            "patriot-${ENVIRONMENT}_order-command-service"
            "patriot-${ENVIRONMENT}_postgres-primary"
            "patriot-${ENVIRONMENT}_redis-cluster"
            "patriot-${ENVIRONMENT}_kafka"
        )
        
        for service in "${services[@]}"; do
            replicas=$(docker service ps "$service" --filter "desired-state=running" --format "{{.CurrentState}}" | grep -c "Running" || echo "0")
            desired=$(docker service ls --filter "name=$service" --format "{{.Replicas}}" | cut -d'/' -f2)
            
            if [[ "$replicas" == "$desired" ]]; then
                echo "✅ $service: $replicas/$desired replicas running"
            else
                echo "❌ $service: $replicas/$desired replicas running"
            fi
        done
        
        # External health checks
        echo ""
        echo "🌐 External Health Checks:"
        
        endpoints=(
            "https://api.patriot-trading.com/health:API Gateway"
            "https://monitoring.patriot-trading.com:Monitoring"
        )
        
        for endpoint_config in "${endpoints[@]}"; do
            IFS=':' read -r endpoint name <<< "$endpoint_config"
            
            if curl -f -s -m 10 "$endpoint" >/dev/null; then
                echo "✅ $name: accessible"
            else
                echo "❌ $name: not accessible"
            fi
        done
        ;;
        
    "clean")
        echo "🧹 Cleaning up unused resources..."
        
        # Remove unused containers
        docker container prune -f
        
        # Remove unused images
        docker image prune -a -f
        
        # Remove unused volumes
        docker volume prune -f
        
        # Remove unused networks
        docker network prune -f
        
        # Remove build cache
        docker builder prune -a -f
        
        echo "✅ Cleanup completed"
        ;;
        
    "monitor")
        echo "📊 Live monitoring (Ctrl+C to exit)..."
        
        while true; do
            clear
            echo "PATRIOT Trading System - Live Monitor"
            echo "======================================"
            echo "Time: $(date)"
            echo ""
            
            # Service status
            docker service ls --filter "name=patriot-${ENVIRONMENT}" --format "table {{.Name}}\t{{.Replicas}}"
            echo ""
            
            # Resource usage
            echo "📈 System Resources:"
            docker system df
            echo ""
            
            # Recent logs (errors only)
            echo "🚨 Recent Errors:"
            docker service logs --tail 5 --since 1m "patriot-${ENVIRONMENT}_user-command-service" 2>&1 | grep -i error || echo "No recent errors"
            
            sleep 30
        done
        ;;
        
    *)
        echo "❌ Unknown operation: $OPERATION"
        echo ""
        echo "Available operations:"
        echo "  status     - Show cluster status"
        echo "  scale      - Scale a service"
        echo "  update     - Update a service"
        echo "  rollback   - Rollback a service"
        echo "  logs       - View service logs"
        echo "  backup     - Create system backup"
        echo "  restore    - Restore from backup"
        echo "  maintenance - Enable/disable maintenance mode"
        echo "  health     - Comprehensive health check"
        echo "  clean      - Clean unused resources"
        echo "  monitor    - Live monitoring"
        exit 1
        ;;
esac
```

### Monitoring and Alerting Configuration

#### config/prometheus/prod/alert-rules.yml
```yaml
groups:
  - name: patriot-trading-alerts
    rules:
      # Service Health Alerts
      - alert: ServiceDown
        expr: up == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Service {{ $labels.instance }} is down"
          description: "{{ $labels.instance }} has been down for more than 5 minutes"
          
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate on {{ $labels.instance }}"
          description: "Error rate is {{ $value }} errors per second"
          
      # Database Alerts
      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL is down"
          description: "PostgreSQL has been down for more than 1 minute"
          
      - alert: PostgreSQLReplicationLag
        expr: pg_replication_lag > 60
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL replication lag is high"
          description: "Replication lag is {{ $value }} seconds"
          
      - alert: PostgreSQLConnectionsHigh
        expr: pg_stat_database_numbackends / pg_settings_max_connections > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL connections are high"
          description: "{{ $value }}% of connections are in use"
          
      # Redis Alerts
      - alert: RedisDown
        expr: redis_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Redis is down"
          description: "Redis has been down for more than 1 minute"
          
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis memory usage is high"
          description: "Redis is using {{ $value }}% of available memory"
          
      # Kafka Alerts
      - alert: KafkaDown
        expr: kafka_server_replicamanager_leadercount == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Kafka broker is down"
          description: "Kafka broker has no leaders"
          
      - alert: KafkaConsumerLag
        expr: kafka_consumer_lag_sum > 1000
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Kafka consumer lag is high"
          description: "Consumer lag is {{ $value }} messages"
          
      # Trading Specific Alerts
      - alert: OrderProcessingDelayed
        expr: histogram_quantile(0.95, rate(order_processing_duration_seconds_bucket[5m])) > 5
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "Order processing is delayed"
          description: "95th percentile processing time is {{ $value }} seconds"
          
      - alert: RiskViolation
        expr: risk_violation_total > 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Risk violation detected"
          description: "{{ $value }} risk violations in the last minute"
          
      - alert: ExchangeConnectionDown
        expr: exchange_connection_status == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Exchange connection is down"
          description: "Connection to {{ $labels.exchange }} has been down for 2 minutes"
          
      # System Resource Alerts
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[2m])) * 100) > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"
          description: "CPU usage is {{ $value }}%"
          
      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage on {{ $labels.instance }}"
          description: "Memory usage is {{ $value }}%"
          
      - alert: DiskSpaceLow
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Disk space low on {{ $labels.instance }}"
          description: "Available disk space is {{ $value }}%"
```

---

> **Deployment Status Summary:**
> - ✅ Development environment with full Docker Compose setup
> - ✅ Staging environment with clustering and monitoring
> - ✅ Production environment with high availability and security
> - ✅ Automated deployment scripts with validation
> - ✅ Cluster management and maintenance tools
> - ✅ Comprehensive monitoring and alerting

> **Key Features:**
> 1. **Multi-Environment Support**: Development, staging, and production configurations
> 2. **High Availability**: Database replication, Redis clustering, service scaling
> 3. **Security**: SSL/TLS, secrets management, network isolation
> 4. **Monitoring**: Prometheus, Grafana, ELK stack integration
> 5. **Automation**: Deployment scripts, health checks, maintenance tools
> 6. **Scalability**: Docker Swarm orchestration, horizontal scaling

> **Next Steps:**
> 1. Set up CI/CD pipelines for automated deployments
> 2. Configure external monitoring and alerting (PagerDuty, Slack)
> 3. Implement blue-green deployment strategy
> 4. Set up disaster recovery procedures
> 5. Configure log aggregation and analysis
> 6. Implement automated scaling based on metrics
