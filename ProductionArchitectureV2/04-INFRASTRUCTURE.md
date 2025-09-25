# PATRIOT Trading System - Infrastructure Architecture

## 📋 Document Information

**Document ID**: 04-INFRASTRUCTURE  
**Version**: 2.0  
**Date**: September 2025  
**Authors**: Solution Architecture Team  
**Status**: Draft  

> **Cross-References:**  
> - System Requirements: [01-SYSTEM-REQUIREMENTS.md](01-SYSTEM-REQUIREMENTS.md#NFR-002)  
> - System Architecture: [02-SYSTEM-ARCHITECTURE.md](02-SYSTEM-ARCHITECTURE.md#infrastructure-layer)  
> - Component Specifications: [03-COMPONENT-SPECIFICATIONS.md](03-COMPONENT-SPECIFICATIONS.md)  
> - Deployment Examples: [annexes/ANNEX-C-DEPLOYMENT-EXAMPLES.md](annexes/ANNEX-C-DEPLOYMENT-EXAMPLES.md)

---

## 🏗️ Infrastructure Overview

The PATRIOT trading system infrastructure is designed for **production-grade reliability, scalability, and observability**. The infrastructure follows cloud-native principles with containerized deployments, comprehensive monitoring, and automated operations.

### Infrastructure Principles

#### 1. **High Availability Design**
- Multi-zone deployment with automatic failover
- Database clustering with read replicas
- Load balancing across service instances
- Circuit breaker patterns for external dependencies

#### 2. **Scalability & Performance**
- Horizontal scaling for stateless services
- Vertical scaling for stateful components
- Connection pooling and resource optimization
- Caching strategies for reduced latency

#### 3. **Security & Compliance**
- Network segmentation and firewall controls
- Encrypted data transmission and storage
- Audit logging and compliance monitoring
- Secure secret management

#### 4. **Observability & Operations**
- Comprehensive monitoring and alerting
- Centralized logging with correlation
- Distributed tracing for request flow
- Performance monitoring and optimization

---

## 🐳 Containerization & Deployment Architecture

### Docker & Container Strategy

#### Base Images and Standards
```dockerfile
# Base Python service image
FROM python:3.11-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r patriot && useradd -r -g patriot patriot

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=patriot:patriot . .

# Switch to non-root user
USER patriot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Multi-Stage Build Example
```dockerfile
# services/order-command-service/Dockerfile
FROM python:3.11-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim as runtime

# Copy installed packages
COPY --from=builder /root/.local /home/patriot/.local

# Create application user
RUN groupadd -r patriot && useradd -r -g patriot patriot

# Set up application
WORKDIR /app
COPY --chown=patriot:patriot ./src ./src
COPY --chown=patriot:patriot ./config ./config
COPY --chown=patriot:patriot main.py .

USER patriot

# Make sure scripts in .local are usable
ENV PATH=/home/patriot/.local/bin:$PATH

EXPOSE 8004

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8004/health')"

CMD ["python", "main.py"]
```

### Docker Compose Architecture

#### Development Environment
```yaml
# docker-compose.dev.yml
version: '3.8'

networks:
  patriot-internal:
    driver: bridge
  patriot-external:
    driver: bridge

services:
  # API Gateway
  kong:
    image: kong:3.3
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /config/kong.dev.yml
      KONG_PROXY_LISTEN: "0.0.0.0:8000"
      KONG_ADMIN_LISTEN: "0.0.0.0:8001"
    ports:
      - "8000:8000"  # External API Gateway port
      - "8001:8001"  # Kong Admin API (dev only)
    volumes:
      - ./config/kong:/config
    networks:
      - patriot-external
      - patriot-internal
    depends_on:
      - user-command-service
      - user-query-service

  # Core Services (Command Side)
  user-command-service:
    build:
      context: ./services/user-command-service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://patriot:password@postgres:5432/patriot_db
      - REDIS_URL=redis://redis:6379/0
      - KAFKA_BROKERS=kafka:9092
      - JWT_SECRET=${JWT_SECRET}
      - API_KEY_ENCRYPTION_KEY=${API_KEY_ENCRYPTION_KEY}
    ports:
      - "8101:8001"  # Development port mapping
    networks:
      - patriot-internal
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      kafka:
        condition: service_healthy

  order-command-service:
    build:
      context: ./services/order-command-service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://patriot:password@postgres:5432/patriot_db
      - REDIS_URL=redis://redis:6379/1
      - KAFKA_BROKERS=kafka:9092
      - RISK_ENGINE_URL=http://risk-engine:8006
    ports:
      - "8104:8004"
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka
      - risk-engine

  # Core Services (Query Side)
  user-query-service:
    build:
      context: ./services/user-query-service
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://patriot:password@postgres:5432/patriot_db
      - REDIS_URL=redis://redis:6379/2
      - KAFKA_BROKERS=kafka:9092
    ports:
      - "8102:8002"
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka

  # Domain Services
  trading-engine:
    build:
      context: ./services/trading-engine
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://patriot:password@postgres:5432/patriot_db
      - KAFKA_BROKERS=kafka:9092
      - BINANCE_API_URL=https://fapi.binance.com
      - BYBIT_API_URL=https://api.bybit.com
    networks:
      - patriot-internal
    depends_on:
      - kafka
      - postgres

  risk-engine:
    build:
      context: ./services/risk-engine
      dockerfile: Dockerfile
    environment:
      - DATABASE_URL=postgresql://patriot:password@postgres:5432/patriot_db
      - REDIS_URL=redis://redis:6379/3
      - KAFKA_BROKERS=kafka:9092
    ports:
      - "8106:8006"
    networks:
      - patriot-internal
    depends_on:
      - postgres
      - redis
      - kafka

  # Data Services
  market-data-service:
    build:
      context: ./services/market-data-service
      dockerfile: Dockerfile
    environment:
      - KAFKA_BROKERS=kafka:9092
      - REDIS_URL=redis://redis:6379/4
      - BINANCE_WS_URL=wss://fstream.binance.com/ws
      - BYBIT_WS_URL=wss://stream.bybit.com/v5/public/linear
    networks:
      - patriot-internal
    depends_on:
      - kafka
      - redis

  # Infrastructure Services
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: patriot_db
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD: password
      POSTGRES_INITDB_ARGS: "--encoding=UTF-8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    networks:
      - patriot-internal
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U patriot -d patriot_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - patriot-internal
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_NUM_PARTITIONS: 6
      KAFKA_DEFAULT_REPLICATION_FACTOR: 1
    ports:
      - "9092:9092"
    networks:
      - patriot-internal
    depends_on:
      - zookeeper
    healthcheck:
      test: ["CMD", "kafka-broker-api-versions", "--bootstrap-server", "localhost:9092"]
      interval: 30s
      timeout: 10s
      retries: 5

  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000
    networks:
      - patriot-internal

volumes:
  postgres_data:
  redis_data:
```

#### Production Environment
```yaml
# docker-compose.prod.yml
version: '3.8'

networks:
  patriot-internal:
    driver: overlay
    encrypted: true
  patriot-external:
    driver: overlay
  monitoring:
    driver: overlay

services:
  # API Gateway with SSL termination
  kong:
    image: kong:3.3
    environment:
      KONG_DATABASE: "off"
      KONG_DECLARATIVE_CONFIG: /config/kong.prod.yml
      KONG_PROXY_LISTEN: "0.0.0.0:8000 ssl"
      KONG_ADMIN_LISTEN: "127.0.0.1:8001"
      KONG_SSL_CERT: /certs/patriot.crt
      KONG_SSL_CERT_KEY: /certs/patriot.key
    ports:
      - "443:8000"
    volumes:
      - ./config/kong:/config:ro
      - ./certs:/certs:ro
    networks:
      - patriot-external
      - patriot-internal
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: any
        delay: 5s
        max_attempts: 3

  # Command Services (Scaled)
  user-command-service:
    image: patriot/user-command-service:${VERSION}
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
      - JWT_SECRET=${JWT_SECRET}
      - API_KEY_ENCRYPTION_KEY=${API_KEY_ENCRYPTION_KEY}
      - LOG_LEVEL=INFO
      - METRICS_ENABLED=true
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: any

  order-command-service:
    image: patriot/order-command-service:${VERSION}
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
      - RISK_ENGINE_URL=http://risk-engine:8006
      - LOG_LEVEL=INFO
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 4  # Higher replica count for critical service
      resources:
        limits:
          memory: 1G
          cpus: '1'
        reservations:
          memory: 512M
          cpus: '0.5'

  # Query Services (Scaled for Read Load)
  user-query-service:
    image: patriot/user-query-service:${VERSION}
    environment:
      - DATABASE_URL=${DATABASE_READONLY_URL}
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 4
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  # Domain Services (Stateful, Controlled Scaling)
  trading-engine:
    image: patriot/trading-engine:${VERSION}
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
      - BINANCE_API_URL=https://fapi.binance.com
      - BYBIT_API_URL=https://api.bybit.com
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 2  # Limited scaling for state consistency
      resources:
        limits:
          memory: 2G
          cpus: '1'
        reservations:
          memory: 1G
          cpus: '0.5'

  risk-engine:
    image: patriot/risk-engine:${VERSION}
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - KAFKA_BROKERS=${KAFKA_BROKERS}
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '1.5'

  # Market Data Service (High Availability)
  market-data-service:
    image: patriot/market-data-service:${VERSION}
    environment:
      - KAFKA_BROKERS=${KAFKA_BROKERS}
      - REDIS_URL=${REDIS_URL}
      - BINANCE_WS_URL=wss://fstream.binance.com/ws
      - BYBIT_WS_URL=wss://stream.bybit.com/v5/public/linear
    networks:
      - patriot-internal
      - monitoring
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 1G
          cpus: '1'

# External dependencies managed separately in production
# - PostgreSQL cluster with read replicas
# - Redis cluster with sentinel
# - Kafka cluster with Zookeeper ensemble
```

---

## 📊 Monitoring Architecture

### Comprehensive Observability Stack

#### Prometheus + Grafana Monitoring

**Monitoring Architecture Diagram**:
```mermaid
graph TB
    subgraph "PATRIOT Services"
        UC[User Command Service]
        OC[Order Command Service]
        TE[Trading Engine]
        RE[Risk Engine]
        MDS[Market Data Service]
    end
    
    subgraph "Infrastructure"
        PG[(PostgreSQL Cluster)]
        REDIS[(Redis Cluster)]
        KAFKA[(Kafka Cluster)]
    end
    
    subgraph "Monitoring Stack"
        PROM[Prometheus Server]
        GRAF[Grafana Dashboards]
        AM[Alert Manager]
    end
    
    subgraph "Exporters"
        PE[Postgres Exporter]
        RE_EX[Redis Exporter]
        KE[Kafka Exporter]
        NE[Node Exporter]
    end
    
    subgraph "Log Management"
        ELK[ELK Stack]
        LOKI[Loki + Promtail]
    end
    
    subgraph "Tracing"
        JAEGER[Jaeger]
    end
    
    %% Service metrics
    UC --> PROM
    OC --> PROM
    TE --> PROM
    RE --> PROM
    MDS --> PROM
    
    %% Infrastructure exporters
    PE --> PROM
    RE_EX --> PROM
    KE --> PROM
    NE --> PROM
    
    %% Monitoring flow
    PROM --> GRAF
    PROM --> AM
    
    %% Logging flow
    UC --> ELK
    OC --> ELK
    TE --> LOKI
    
    %% Tracing flow
    UC --> JAEGER
    OC --> JAEGER
```

#### Custom Business Metrics

**PATRIOT-Specific Metrics Collection**:
```python
# services/common/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry
import time
import functools
from typing import Dict, Any

class PatriotMetrics:
    """PATRIOT Trading System specific metrics"""
    
    def __init__(self, registry: CollectorRegistry = None):
        self.registry = registry or CollectorRegistry()
        
        # WebSocket Connection Metrics
        self.websocket_connections = Gauge(
            'patriot_websocket_connections_total',
            'Total WebSocket connections',
            ['exchange', 'connection_type', 'status'],
            registry=self.registry
        )
        
        # Order Lifecycle Metrics
        self.tracked_orders = Gauge(
            'patriot_tracked_orders_total',
            'Total orders being tracked by Order Lifecycle Service',
            ['status', 'exchange', 'strategy_id'],
            registry=self.registry
        )
        
        self.order_processing_time = Histogram(
            'patriot_order_processing_seconds',
            'Time spent processing orders',
            ['operation', 'exchange', 'result'],
            registry=self.registry
        )
        
        # Risk Management Metrics
        self.risk_violations = Counter(
            'patriot_risk_violations_total',
            'Total risk violations detected',
            ['user_id', 'violation_type', 'severity'],
            registry=self.registry
        )
        
        self.portfolio_risk_score = Gauge(
            'patriot_portfolio_risk_score',
            'Current portfolio risk score',
            ['user_id', 'account_id'],
            registry=self.registry
        )
        
        # Strategy Performance Metrics
        self.strategy_signals = Counter(
            'patriot_strategy_signals_total',
            'Total trading signals generated',
            ['strategy_id', 'symbol', 'action'],
            registry=self.registry
        )
        
        self.strategy_pnl = Gauge(
            'patriot_strategy_pnl_total',
            'Total PnL for strategy',
            ['strategy_id', 'user_id'],
            registry=self.registry
        )
        
        # Redis Cache Metrics
        self.redis_keys = Gauge(
            'patriot_redis_keys_total',
            'Total Redis keys by pattern',
            ['pattern', 'database'],
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'patriot_cache_hit_rate',
            'Cache hit rate percentage',
            ['cache_type'],
            registry=self.registry
        )
        
        # Database Metrics
        self.database_connections = Gauge(
            'patriot_database_connections_active',
            'Active database connections',
            ['database', 'pool_name'],
            registry=self.registry
        )
        
        self.query_duration = Histogram(
            'patriot_database_query_seconds',
            'Database query execution time',
            ['query_type', 'table'],
            registry=self.registry
        )

    def track_operation_time(self, operation: str, exchange: str = "unknown"):
        """Decorator to automatically track operation timing"""
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                result = "success"
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    result = "error"
                    raise
                finally:
                    self.order_processing_time.labels(
                        operation=operation,
                        exchange=exchange,
                        result=result
                    ).observe(time.time() - start_time)
            return wrapper
        return decorator

# Global metrics instance
patriot_metrics = PatriotMetrics()

# Usage examples in services
class OrderLifecycleService:
    """Order Lifecycle Service with metrics integration"""
    
    def __init__(self):
        self.tracked_orders: Dict[str, Any] = {}
        
    @patriot_metrics.track_operation_time("start_tracking")
    async def start_tracking_order(self, order_data: dict):
        """Start tracking order with metrics"""
        order_id = order_data["order_id"]
        self.tracked_orders[order_id] = order_data
        
        # Update tracked orders metric
        patriot_metrics.tracked_orders.labels(
            status=order_data["status"],
            exchange=order_data["exchange"],
            strategy_id=order_data.get("strategy_id", "none")
        ).inc()
    
    async def stop_tracking_order(self, order_id: str):
        """Stop tracking order with metrics update"""
        if order_id in self.tracked_orders:
            order_data = self.tracked_orders.pop(order_id)
            
            # Decrement tracked orders metric
            patriot_metrics.tracked_orders.labels(
                status=order_data["status"],
                exchange=order_data["exchange"],
                strategy_id=order_data.get("strategy_id", "none")
            ).dec()

class RiskEngine:
    """Risk Engine with metrics integration"""
    
    async def check_risk_violation(self, user_id: str, risk_data: dict):
        """Check risk with violation tracking"""
        violations = await self.analyze_risk(risk_data)
        
        for violation in violations:
            # Track risk violation
            patriot_metrics.risk_violations.labels(
                user_id=user_id,
                violation_type=violation["type"],
                severity=violation["severity"]
            ).inc()
            
            # Update risk score
            patriot_metrics.portfolio_risk_score.labels(
                user_id=user_id,
                account_id=violation["account_id"]
            ).set(violation["risk_score"])
```

#### Grafana Dashboard Configuration

**Core System Dashboard**:
```json
{
  "dashboard": {
    "title": "PATRIOT Trading System - Core Metrics",
    "tags": ["patriot", "trading", "production"],
    "refresh": "30s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "title": "WebSocket Connections Health",
        "type": "stat",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "targets": [
          {
            "expr": "sum(patriot_websocket_connections_total{status=\"connected\"}) by (exchange, connection_type)",
            "legendFormat": "{{exchange}} - {{connection_type}}",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {"mode": "value"},
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 1},
                {"color": "green", "value": 2}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Order Processing Performance",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(patriot_order_processing_seconds_bucket[5m]))",
            "legendFormat": "95th Percentile",
            "refId": "A"
          },
          {
            "expr": "histogram_quantile(0.50, rate(patriot_order_processing_seconds_bucket[5m]))",
            "legendFormat": "50th Percentile", 
            "refId": "B"
          }
        ],
        "yAxes": [
          {"label": "Seconds", "min": 0}
        ]
      },
      {
        "id": 3,
        "title": "Risk Violations (Last 24h)",
        "type": "pie",
        "gridPos": {"h": 8, "w": 8, "x": 0, "y": 8},
        "targets": [
          {
            "expr": "increase(patriot_risk_violations_total[24h])",
            "legendFormat": "{{violation_type}} - {{severity}}",
            "refId": "A"
          }
        ]
      },
      {
        "id": 4,
        "title": "Active Orders by Exchange",
        "type": "bar",
        "gridPos": {"h": 8, "w": 8, "x": 8, "y": 8},
        "targets": [
          {
            "expr": "sum(patriot_tracked_orders_total{status!=\"completed\"}) by (exchange)",
            "legendFormat": "{{exchange}}",
            "refId": "A"
          }
        ]
      },
      {
        "id": 5,
        "title": "Cache Performance",
        "type": "stat",
        "gridPos": {"h": 8, "w": 8, "x": 16, "y": 8},
        "targets": [
          {
            "expr": "patriot_cache_hit_rate",
            "legendFormat": "{{cache_type}}",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 70},
                {"color": "green", "value": 85}
              ]
            }
          }
        }
      }
    ],
    "templating": {
      "list": [
        {
          "name": "exchange",
          "type": "query",
          "query": "label_values(patriot_websocket_connections_total, exchange)",
          "refresh": 1
        }
      ]
    }
  }
}
```

### Alert Management Configuration

**Critical Alerts**:
```yaml
# alertmanager/alerts.yml
groups:
  - name: patriot_critical
    rules:
      - alert: WebSocketConnectionDown
        expr: patriot_websocket_connections_total{status="connected"} == 0
        for: 1m
        labels:
          severity: critical
          service: market-data
        annotations:
          summary: "WebSocket connection down for {{ $labels.exchange }}"
          description: "{{ $labels.connection_type }} connection to {{ $labels.exchange }} has been down for more than 1 minute"
          
      - alert: HighOrderProcessingTime
        expr: histogram_quantile(0.95, rate(patriot_order_processing_seconds_bucket[5m])) > 1
        for: 2m
        labels:
          severity: warning
          service: order-processing
        annotations:
          summary: "High order processing time detected"
          description: "95th percentile order processing time is {{ $value }}s"
          
      - alert: RiskViolationSpike
        expr: increase(patriot_risk_violations_total{severity="critical"}[5m]) > 5
        for: 0m
        labels:
          severity: critical
          service: risk-management
        annotations:
          summary: "Critical risk violations spike"
          description: "{{ $value }} critical risk violations in the last 5 minutes"
          
      - alert: DatabaseConnectionExhaustion
        expr: patriot_database_connections_active / patriot_database_connections_max > 0.9
        for: 30s
        labels:
          severity: warning
          service: database
        annotations:
          summary: "Database connection pool near exhaustion"
          description: "{{ $labels.database }} connection pool is {{ $value | humanizePercentage }} full"

  - name: patriot_performance
    rules:
      - alert: LowCacheHitRate
        expr: patriot_cache_hit_rate{cache_type="portfolio"} < 0.8
        for: 5m
        labels:
          severity: warning
          service: caching
        annotations:
          summary: "Low cache hit rate for {{ $labels.cache_type }}"
          description: "Cache hit rate is {{ $value | humanizePercentage }}, below 80% threshold"
          
      - alert: HighStrategySignalRate
        expr: rate(patriot_strategy_signals_total[1m]) > 100
        for: 2m
        labels:
          severity: warning
          service: strategy-engine
        annotations:
          summary: "Unusually high strategy signal rate"
          description: "Strategy {{ $labels.strategy_id }} generating {{ $value }} signals per minute"
