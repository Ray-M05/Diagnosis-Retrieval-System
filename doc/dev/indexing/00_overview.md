# Indexing Module Overview

El módulo de **Indexación** es responsable de procesar documentos adquiridos (HTML, PDF) y cargarlos en el motor de búsqueda (OpenSearch) de forma eficiente e incremental.

## Arquitectura

Sigue el patrón de **Arquitectura Hexagonal** (Ports & Adapters) para desacoplar la lógica de negocio de la infraestructura:

1.  **Core (Schemas & Ports)**: Define qué es un documento de índice y qué interfaces necesitan los Use Cases.
2.  **Use Cases**: Orquestan el flujo de indexación (lectura -> preparación -> enriquecimiento -> persistencia).
3.  **Adapters**: Implementaciones concretas de los puertos (OpenSearch para persistencia, SQLite para manifest de cambios, JSONL para lectura).
4.  **App**: Interfaz de usuario (CLI) para ejecutar los procesos.

## Flujo de Datos

```mermaid
graph LR
    Source[JSONL Source] -->|AcquiredDocument| UC[IndexOpenSearchUseCase]
    UC -->|Prepare| Prep[Prepare Module]
    Prep -->|Enrich| Concepts[Concept Extractor]
    Concepts -->|IndexDocument| Sink[OpenSearch Sink]
    UC -->|Update| Manifest[Manifest Store]
```

---

## Índice de Documentación

- [01_schemas.md](01_schemas.md): Modelos de datos.
- [02_ports.md](02_ports.md): Interfaces de los componentes.
- [03_adapters.md](03_adapters.md): Implementaciones de infraestructura.
- [04_usecases.md](04_usecases.md): Lógica de orquestación.
- [05_cli_config.md](05_cli_config.md): Guía de uso del CLI y configuración.
