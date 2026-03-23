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

export const commonSymptoms = Array.from(
  new Set(diseases.flatMap((d) => d.symptoms))
).sort();