```

---

## 📋 Centralized Logging Architecture

### ELK Stack Integration

#### Elasticsearch Configuration
```yaml
# elasticsearch/elasticsearch.yml
cluster.name: "patriot-logging"
node.name: "patriot-es-01"
network.host: 0.0.0.0
http.port: 9200
discovery.type: single-node

# Index lifecycle management
xpack.ilm.enabled: true
xpack.monitoring.collection.enabled: true

# Security settings
xpack.security.enabled: true
xpack.security.transport.ssl.enabled: true
xpack.security.http.ssl.enabled: true

# Performance tuning
indices.memory.index_buffer_size: 20%
thread_pool.write.queue_size: 1000
```

#### Logstash Pipeline Configuration
```yaml
# logstash/pipeline/patriot.conf
input {
  beats {
    port => 5044
  }
  
  kafka {
    bootstrap_servers => "kafka:9092"
    topics => ["application-logs"]
    codec => json
  }
}

filter {
  # Parse PATRIOT application logs
  if [service] == "patriot" {
    json {
      source => "message"
    }
    
    # Add correlation tracking
    if [correlation_id] {
      mutate {
        add_tag => ["correlated"]
      }
    }
    
    # Parse order-related logs
    if [component] == "order-lifecycle" {
      mutate {
        add_field => { "log_category" => "trading" }
      }
    }
    
    # Parse risk management logs
    if [component] == "risk-engine" {
      mutate {
        add_field => { "log_category" => "risk" }
      }
      
      # Extract risk metrics
      if [risk_score] {
        mutate {
          convert => { "risk_score" => "float" }
        }
      }
    }
    
    # Geoip for admin access logs
    if [source_ip] {
      geoip {
        source => "source_ip"
        target => "geoip"
      }
    }
  }
  
  # Add timestamp
  date {
    match => [ "timestamp", "ISO8601" ]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "patriot-logs-%{+YYYY.MM.dd}"
    
    # Template for log structure
    template_name => "patriot-logs"
    template => "/usr/share/logstash/templates/patriot-logs.json"
    template_overwrite => true
  }
  
  # Send critical errors to separate index
  if [level] == "ERROR" or [level] == "CRITICAL" {
    elasticsearch {
      hosts => ["elasticsearch:9200"] 
      index => "patriot-errors-%{+YYYY.MM.dd}"
    }
  }
}
```

#### Application Logging Standards

**Structured Logging Implementation**:
```python
# services/common/logging.py
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

