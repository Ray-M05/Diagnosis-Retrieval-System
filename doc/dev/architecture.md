# Arquitectura Detallada: SRI-DX

Este documento describe la arquitectura de **SRI-DX** y proporciona guías técnicas para desarrolladores que deseen ampliar las funcionalidades del sistema.

## 📐 Patrón: Hexagonal Mínima + Módulos SRI

Hemos adoptado una arquitectura Hexagonal (Puertos y Adaptadores) simplificada para asegurar que el sistema sea testeable y que los componentes sean fácilmente reemplazables.

### Capas del Sistema

1.  **Core (Dominio)**: Contiene los modelos de datos (`schemas.py`) y las interfaces (`ports.py`). No depende de ninguna otra capa.
2.  **Use Cases (Aplicación)**: Orquestan los flujos de trabajo (ej: búsqueda, indexación) utilizando los puertos definidos en el Core.
3.  **Modules (Funcionalidades SRI)**: Implementaciones internas de los componentes requeridos por la guía del proyecto (Retrieval, RAG, Web Search, etc.).
4.  **Adapters (Infraestructura)**: Implementaciones concretas que interactúan con el mundo exterior (bases de datos vectoriales, librerías de embeddings, scraping).
5.  **App (Entrypoints)**: Interfaz de usuario (Streamlit) y línea de comandos (CLI).

## 🛠️ Cómo implementar nuevas funcionalidades

Para añadir un nuevo componente (ej. un nuevo Ranker o un nuevo módulo de Scraping), siga este flujo:

### 1. Definir el Puerto (si no existe)

En `src/sri_dx/core/ports.py`, defina una clase abstracta que herede de `ABC`.

```python
class NewComponentPort(ABC):
    @abstractmethod
    def do_something(self, data: Any) -> Result:
        pass
```

### 2. Implementar el Adaptador o Módulo

Cree la implementación concreta en la carpeta correspondiente (`adapters/` si es una dependencia externa, `modules/` si es lógica propia del SRI).

```python
class ConcreteImplementation(NewComponentPort):
    def do_something(self, data: Any) -> Result:
        # Lógica específica aquí
        return Result(...)
```

### 3. Integrar en el Caso de Uso o App

Inyecte la implementación concreta a través de los constructores. **Evite instanciar clases concretas dentro de los casos de uso.**

```python
# En la inicialización (app/cli.py o app/ui_streamlit.py)
retriever = MyConcreteRetriever()
ranker = MyConcreteRanker()
search_flow = SearchUseCase(retriever, ranker)
```

## 🧪 Testing

Las pruebas deben enfocarse en los Casos de Uso y el Core. Utilice mocks para los puertos definidos en `ports.py` para evitar dependencias pesadas durante los tests unitarios.
