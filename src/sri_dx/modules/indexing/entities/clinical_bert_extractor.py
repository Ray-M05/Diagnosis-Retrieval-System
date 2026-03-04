# modules/indexing/entities/clinical_bert_extractor.py
"""
Extractor de Entidades Clínicas usando Bio_ClinicalBERT.

Implementación del EntityExtractorPort que usa Bio_ClinicalBERT
para identificar entidades médicas en texto clínico.

Estrategia:
- Usa embeddings de tokens para detectar spans de entidades
- Aplica reglas heurísticas basadas en patrones médicos comunes
- Optimizado para notas clínicas estilo MIMIC-III

Limitaciones:
- Bio_ClinicalBERT no es un modelo NER nativo
- Para NER puro, considerar: clinicalBERT-NER, en_core_sci_lg
- Esta implementación usa embeddings + heurísticas
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Set, TYPE_CHECKING

from sri_dx.core.ports.indexing.entity_extractor_port import (
    EntityExtractorPort,
    ClinicalEntity,
    EntityExtractionConfig
)

if TYPE_CHECKING:
    import torch
    from sri_dx.adapters.embeddings.clinical_bert_adapter import ClinicalBERTAdapter

logger = logging.getLogger(__name__)


# Patrones heurísticos para entidades médicas comunes
MEDICAL_PATTERNS: Dict[str, List[re.Pattern]] = {
    "PROBLEM": [
        re.compile(r'\b(diagnosed?\s+with|suffering\s+from|presents?\s+with)\s+([a-zA-Z\s\-]+)', re.I),
        re.compile(r'\b(pain|ache|discomfort|dysfunction|disorder|syndrome|disease|infection|inflammation)\b', re.I),
        re.compile(r'\b(fever|cough|nausea|vomiting|diarrhea|headache|fatigue|weakness)\b', re.I),
        re.compile(r'\b(diabetes|hypertension|cancer|pneumonia|asthma|COPD|CHF|MI|CVA|stroke)\b', re.I),
        re.compile(r'\b(acute|chronic|severe|mild|moderate)\s+[a-zA-Z]+\s*(pain|condition|disease)?\b', re.I),
    ],
    "TREATMENT": [
        re.compile(r'\b(prescribed|administered|given|started\s+on)\s+([a-zA-Z\s\-]+)', re.I),
        re.compile(r'\b\d+\s*(mg|ml|mcg|units?)\s+([a-zA-Z]+)\b', re.I),
        re.compile(r'\b(aspirin|ibuprofen|acetaminophen|metformin|lisinopril|atorvastatin)\b', re.I),
        re.compile(r'\b(surgery|procedure|therapy|treatment|intervention|transplant)\b', re.I),
        re.compile(r'\b(antibiotic|analgesic|diuretic|beta.?blocker|ACE.?inhibitor)\b', re.I),
    ],
    "TEST": [
        re.compile(r'\b(CT|MRI|X-?ray|ultrasound|ECG|EKG|EEG|PET)\s*(scan)?\b', re.I),
        re.compile(r'\b(blood\s+test|urinalysis|biopsy|culture|smear)\b', re.I),
        re.compile(r'\b(CBC|BMP|CMP|LFT|BNP|troponin|hemoglobin|hematocrit)\b', re.I),
        re.compile(r'\b(glucose|creatinine|potassium|sodium|WBC|RBC|platelet)\s*(level|count)?\b', re.I),
    ],
    "ANATOMY": [
        re.compile(r'\b(heart|lung|liver|kidney|brain|stomach|intestine|colon)\b', re.I),
        re.compile(r'\b(left|right)\s+(arm|leg|lung|kidney|eye|ear)\b', re.I),
        re.compile(r'\b(chest|abdomen|pelvis|thorax|cranium|spine)\b', re.I),
        re.compile(r'\b(artery|vein|nerve|muscle|bone|joint|cartilage)\b', re.I),
        re.compile(r'\b(cardiac|hepatic|renal|pulmonary|cerebral|gastric)\b', re.I),
    ]
}


@dataclass
class ClinicalBERTExtractorConfig:
    """Configuración específica del extractor."""
    
    use_embeddings_similarity: bool = True
    """Si True, usa embeddings para validar entidades detectadas por regex."""
    
    entity_embedding_threshold: float = 0.6
    """Umbral de similitud para validar entidad contra prototipos."""
    
    max_entity_words: int = 6
    """Máximo de palabras en una entidad."""
    
    min_entity_chars: int = 2
    """Mínimo de caracteres para considerar una entidad."""
    
    deduplicate: bool = True
    """Si True, elimina entidades duplicadas/solapadas."""


class ClinicalBERTEntityExtractor(EntityExtractorPort):
    """
    Extractor de entidades clínicas usando Bio_ClinicalBERT.
    
    Combina:
    1. Patrones regex médicos
    2. Validación con embeddings (opcional)
    3. Post-procesamiento y deduplicación
    """
    
    SUPPORTED_LABELS = ["PROBLEM", "TREATMENT", "TEST", "ANATOMY"]
    
    def __init__(
        self,
        extractor_config: Optional[ClinicalBERTExtractorConfig] = None,
        bert_adapter: Optional["ClinicalBERTAdapter"] = None
    ):
        """
        Inicializa el extractor.
        
        Args:
            extractor_config: Configuración del extractor
            bert_adapter: Adaptador BERT (si None, crea uno)
        """
        self.extractor_config = extractor_config or ClinicalBERTExtractorConfig()
        self._bert_adapter = bert_adapter
        
        # Cache de embeddings prototipo para cada tipo de entidad
        self._prototype_embeddings: Optional[Dict[str, "torch.Tensor"]] = None
    
    @property
    def bert_adapter(self) -> "ClinicalBERTAdapter":
        """Acceso lazy al adaptador BERT."""
        if self._bert_adapter is None:
            from sri_dx.adapters.embeddings.clinical_bert_adapter import (
                ClinicalBERTAdapter
            )
            self._bert_adapter = ClinicalBERTAdapter.get_instance()
        return self._bert_adapter
    
    @property
    def model_name(self) -> str:
        """Nombre del modelo usado."""
        return "emilyalsentzer/Bio_ClinicalBERT"
    
    def get_supported_labels(self) -> List[str]:
        """Retorna labels soportados."""
        return self.SUPPORTED_LABELS.copy()
    
    def extract(
        self, 
        text: str, 
        config: Optional[EntityExtractionConfig] = None
    ) -> List[ClinicalEntity]:
        """
        Extrae entidades clínicas de un texto.
        
        Args:
            text: Texto clínico
            config: Configuración de extracción
            
        Returns:
            Lista de entidades encontradas
        """
        config = config or EntityExtractionConfig()
        
        # Filtrar labels a extraer
        labels_to_extract = config.labels_to_extract or self.SUPPORTED_LABELS
        labels_to_extract = [l for l in labels_to_extract if l in self.SUPPORTED_LABELS]
        
        entities: List[ClinicalEntity] = []
        
        # Extraer por patrones regex
        for label in labels_to_extract:
            patterns = MEDICAL_PATTERNS.get(label, [])
            for pattern in patterns:
                for match in pattern.finditer(text):
                    # Obtener el texto matcheado
                    # Usar grupo completo o grupo 2 si existe (para patrones con contexto)
                    entity_text = match.group(2) if match.lastindex and match.lastindex >= 2 else match.group(0)
                    entity_text = entity_text.strip()
                    
                    # Validar longitud
                    if len(entity_text) < self.extractor_config.min_entity_chars:
                        continue
                    
                    if len(entity_text.split()) > self.extractor_config.max_entity_words:
                        continue
                    
                    # Calcular posición
                    start = match.start(2) if match.lastindex and match.lastindex >= 2 else match.start()
                    end = match.end(2) if match.lastindex and match.lastindex >= 2 else match.end()
                    
                    # Crear entidad
                    entity = ClinicalEntity(
                        text=entity_text,
                        label=label,
                        start_char=start,
                        end_char=end,
                        confidence=0.7,  # Base confidence para regex
                        normalized_text=self._normalize_text(entity_text),
                        metadata={"extraction_method": "regex"}
                    )
                    
                    entities.append(entity)
        
        # Validar con embeddings si está configurado
        if self.extractor_config.use_embeddings_similarity and entities:
            entities = self._validate_with_embeddings(entities, config)
        
        # Deduplicar
        if self.extractor_config.deduplicate:
            entities = self._deduplicate_entities(entities)
        
        # Filtrar por confianza
        entities = [e for e in entities if e.confidence >= config.min_confidence]
        
        # Ordenar por posición
        entities.sort(key=lambda e: e.start_char)
        
        return entities
    
    def extract_batch(
        self, 
        texts: List[str], 
        config: Optional[EntityExtractionConfig] = None
    ) -> List[List[ClinicalEntity]]:
        """
        Extrae entidades de múltiples textos.
        
        Optimización: procesa todos los textos primero con regex,
        luego valida todos los embeddings en batch.
        
        Args:
            texts: Lista de textos
            config: Configuración
            
        Returns:
            Lista de listas de entidades
        """
        config = config or EntityExtractionConfig()
        
        # Paso 1: Extraer con regex para todos los textos
        all_entities: List[List[ClinicalEntity]] = []
        all_entity_texts: List[str] = []
        entity_indices: List[tuple[int, int]] = []  # (text_idx, entity_idx)
        
        for text_idx, text in enumerate(texts):
            # Extraer sin validación de embeddings
            temp_config = ClinicalBERTExtractorConfig(
                use_embeddings_similarity=False,
                deduplicate=False
            )
            original_config = self.extractor_config
            self.extractor_config = temp_config
            
            entities = self.extract(text, config)
            all_entities.append(entities)
            
            self.extractor_config = original_config
            
            # Guardar textos para batch embedding
            for ent_idx, entity in enumerate(entities):
                all_entity_texts.append(entity.text)
                entity_indices.append((text_idx, ent_idx))
        
        # Paso 2: Validar con embeddings en batch
        if self.extractor_config.use_embeddings_similarity and all_entity_texts:
            # Obtener embeddings de todas las entidades de una vez
            entity_embeddings = self.bert_adapter.encode(all_entity_texts)
            prototype_embeddings = self._get_prototype_embeddings()
            
            # Actualizar confianza basada en similitud
            import torch
            
            for idx, (text_idx, ent_idx) in enumerate(entity_indices):
                entity = all_entities[text_idx][ent_idx]
                entity_emb = entity_embeddings[idx:idx+1]
                
                # Buscar mejor similitud con prototipos de su label
                label_protos = prototype_embeddings.get(entity.label)
                if label_protos is not None:
                    similarities = torch.nn.functional.cosine_similarity(
                        entity_emb, label_protos
                    )
                    max_sim = similarities.max().item()
                    
                    # Ajustar confianza
                    new_confidence = (entity.confidence + max_sim) / 2
                    
                    # Crear nueva entidad con confianza actualizada
                    all_entities[text_idx][ent_idx] = ClinicalEntity(
                        text=entity.text,
                        label=entity.label,
                        start_char=entity.start_char,
                        end_char=entity.end_char,
                        confidence=new_confidence,
                        normalized_text=entity.normalized_text,
                        umls_cui=entity.umls_cui,
                        metadata={**entity.metadata, "embedding_similarity": max_sim}
                    )
        
        # Paso 3: Post-procesamiento
        result = []
        for entities in all_entities:
            if self.extractor_config.deduplicate:
                entities = self._deduplicate_entities(entities)
            entities = [e for e in entities if e.confidence >= config.min_confidence]
            entities.sort(key=lambda e: e.start_char)
            result.append(entities)
        
        return result
    
    def _get_prototype_embeddings(self) -> Dict[str, "torch.Tensor"]:
        """
        Obtiene embeddings prototipo para cada tipo de entidad.
        Se cachean para reutilizar.
        """
        if self._prototype_embeddings is not None:
            return self._prototype_embeddings
        
        # Ejemplos prototipo para cada categoría
        prototypes = {
            "PROBLEM": [
                "chest pain", "shortness of breath", "diabetes mellitus",
                "hypertension", "fever", "headache", "abdominal pain",
                "heart failure", "pneumonia", "sepsis"
            ],
            "TREATMENT": [
                "aspirin 81mg", "metformin", "lisinopril", "surgery",
                "chemotherapy", "physical therapy", "insulin",
                "antibiotic therapy", "IV fluids", "oxygen therapy"
            ],
            "TEST": [
                "chest X-ray", "CT scan", "MRI", "blood test", "ECG",
                "complete blood count", "urinalysis", "biopsy",
                "glucose level", "creatinine"
            ],
            "ANATOMY": [
                "heart", "lung", "liver", "kidney", "brain",
                "left arm", "right leg", "abdomen", "chest",
                "coronary artery"
            ]
        }
        
        self._prototype_embeddings = {}
        for label, examples in prototypes.items():
            embeddings = self.bert_adapter.encode(examples)
            self._prototype_embeddings[label] = embeddings
        
        return self._prototype_embeddings
    
    def _validate_with_embeddings(
        self, 
        entities: List[ClinicalEntity],
        config: EntityExtractionConfig
    ) -> List[ClinicalEntity]:
        """Valida entidades usando similitud con prototipos."""
        import torch
        
        if not entities:
            return entities
        
        # Obtener embeddings de entidades
        entity_texts = [e.text for e in entities]
        entity_embeddings = self.bert_adapter.encode(entity_texts)
        
        # Obtener prototipos
        prototype_embeddings = self._get_prototype_embeddings()
        
        # Validar cada entidad
        validated = []
        for idx, entity in enumerate(entities):
            entity_emb = entity_embeddings[idx:idx+1]
            label_protos = prototype_embeddings.get(entity.label)
            
            if label_protos is None:
                validated.append(entity)
                continue
            
            # Calcular similitud máxima con prototipos
            similarities = torch.nn.functional.cosine_similarity(entity_emb, label_protos)
            max_sim = similarities.max().item()
            
            # Ajustar confianza basada en similitud
            new_confidence = (entity.confidence + max_sim) / 2
            
            # Solo mantener si supera umbral
            if max_sim >= self.extractor_config.entity_embedding_threshold:
                validated.append(ClinicalEntity(
                    text=entity.text,
                    label=entity.label,
                    start_char=entity.start_char,
                    end_char=entity.end_char,
                    confidence=new_confidence,
                    normalized_text=entity.normalized_text,
                    umls_cui=entity.umls_cui,
                    metadata={**entity.metadata, "embedding_similarity": max_sim}
                ))
        
        return validated
    
    def _deduplicate_entities(
        self, 
        entities: List[ClinicalEntity]
    ) -> List[ClinicalEntity]:
        """Elimina entidades duplicadas o solapadas, manteniendo la de mayor confianza."""
        if not entities:
            return entities
        
        # Ordenar por posición y luego por confianza (descendente)
        sorted_entities = sorted(
            entities, 
            key=lambda e: (e.start_char, -e.confidence)
        )
        
        result = []
        for entity in sorted_entities:
            # Verificar si solapa con alguna entidad ya aceptada
            overlaps = False
            for accepted in result:
                # Hay solapamiento si los rangos se intersectan
                if not (entity.end_char <= accepted.start_char or 
                        entity.start_char >= accepted.end_char):
                    overlaps = True
                    break
            
            if not overlaps:
                result.append(entity)
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normaliza texto de entidad."""
        # Lowercase
        text = text.lower()
        # Remover espacios extras
        text = re.sub(r'\s+', ' ', text).strip()
        # Remover puntuación al inicio/final
        text = re.sub(r'^[^\w]+|[^\w]+$', '', text)
        return text
