# RDTII Backend - Build Stage Report

> **Last Updated:** 2026-04-30  
> **Status:** Phase 1 Complete — Project scaffolded, controllers & infrastructure ready

---

## Build Status

| Component | Status | Notes |
|---|---|---|
| Maven Compile | ✅ Pass | `./mvnw compile` succeeds |
| Dockerfile | ✅ Ready | Multi-stage build (JDK → JRE) |
| CI Workflow | ✅ Ready | `.github/workflows/backend-ci.yml` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Spring Boot 4.0.6 |
| Language | Java 17 |
| Build | Maven (with wrapper) |
| Database | PostgreSQL 17 + pgvector |
| ORM | Spring Data JPA / Hibernate |
| Container | Docker (multi-stage) |
| CI | GitHub Actions |

---

## Project Structure

```
rdtii-backend/RDTII/
├── src/main/java/org/unescap/rdtii/
│   ├── RdtiiApplication.java          # Spring Boot entry point
│   ├── config/
│   │   └── CorsConfig.java            # CORS configuration for frontend
│   ├── documents/
│   │   └── DocumentController.java    # PDF upload & management
│   ├── pillar/
│   │   └── PillarController.java      # RDTII pillar & criteria queries
│   ├── indicater/
│   │   └── IndicatorController.java   # Indicator listing & filtering
│   ├── ocr/
│   │   └── OcrController.java         # OCR extraction & task status
│   └── user/
│       └── UserController.java        # User management (optional)
├── src/main/resources/
│   ├── application.properties         # DB, JPA, server config
│   ├── banner.txt
│   └── migration/
│       ├── V1__init.sql               # Database schema (10 tables)
│       └── V2__set_ivfflat_probes.sql  # pgvector index tuning
└── src/test/java/org/unescap/rdtii/
    └── RdtiiApplicationTests.java     # Context load test
```

---

## REST API Endpoints (Stub)

All controllers return placeholder responses, ready for service/repository wiring.

| Controller | Base Path | Methods | Description |
|---|---|---|---|
| `DocumentController` | `/api/documents` | `GET`, `GET /{id}`, `POST /upload`, `DELETE /{id}` | Legal PDF lifecycle |
| `PillarController` | `/api/pillars` | `GET`, `GET /{id}`, `GET /{id}/criteria` | RDTII framework queries |
| `IndicatorController` | `/api/indicators` | `GET` (filtered by pillar/country), `GET /{id}` | Indicator detail |
| `OcrController` | `/api/ocr` | `POST /extract`, `GET /status/{taskId}` | OCR extraction pipeline |
| `UserController` | `/api/users` | `GET`, `GET /{id}`, `PUT /{id}` | User management |

---

## Database Schema (10 Tables)

| Table | Purpose |
|---|---|
| `countries` | 18-country reference data |
| `rdtii_pillars` | RDTII framework (pillars, criteria, indicators) |
| `documents` | Uploaded PDFs with status tracking |
| `document_sections` | Sliced articles/clauses from PDFs |
| `document_chunks` | RAG text chunks for semantic search |
| `chunk_embeddings` | 1536-dim vector embeddings (pgvector, IVFFlat index) |
| `extracted_obligations` | LLM-extracted compliance obligations |
| `regulation_mappings` | Obligation → RDTII criteria mappings |
| `audit_trail` | Source PDF highlight links for transparency UI |
| `users` | Optional user management |

---

## Docker Configuration

### Backend Dockerfile (`RDTII/Dockerfile`)

- **Stage 1 (build):** `eclipse-temurin:17-jdk` — Maven dependency resolution + JAR compilation
- **Stage 2 (runtime):** `eclipse-temurin:17-jre` — Minimal image with non-root user

```bash
cd rdtii-backend/RDTII && docker build -t rdtii-backend .
```

### Docker Compose (`/docker-compose.yaml`)

| Service | Image | Port |
|---|---|---|
| `postgres` | `pgvector/pgvector:pg17` | 5432 |
| `redis` | `redis:7-alpine` | 6379 |

```bash
docker-compose up -d
```

---

## Next Steps (Phase 2)

- [ ] Implement Entity classes mapping to database schema
- [ ] Create Repository interfaces (Spring Data JPA)
- [ ] Build Service layer for each domain
- [ ] Wire controllers to services (replace stubs)
- [ ] Add Flyway migration integration
- [ ] Implement OCR extraction pipeline integration
- [ ] Add RDTII data seeding from CSV dataset