class PatriotLogger:
    """Structured logging for PATRIOT services"""
    
    def __init__(self, service_name: str, component: str):
        self.service_name = service_name
        self.component = component
        self.logger = logging.getLogger(f"{service_name}.{component}")
        
        # Configure structured JSON formatter
        formatter = StructuredFormatter(service_name, component)
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def info(self, message: str, **kwargs):
        """Log info level message"""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning level message"""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """Log error level message"""
        extra_data = kwargs
        if error:
            extra_data.update({
                "error_type": error.__class__.__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc()
            })
        self._log("ERROR", message, **extra_data)
    
    def audit(self, action: str, user_id: str = None, **kwargs):
        """Log audit trail events"""
        audit_data = {
            "log_category": "audit",
            "action": action,
            "user_id": user_id,
            **kwargs
        }
        self._log("INFO", f"Audit: {action}", **audit_data)
    
    def business(self, event: str, **kwargs):
        """Log business events"""
        business_data = {
            "log_category": "business",
            "business_event": event,
            **kwargs
        }
        self._log("INFO", f"Business: {event}", **business_data)
    
    def _log(self, level: str, message: str, **kwargs):
        """Internal logging method"""
        log_data = {
            "message": message,
            "level": level,
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def __init__(self, service_name: str, component: str):
        self.service_name = service_name
        self.component = component
        super().__init__()
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": self.service_name,
            "component": self.component,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add extra fields if present
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
            
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
            
        if hasattr(record, 'order_id'):
            log_entry["order_id"] = record.order_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# Usage in services
class OrderCommandService:
    """Example service with structured logging"""
    
    def __init__(self):
        self.logger = PatriotLogger("order-command-service", "order-processing")
    
    async def create_order(self, order_request: dict, user_id: str):
        """Create order with comprehensive logging"""
        correlation_id = str(uuid.uuid4())
        
        try:
            # Log order creation start
            self.logger.business(
                "order_creation_started",
                correlation_id=correlation_id,
                user_id=user_id,
                symbol=order_request["symbol"],
                order_type=order_request["type"],
                quantity=str(order_request["quantity"])
            )
            
            # Process order
            order = await self._process_order_creation(order_request)
            
            # Log successful creation
            self.logger.business(
                "order_created",
                correlation_id=correlation_id,
                user_id=user_id,
                order_id=order.id,
                symbol=order.symbol,
                status=order.status
            )
            
            # Audit log
            self.logger.audit(
                "order_created",
                user_id=user_id,
                order_id=order.id,
                correlation_id=correlation_id
            )
            
            return order
            
        except Exception as e:
            # Log error with context
            self.logger.error(
                "Order creation failed",
                error=e,
                correlation_id=correlation_id,
                user_id=user_id,
                order_request=order_request
            )
            raise
```

#### Kibana Dashboard Configuration

**Log Analysis Dashboard**:
```json
{
  "version": "8.8.0",
  "objects": [
    {
      "id": "patriot-logs-dashboard",
      "type": "dashboard", 
      "attributes": {
        "title": "PATRIOT Trading System - Log Analysis",
        "panelsJSON": [
          {
            "id": "log-levels-pie",
            "type": "visualization",
            "gridData": {"x": 0, "y": 0, "w": 24, "h": 15},
            "panelConfig": {
              "title": "Log Levels Distribution",
              "type": "pie",
              "params": {
                "addLegend": true,
                "addTooltip": true,
                "legendPosition": "right"
              }
            },
            "query": {
              "query": "service:patriot",
              "language": "kuery"
            },
            "aggs": [
              {
                "id": "1",
                "type": "count"
              },
              {
                "id": "2", 
                "type": "terms",
                "params": {"field": "level.keyword"}
              }
            ]
          },
          {
            "id": "error-timeline",
            "type": "visualization",
            "gridData": {"x": 0, "y": 15, "w": 48, "h": 15},
            "panelConfig": {
              "title": "Error Timeline",
              "type": "line"
            },
            "query": {
              "query": "service:patriot AND level:(ERROR OR CRITICAL)",
              "language": "kuery"
            },
            "aggs": [
              {
                "id": "1",
                "type": "count"
              },
              {
                "id": "2",
                "type": "date_histogram", 
                "params": {
                  "field": "@timestamp",
                  "interval": "5m"
                }
              }
            ]
          },
          {
            "id": "component-logs",
            "type": "visualization",
            "gridData": {"x": 24, "y": 0, "w": 24, "h": 15},
            "panelConfig": {
              "title": "Logs by Component",
              "type": "horizontal_bar"
            },
            "query": {
              "query": "service:patriot",
              "language": "kuery"
            },
            "aggs": [
              {
                "id": "1", 
                "type": "count"
              },
              {
                "id": "2",
                "type": "terms",
                "params": {"field": "component.keyword"}
              }
            ]
          }
        ],
        "timeRestore": false,
        "timeTo": "now",
        "timeFrom": "now-24h",
        "refreshInterval": {
          "pause": false,
          "value": 30000
        }
      }
    }
  ]
}
```

---

## 🔍 Distributed Tracing

### Jaeger Integration

#### Tracing Configuration
```python
# services/common/tracing.py
from jaeger_client import Config
from opentracing import tracer
import opentracing
from typing import Optional

class PatriotTracer:
    """Distributed tracing for PATRIOT services"""
    
    def __init__(self, service_name: str):
        config = Config(
            config={
                'sampler': {'type': 'const', 'param': 1},
                'logging': True,
                'reporter': {
                    'batch_size': 1,
                    'queue_size': 100,
                    'flush_interval': 1,
                    'agent': {
                        'reporting_host': 'jaeger',
                        'reporting_port': 6831,
                    }
                }
            },
            service_name=service_name
        )
        
        self.tracer = config.initialize_tracer()
        opentracing.set_global_tracer(self.tracer)
    
    def trace_operation(self, operation_name: str, parent_span=None):
        """Context manager for tracing operations"""
        return self.tracer.start_span(
            operation_name=operation_name,
            child_of=parent_span
        )
    
    def trace_async_operation(self, operation_name: str):
        """Decorator for async operations"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                with self.trace_operation(operation_name) as span:
                    try:
                        # Add operation metadata
                        span.set_tag('operation.name', func.__name__)
                        span.set_tag('operation.module', func.__module__)
                        
                        result = await func(*args, **kwargs)
                        span.set_tag('operation.result', 'success')
                        return result
                        
                    except Exception as e:
                        span.set_tag('operation.result', 'error')
                        span.set_tag('error.type', e.__class__.__name__)
                        span.set_tag('error.message', str(e))
                        raise
            return wrapper
        return decorator

