export interface EvidenceChunk {
  id: string;
  snippet: string;
  rerankScore: number;
  nerScore: number;
}

export interface DiseaseResult {
  rank: number;
  name: string;
  evidenceChunks: EvidenceChunk[];
}

export interface HybridResult {
  docId: string;
  score: number;
  sourceUrl: string;
  crossEncoderScore: number;
  semanticScore: number;
  snippet: string;
}

export const hybridMockResults: HybridResult[] = [
  {
    docId: "DOC-2024-001",
    score: 0.942,
    sourceUrl: "https://pubmed.ncbi.nlm.nih.gov/324123",
    crossEncoderScore: 0.98,
    semanticScore: 0.89,
    snippet: "The presence of dry cough and fever in patients with respiratory distress often correlates with several viral pathogens, including Influenza A and B. High titers of viral RNA are detectable in upper respiratory secretions."
  },
  {
    docId: "DOC-2024-005",
    score: 0.885,
    sourceUrl: "https://mayoclinic.org/respiratory-conditions",
    crossEncoderScore: 0.91,
    semanticScore: 0.84,
    snippet: "Clinical evaluation of patients reporting sudden onset of chills and muscle aches should include screening for seasonal flu variants. Differential diagnosis involves checking for secondary bacterial pneumonia."
  },
  {
    docId: "DOC-2024-012",
    score: 0.812,
    sourceUrl: "https://cdc.gov/flu/clinical-guidelines",
    crossEncoderScore: 0.85,
    semanticScore: 0.76,
    snippet: "Viral shedding typically occurs for 5-7 days after symptom onset. Primary symptoms include high fever, fatigue, and persistent dry cough, which may lead to dehydration in elderly patients."
  }
];

export const diagnosticMockResults: DiseaseResult[] = [
  {
    rank: 1,
    name: "Influenza (Flu)",
    evidenceChunks: [
      {
        id: "chunk-1",
        snippet: "Patient presents with persistent dry cough and high-grade fever. Muscle aches are reported as severe in the extremities.",
        rerankScore: 0.985,
        nerScore: 0.92
      },
      {
        id: "chunk-2",
        snippet: "Symptoms such as chills and fatigue are classic indicators of viral respiratory infections, specifically influenza-like illnesses.",
        rerankScore: 0.942,
        nerScore: 0.88
      },
      {
        id: "chunk-3",
        snippet: "Secondary indicators observed: sudden onset of lethargy and mild headache during the first 24 hours of symptom onset.",
        rerankScore: 0.812,
        nerScore: 0.75
      }
    ]
  },
  {
    rank: 2,
    name: "Pneumonia",
    evidenceChunks: [
      {
        id: "chunk-4",
        snippet: "Severe chest pain associated with deep breathing or coughing suggests alveolar inflammation. Shortness of breath is also prevalent.",
        rerankScore: 0.854,
        nerScore: 0.79
      },
      {
        id: "chunk-5",
        snippet: "High fever exceeding 101°F and production of thick phlegm indicate possible bacterial or viral infection of the lung tissue.",
        rerankScore: 0.789,
        nerScore: 0.72
      }
    ]
  }
];

export interface Disease {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  source: string;
  sourceUrl: string;
}

export const diseases: Disease[] = [
  {
    id: "1",
    name: "Common Cold",
    description: "A viral infection of your nose and throat.",
    symptoms: ["sneezing", "stuffy nose", "sore throat", "coughing"],
    source: "Mayo Clinic",
    sourceUrl: "https://www.mayoclinic.org/diseases-conditions/common-cold/symptoms-causes/syc-20351605"
  },
  {
    id: "2",
    name: "Influenza (Flu)",
    description: "A viral infection that attacks your respiratory system.",
    symptoms: ["fever", "muscle aches", "chills", "fatigue", "dry cough"],
    source: "CDC - Centers for Disease Control and Prevention",
    sourceUrl: "https://www.cdc.gov/flu/symptoms/symptoms.htm"
  },
  {
    id: "3",
    name: "Migraine",
    description: "A headache that can cause severe throbbing pain or a pulsing sensation.",
    symptoms: ["headache", "nausea", "light sensitivity", "blurred vision"],
    source: "World Health Organization (WHO)",
    sourceUrl: "https://www.who.int/news-room/fact-sheets/detail/headache-disorders"
  },
  {
    id: "4",
    name: "Gastroenteritis",
    description: "Inflammation of the lining of the stomach and intestines.",
    symptoms: ["diarrhea", "abdominal pain", "vomiting", "mild fever"],
    source: "NHS UK",
    sourceUrl: "https://www.nhs.uk/conditions/diarrhoea-and-vomiting/"
  },
  {
    id: "5",
    name: "Seasonal Allergies",
    description: "Immune system reaction to pollen, dust, or mold.",
    symptoms: ["itchy eyes", "sneezing", "runny nose", "scratchy throat"],
    source: "American Academy of Allergy, Asthma & Immunology",
    sourceUrl: "https://www.aaaai.org/conditions-treatments/allergies"
  },
  {
    id: "6",
    name: "Appendicitis",
    description: "An inflammation of the appendix, a finger-shaped pouch that projects from your colon.",
    symptoms: ["sharp abdominal pain", "loss of appetite", "nausea", "fever"],
    source: "Johns Hopkins Medicine",
    sourceUrl: "https://www.hopkinsmedicine.org/health/conditions-and-diseases/appendicitis"
  },
  {
    id: "7",
    name: "Pneumonia",
    description: "An infection that inflames the air sacs in one or both lungs.",
    symptoms: ["shortness of breath", "chest pain", "high fever", "cough with phlegm"],
    source: "American Lung Association",
    sourceUrl: "https://www.lung.org/lung-health-diseases/lung-disease-lookup/pneumonia"
  },
  {
    id: "8",
    name: "Conjunctivitis (Pink Eye)",
    description: "An inflammation or infection of the transparent membrane that lines your eyelid.",
    symptoms: ["red eyes", "itchy eyes", "eye discharge", "gritty sensation"],
    source: "National Eye Institute",
    sourceUrl: "https://www.nei.nih.gov/learn-about-eye-health/eye-conditions-and-diseases/pink-eye"
  }
];