# Usage in services
class OrderLifecycleService:
    """Order Lifecycle Service with distributed tracing"""
    
    def __init__(self):
        self.tracer = PatriotTracer("order-lifecycle-service")
    
    @trace_async_operation("start_order_tracking")
    async def start_tracking_order(self, order_data: dict):
        """Start tracking order with distributed tracing"""
        
        with self.tracer.trace_operation("validate_order_data") as span:
            span.set_tag('order.id', order_data['order_id'])
            span.set_tag('order.symbol', order_data['symbol'])
            await self._validate_order_data(order_data)
        
        with self.tracer.trace_operation("initialize_tracking") as span:
            await self._initialize_order_tracking(order_data)
        
        with self.tracer.trace_operation("start_monitoring") as span:
            await self._start_market_monitoring(order_data['symbol'])
```

---

## 🗄️ Database Infrastructure

### PostgreSQL Cluster Configuration

#### Primary Database Setup
```yaml
# docker-compose.postgres.yml
version: '3.8'

services:
  postgres-primary:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: patriot_db
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_REPLICATION_USER: replicator
      POSTGRES_REPLICATION_PASSWORD: ${REPLICATION_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
      - ./config/postgres/primary.conf:/etc/postgresql/postgresql.conf
      - ./config/postgres/pg_hba.conf:/etc/postgresql/pg_hba.conf
      - ./database/init:/docker-entrypoint-initdb.d
    command: >
      postgres
      -c config_file=/etc/postgresql/postgresql.conf
    ports:
      - "5432:5432"
    networks:
      - patriot-db

  postgres-replica-1:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGUSER: postgres
    volumes:
      - postgres_replica1_data:/var/lib/postgresql/data
      - ./config/postgres/replica.conf:/etc/postgresql/postgresql.conf
    command: >
      bash -c "
      until pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U replicator -v -P; do
        sleep 5
      done
      postgres -c config_file=/etc/postgresql/postgresql.conf
      "
    depends_on:
      - postgres-primary
    networks:
      - patriot-db

  postgres-replica-2:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: patriot
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGUSER: postgres
    volumes:
      - postgres_replica2_data:/var/lib/postgresql/data
      - ./config/postgres/replica.conf:/etc/postgresql/postgresql.conf
    command: >
      bash -c "
      until pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U replicator -v -P; do
        sleep 5
      done
      postgres -c config_file=/etc/postgresql/postgresql.conf
      "
    depends_on:
      - postgres-primary
    networks:
      - patriot-db

volumes:
  postgres_primary_data:
  postgres_replica1_data:
  postgres_replica2_data:

networks:
  patriot-db:
    driver: bridge
```

#### Database Performance Configuration
```conf
# config/postgres/primary.conf
# PostgreSQL configuration for PATRIOT primary database

# Connection settings
listen_addresses = '*'
port = 5432
max_connections = 200
shared_buffers = 2GB
effective_cache_size = 6GB

# Write-ahead logging
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
max_wal_senders = 3
wal_keep_size = 1GB

# Replication settings  
hot_standby = on
hot_standby_feedback = on

# Performance tuning
work_mem = 64MB
maintenance_work_mem = 512MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Logging
log_destination = 'stderr'
log_line_prefix = '[%t] %u@%d %p %r '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on
log_min_duration_statement = 1000

# Time series optimization (TimescaleDB)
shared_preload_libraries = 'timescaledb'
```

### Redis Cluster Configuration

```yaml
# docker-compose.redis.yml  
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    command: >
      redis-server
      --port 6379
      --bind 0.0.0.0
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
      --save 900 1
      --save 300 10
      --save 60 10000
    volumes:
      - redis_master_data:/data
    ports:
      - "6379:6379"
    networks:
      - patriot-redis

  redis-replica-1:
    image: redis:7-alpine
    command: >
      redis-server
      --port 6379
      --bind 0.0.0.0
      --replicaof redis-master 6379
      --appendonly yes
      --maxmemory 2gb
      --maxmemory-policy allkeys-lru
    volumes:
      - redis_replica1_data:/data
    depends_on:
      - redis-master
    networks:
      - patriot-redis

  redis-sentinel-1:
    image: redis:7-alpine
    command: redis-sentinel /usr/local/etc/redis/sentinel.conf
    volumes:
      - ./config/redis/sentinel.conf:/usr/local/etc/redis/sentinel.conf
    depends_on:
      - redis-master
    networks:
      - patriot-redis

volumes:
  redis_master_data:
  redis_replica1_data:

networks:
  patriot-redis:
    driver: bridge
```

---

> **Next Steps:**  
> 1. Continue with CI/CD Pipeline specifications
> 2. Add Security hardening guidelines  
> 3. Create Disaster Recovery procedures
> 4. Develop Infrastructure as Code (Terraform) specifications
> 5. Complete [05-ARCHITECTURAL-DECISIONS.md](05-ARCHITECTURAL-DECISIONS.md)

> **Implementation Priority:**  
> - **Phase 1**: Basic monitoring with Prometheus + Grafana
> - **Phase 2**: Structured logging with ELK stack
> - **Phase 3**: Distributed tracing with Jaeger
> - **Phase 4**: Database clustering and Redis HA
