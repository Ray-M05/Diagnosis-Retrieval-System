# Test Cases — Diagnosis Retrieval System

> Reproducible test document for the clinical RAG system. Each disease includes:
> - **Query without chart** (symptom paragraph only, as a general practitioner would describe the patient).
> - **Male patient chart** and **Female patient chart** (realistic, not obvious).
> - **Expected output (Top-1)** and plausible differential diagnoses.
> - **Critical notes** on what is being stress-tested.
>
> **How to use:** copy the "Chief Complaint" into the *Patient Chart* form, fill in the chart fields, and paste the **query** into the search bar. Test first **without chart** (query only) and then **with chart**.
>
> **User language:** English (general practitioner, not specialist).

---

## Index

0. [Web-Enrichment Validation Cases](#0-web-enrichment-validation-cases) — rare diseases poorly covered locally; web chunks must reach the final top
    - 0.1 [POEMS Syndrome](#01-poems-syndrome)
    - 0.2 [Susac Syndrome](#02-susac-syndrome)
    - 0.3 [Whipple Disease](#03-whipple-disease)
1. [Acromegaly](#1-acromegaly)
2. [Lactic Acidosis](#2-lactic-acidosis)
3. [Hyperthyroidism](#3-hyperthyroidism)
4. [Congenital Hypothyroidism](#4-congenital-hypothyroidism)
5. [Hemolytic Anemia](#5-hemolytic-anemia)
6. [Arteriosclerosis / Atherosclerosis](#6-arteriosclerosis--atherosclerosis)
7. [Osteoarthritis](#7-osteoarthritis)
8. [Critical Cases with Negation](#8-critical-cases-with-negation)
9. [Critical Cases with Ambiguity and Overlap](#9-critical-cases-with-ambiguity-and-overlap)
10. [Cases where the Chart may Influence Negatively](#10-cases-where-the-chart-may-influence-negatively)
11. [Additional Diseases](#11-additional-diseases)
    - 11.1 [Type 2 Diabetes Mellitus](#111-type-2-diabetes-mellitus)
    - 11.2 [Pulmonary Embolism](#112-pulmonary-embolism)
    - 11.3 [Addison's Disease (Primary Adrenal Insufficiency)](#113-addisons-disease-primary-adrenal-insufficiency)
    - 11.4 [Cushing's Syndrome](#114-cushings-syndrome)
    - 11.5 [Parkinson's Disease](#115-parkinsons-disease)
    - 11.6 [Multiple Sclerosis](#116-multiple-sclerosis)
    - 11.7 [Systemic Lupus Erythematosus](#117-systemic-lupus-erythematosus)
    - 11.8 [Congestive Heart Failure](#118-congestive-heart-failure)
    - 11.9 [Acute Pancreatitis](#119-acute-pancreatitis)
    - 11.10 [Pheochromocytoma](#1110-pheochromocytoma)
12. [Extended Disease Coverage](#12-extended-disease-coverage) — §12.1 to §12.65 (minimal-structure cases: query + expected output only)

---

## 0. Web-Enrichment Validation Cases

> These cases exist to validate the **web-search-and-enrich** path end to end.
> They are rare diseases the local corpus (Mayo Clinic / NHS / MSD Manuals / CDC)
> barely covers, but which PubMed / Europe PMC cover well. With web enrichment ON
> (`stages.web_enrichment = true`), the medical APIs are queried, their documents
> are indexed, **embedded into the shared vector index**, and then retrieved through
> the normal hybrid (BM25 + kNN) + cross-encoder pipeline alongside local content.
> The validation criterion is that **web chunks reach the final top**, not just that
> web search is triggered.
>
> **How to use:** paste the query into the search bar with web enrichment enabled.
> Observe that several top cards link to `europepmc.org` / `pubmed.ncbi.nlm.nih.gov`.

### 0.1 POEMS Syndrome

```
Middle-aged adult with progressive peripheral neuropathy, enlarged liver and spleen, skin hyperpigmentation and thickening, excessive hair growth, and a monoclonal plasma cell disorder with elevated VEGF.
```

- **Top-1 esperado:** POEMS syndrome (Polyneuropathy, Organomegaly, Endocrinopathy, Monoclonal protein, Skin changes).
- **Diferenciales plausibles:** Chronic inflammatory demyelinating polyneuropathy (CIDP), multiple myeloma, amyloidosis, paraneoplastic neuropathy.
- **Notas críticas:**
  - Strongest web case observed: **9/10** final cards come from web (Europe PMC), all retrieved by kNN (`vector_score ≈ 0.97–0.98`) after embedding.
  - POEMS is essentially absent from the local corpus, so without working web embedding the top would be irrelevant local conditions.

### 0.2 Susac Syndrome

```
Young woman with the triad of encephalopathy with confusion, branch retinal artery occlusions causing visual loss, and sensorineural hearing loss.
```

- **Top-1 esperado:** Susac syndrome (retinocochleocerebral vasculopathy).
- **Diferenciales plausibles:** Multiple sclerosis, ADEM, primary CNS angiitis, MELAS.
- **Notas críticas:**
  - Best **qualitative** web case: web chunks win even on the cross-encoder (positive `rerank_score ≈ 1.5–2.1`), not only on kNN — i.e. web is genuinely the most relevant, not merely surfaced. **7/10** top cards are web.

### 0.3 Whipple Disease

```
Adult with chronic diarrhea and weight loss, migratory joint pain for years, abdominal pain, low-grade fever, and skin darkening; small bowel biopsy shows PAS-positive macrophages.
```

- **Top-1 esperado:** Whipple disease (*Tropheryma whipplei* infection).
- **Diferenciales plausibles:** Celiac disease, inflammatory bowel disease, intestinal lymphoma, sprue.
- **Notas críticas:**
  - Mixed local/web case: the **#1** card is web (`rerank_score` above all local results), with local differentials (celiac, pouchitis) following. Validates that web competes on equal footing rather than being injected at fixed positions.

---

## 1. Acromegaly

### 1.1 Consulta sin chart (RAG simple)

```
Patient who for several years has noticed that his shoe size has increased and that his rings no longer fit. He reports that his facial features have become coarser, with a more prominent jaw and separation of the teeth. He complains of persistent headache, tingling in the hands compatible with carpal tunnel syndrome, excessive sweating, and intense snoring with sleep apnea. He also has generalized joint pain and decreased libido.
```

### 1.2 Chart — Male Patient

- **Age:** 47
- **Sex:** M
- **Comorbidities:** arterial hypertension, glucose intolerance, sleep apnea syndrome
- **Chief Complaint:** Progressive change in shoe and ring size over the last 4 years, with daily headache
- **Vital Signs:** HR 78 · BP 148/92 · RR 14 · SpO2 96 · Temp 36.7
- **Physical Findings:** Enlarged hands and feet, coarse facial features, prognathism, mild macroglossia, thickened skin with hyperhidrosis. Bilateral positive Tinel's sign.
- **Lab Results:** Fasting glucose 128 mg/dL, HbA1c 6.7%. IGF-1 and GH not requested.
- **Imaging:** None available.
- **Current Medications:** enalapril 20 mg/day, ibuprofen PRN
- **Allergies:** NKDA
- **Social History:** Non-smoker, social drinker, truck driver
- **Family History:** Father with hypertension. No known endocrine conditions.
- **Additional Notes:** Reports his wife notices he snores louder and louder, and that he has had to change his wedding ring twice.

### 1.3 Chart — Female Patient

- **Age:** 52
- **Sex:** F
- **Comorbidities:** multinodular goiter, type 2 diabetes
- **Chief Complaint:** Generalized joint pain, paresthesias in hands, and voice changes
- **Vital Signs:** HR 82 · BP 142/88 · RR 16 · SpO2 97 · Temp 36.8
- **Physical Findings:** Hoarse and deep voice, coarse facies, prominent supraciliary arches, large hands with sausage-shaped fingers. Palpable goiter.
- **Lab Results:** Glucose 156 mg/dL, HbA1c 7.4%, TSH 1.2 mIU/L (normal). No IGF-1.
- **Imaging:** Thyroid ultrasound with multiple benign nodules.
- **Current Medications:** metformin 1g BID
- **Allergies:** NKDA
- **Social History:** Housewife, non-smoker
- **Family History:** Mother with T2DM and hypertension
- **Additional Notes:** Reports amenorrhea for 8 months (attributed to menopause) and occasional galactorrhea.

### 1.4 Salida esperada

- **Top-1 esperado:** Acromegaly
- **Diferenciales plausibles:** Hypothyroidism (due to hoarse voice / facies), gigantism (ruled out by adult age), idiopathic carpal tunnel syndrome, primary osteoarthritis.
- **Notas críticas:**
  - The female patient has comorbidities (goiter, T2DM) that **distract** toward hyperthyroidism/hypothyroidism. The system should prioritize acromegaly because of the facies + large hands + galactorrhea.
  - The male has an "obvious endocrine" chart without the physician having requested IGF-1 — tests whether the system suggests the correct diagnosis and the appropriate diagnostic test.

---

## 2. Lactic Acidosis

### 2.1 Consulta sin chart

```
Patient arriving at the emergency department with severe abdominal pain, nausea, and vomiting. Presents with rapid deep breathing, drowsiness, and confusion. Reports having taken more medication than usual over the last few days because of feeling unwell. Blood gas shows pH 7.18 and serum lactate of 7.2 mmol/L.
```

### 2.2 Chart — Male Patient

- **Age:** 64
- **Sex:** M
- **Comorbidities:** long-standing type 2 diabetes, stage 3b chronic kidney disease, hypertension
- **Chief Complaint:** Abdominal pain, nausea, and rapid breathing of 24 hours' evolution
- **Vital Signs:** HR 118 · BP 92/58 · RR 32 · SpO2 95 · Temp 36.2
- **Physical Findings:** Lethargic, dry mucous membranes, Kussmaul respiration, diffusely tender abdomen without peritoneal signs.
- **Lab Results:** pH 7.17, HCO3 9 mEq/L, lactate 8.1 mmol/L, glucose 142 mg/dL (no ketones), creatinine 2.8 mg/dL, K 5.6.
- **Imaging:** Abdominal X-ray with no acute findings.
- **Current Medications:** metformin 1g BID, enalapril 20 mg, atorvastatin 40 mg
- **Allergies:** NKDA
- **Social History:** Retired, moderate drinker
- **Family History:** Father deceased from MI
- **Additional Notes:** Had gastroenteritis with decreased fluid intake during the past week.

### 2.3 Chart — Female Patient

- **Age:** 38
- **Sex:** F
- **Comorbidities:** none known
- **Chief Complaint:** Persistent vomiting, stomach pain, and shortness of breath
- **Vital Signs:** HR 124 · BP 88/52 · RR 34 · SpO2 94 · Temp 38.6
- **Physical Findings:** Diaphoresis, pallor, tachypnea with deep breathing, soft abdomen with mild diffuse tenderness. No neurological focal signs.
- **Lab Results:** pH 7.20, HCO3 10, lactate 6.8 mmol/L, glucose 88 mg/dL, leukocytes 18,500 with neutrophilia, CRP 220, blood cultures pending.
- **Imaging:** Chest X-ray with right basal infiltrate.
- **Current Medications:** oral contraceptive
- **Allergies:** penicillin
- **Social History:** Teacher, non-smoker, occasional alcohol
- **Family History:** Unremarkable
- **Additional Notes:** 3 days of fever and productive cough, self-medicated with paracetamol and ibuprofen.

### 2.4 Salida esperada

- **Top-1 esperado:** Lactic acidosis
- **Diferenciales plausibles:** Diabetic ketoacidosis (ruled out by absence of ketones in male), sepsis (female — coexisting), septic shock, salicylate intoxication.
- **Notas críticas:**
  - **Male:** chart forces the system not to overlook metformin + CKD (classic precipitating factor).
  - **Female:** sepsis is the **cause** of the lactic acidosis — the system should not give "pneumonia" as Top-1 but recognize the lactic acidosis with sepsis as a triggering factor.

---

## 3. Hyperthyroidism

### 3.1 Consulta sin chart

```
Patient who for the past 3 months reports weight loss despite eating more, nervousness, fine tremor in the hands, palpitations, and excessive sweating. Tolerates heat poorly, tends to have diarrhea, and sleeps poorly. On examination presents tachycardia and a diffuse goiter. Also reports hair loss and menstrual disturbances.
```

### 3.2 Chart — Male Patient

- **Age:** 41
- **Sex:** M
- **Comorbidities:** generalized anxiety disorder (prior diagnosis)
- **Chief Complaint:** 8 kg weight loss in 2 months, palpitations, and insomnia
- **Vital Signs:** HR 112 · BP 138/72 · RR 18 · SpO2 98 · Temp 37.4
- **Physical Findings:** Warm and moist skin, fine distal tremor, bright stare with mild ocular protrusion, diffuse non-tender goiter, brisk reflexes.
- **Lab Results:** TSH < 0.01 mIU/L, free T4 3.8 ng/dL (elevated), free T3 9.2 pg/mL (elevated).
- **Imaging:** Thyroid ultrasound pending.
- **Current Medications:** sertraline 50 mg/day, alprazolam PRN
- **Allergies:** NKDA
- **Social History:** Smoker 1 pack/day, engineer, social alcohol
- **Family History:** Sister with Hashimoto's thyroiditis
- **Additional Notes:** Initially attributed the symptoms to an anxiety crisis and increased alprazolam, without improvement.

### 3.3 Chart — Female Patient

- **Age:** 29
- **Sex:** F
- **Comorbidities:** none
- **Chief Complaint:** Constant feeling of heat, weight loss, and irregular menstrual cycles
- **Vital Signs:** HR 108 · BP 128/68 · RR 16 · SpO2 99 · Temp 37.2
- **Physical Findings:** Symmetric diffuse goiter, mild bilateral exophthalmos, thin and warm skin, mild pretibial erythema.
- **Lab Results:** TSH < 0.01, elevated free T4, elevated free T3, positive TSI antibodies.
- **Imaging:** Thyroid ultrasound with enlarged and hypervascular gland.
- **Current Medications:** none
- **Allergies:** NKDA
- **Social History:** Graphic designer, non-smoker, occasional alcohol
- **Family History:** Mother with Graves' disease, grandmother with vitiligo
- **Additional Notes:** Pregnancy ruled out (β-hCG negative).

### 3.4 Salida esperada

- **Top-1 esperado:** Hyperthyroidism (Graves' disease for the female given the exophthalmos + TSI+; primary for the male)
- **Diferenciales plausibles:** Anxiety/panic disorder (in male, distractor due to history), pheochromocytoma, toxic multinodular goiter, factitious thyrotoxicosis.
- **Notas críticas:**
  - **Male:** chart with previous anxiety tests whether the system "sticks" with the psychiatric explanation or recognizes the endocrine pattern with suppressed TSH.
  - **Female:** textbook case — the challenge is for the Top-1 to be specific enough ("Graves' disease") and not stay at "hyperthyroidism" only.

---

## 4. Congenital Hypothyroidism

### 4.1 Consulta sin chart

```
3-week-old newborn brought to consultation by the mother because "he doesn't wake up to feed", cries little, and sucks with difficulty. Presents with prolonged jaundice, constipation since birth, umbilical hernia, and distended abdomen. On examination has a wide posterior fontanelle, hypotonia, and a prominent tongue. Neonatal screening was not performed due to home delivery.
```

### 4.2 Chart — Male Patient (infant)

- **Age:** 0 (28 days of life)
- **Sex:** M
- **Comorbidities:** none known
- **Chief Complaint:** Lethargy, weak suck, and constipation since birth
- **Vital Signs:** HR 102 · BP 70/40 · RR 32 · SpO2 97 · Temp 36.1
- **Physical Findings:** Persistent jaundice, wide posterior fontanelle, macroglossia, umbilical hernia, generalized hypotonia, hoarse cry.
- **Lab Results:** Total bilirubin 9 mg/dL (mainly indirect), normal Hb, TSH and T4 not performed.
- **Imaging:** None.
- **Current Medications:** none
- **Allergies:** unknown
- **Social History:** Home delivery attended by a midwife, did not receive neonatal metabolic screening
- **Family History:** Mother with postpartum thyroiditis in a previous pregnancy
- **Additional Notes:** Mother reports that the baby sleeps almost all day and must be awakened to feed.

### 4.3 Chart — Female Patient (infant)

- **Age:** 0 (2 months)
- **Sex:** F
- **Comorbidities:** none
- **Chief Complaint:** Poor weight gain and constipation
- **Vital Signs:** HR 110 · BP 72/42 · RR 36 · SpO2 98 · Temp 36.3
- **Physical Findings:** Dry and cold skin, hoarse cry, hypotonia, protruding tongue, prominent abdomen with umbilical hernia. Diminished reflexes.
- **Lab Results:** TSH from neonatal screening "abnormal" (verbal report from mother, no paper). Confirmation not performed.
- **Imaging:** None.
- **Current Medications:** none
- **Allergies:** unknown
- **Social History:** Exclusive breastfeeding
- **Family History:** No known thyroid history
- **Additional Notes:** Weight gain of 280 g in the past month (suboptimal).

### 4.4 Salida esperada

- **Top-1 esperado:** Congenital hypothyroidism
- **Diferenciales plausibles:** Down syndrome (due to hypotonia + macroglossia), Hirschsprung disease (due to constipation), prolonged neonatal jaundice from breast milk, biliary atresia.
- **Notas críticas:**
  - Case especially sensitive to **patient age** — the system must use the chart age to infer that this is the congenital form, not adult hypothyroidism.
  - The history of "maternal postpartum thyroiditis" in the male is a distractor that may push toward "transient neonatal hypothyroidism from maternal antibodies" — a valid differential but not the Top-1.

---

## 5. Hemolytic Anemia

### 5.1 Consulta sin chart

```
Patient consulting for progressive fatigue over the past 2 weeks, intense pallor, headache, and difficulty breathing on climbing stairs. In the last few days has noticed that the skin and eyes have turned yellowish and that the urine is very dark, almost like Coca-Cola. On examination shows palpable splenomegaly.
```

### 5.2 Chart — Male Patient

- **Age:** 22
- **Sex:** M
- **Comorbidities:** none
- **Chief Complaint:** Fatigue, jaundice, and dark urine for 5 days
- **Vital Signs:** HR 110 · BP 110/68 · RR 20 · SpO2 96 · Temp 36.9
- **Physical Findings:** Mucocutaneous pallor, scleral icterus, splenomegaly 3 cm below the costal margin, no lymphadenopathy.
- **Lab Results:** Hb 7.2 g/dL, MCV 96, reticulocytes 11%, LDH 980, indirect bilirubin 4.2 mg/dL, haptoglobin < 10, direct Coombs negative. G6PD pending.
- **Imaging:** Abdominal ultrasound with homogeneous splenomegaly.
- **Current Medications:** none regular. **4 days ago took trimethoprim-sulfamethoxazole** for a urinary tract infection.
- **Allergies:** NKDA
- **Social History:** Mediterranean origin, university student
- **Family History:** Maternal uncle with "rare anemia" since childhood
- **Additional Notes:** Ate fava beans at a family gathering last week.

### 5.3 Chart — Female Patient

- **Age:** 34
- **Sex:** F
- **Comorbidities:** systemic lupus erythematosus
- **Chief Complaint:** Weakness, pallor, and progressive exertional dyspnea
- **Vital Signs:** HR 116 · BP 102/64 · RR 22 · SpO2 95 · Temp 37.1
- **Physical Findings:** Intense pallor, mild jaundice, splenomegaly, no lymphadenopathy.
- **Lab Results:** Hb 6.8 g/dL, MCV 102, reticulocytes 13%, LDH 1100, indirect bilirubin 3.8, undetectable haptoglobin, direct Coombs POSITIVE (IgG).
- **Imaging:** Ultrasound with splenomegaly.
- **Current Medications:** hydroxychloroquine 200 mg/day, prednisone 5 mg/day
- **Allergies:** sulfa drugs
- **Social History:** Office worker
- **Family History:** Mother with rheumatoid arthritis
- **Additional Notes:** Reports recent joint flare and appearance of oral aphthae.

### 5.4 Salida esperada

- **Top-1 esperado:**
  - **Male:** Hemolytic anemia due to G6PD deficiency (favism / drug trigger).
  - **Female:** Autoimmune hemolytic anemia due to warm antibodies (IgG) associated with SLE.
- **Diferenciales plausibles:** Acute hepatitis (due to jaundice + dark urine), hemolytic uremic syndrome, anemia from occult bleeding, megaloblastic anemia.
- **Notas críticas:**
  - **Male:** chart data (Mediterranean origin, fava beans, sulfa drugs) are key diagnostic clues that without chart are NOT in the query. **Excellent case to compare RAG with vs. without chart.**
  - **Female:** Coombs+ and SLE appear only in the chart. Without chart, the system can only reach "hemolytic anemia"; with chart it should specify the autoimmune subtype.

---

## 6. Arteriosclerosis / Atherosclerosis

### 6.1 Consulta sin chart

```
Patient who for several months has experienced oppressive chest pain that appears when walking briskly or climbing hills and resolves with rest within a few minutes. Also notices cramps in the calves after walking two blocks that improve on stopping. Has noticed cold feet and difficulty healing a small wound on the big toe.
```

### 6.2 Chart — Male Patient

- **Age:** 68
- **Sex:** M
- **Comorbidities:** arterial hypertension, dyslipidemia, type 2 diabetes, mild COPD
- **Chief Complaint:** Exertional chest pain and intermittent claudication at 100 meters
- **Vital Signs:** HR 76 · BP 158/92 · RR 16 · SpO2 95 · Temp 36.6
- **Physical Findings:** Right carotid bruit, bilaterally diminished pedal pulses, superficial ulcer on right first toe, atrophic and shiny skin on the legs.
- **Lab Results:** LDL 168, HDL 32, triglycerides 220, glucose 152, HbA1c 7.8%, creatinine 1.2.
- **Imaging:** ECG with Q waves in inferior leads (old, not previously documented).
- **Current Medications:** enalapril 20 mg, metformin 1g BID, ASA 100 mg
- **Allergies:** NKDA
- **Social History:** Smoker 40 pack-years (active), sedentary, fatty diet
- **Family History:** Father MI at 55, brother with coronary bypass
- **Additional Notes:** Reports progressive erectile dysfunction over the past 2 years.

### 6.3 Chart — Female Patient

- **Age:** 72
- **Sex:** F
- **Comorbidities:** hypertension, dyslipidemia, rheumatoid arthritis
- **Chief Complaint:** Cramps in the legs when walking and occasional chest pain
- **Vital Signs:** HR 82 · BP 162/88 · RR 18 · SpO2 96 · Temp 36.5
- **Physical Findings:** Diminished posterior tibial pulses, abdominal bruit, palpebral xanthelasmas, joint deformities in hands.
- **Lab Results:** LDL 184, HDL 48, triglycerides 198, glucose 108, HbA1c 5.9%, ESR 38, CRP 12.
- **Imaging:** Carotid Doppler with bilateral plaques and 50% right-sided stenosis.
- **Current Medications:** losartan 50 mg, methotrexate 15 mg/week, folic acid, prednisone 5 mg
- **Allergies:** NKDA
- **Social History:** Ex-smoker (quit 10 years ago), walks little due to joint pain
- **Family History:** Mother with stroke at 70
- **Additional Notes:** In the last few months has noticed transient vision loss in the right eye ("as if a curtain came down").

### 6.4 Salida esperada

- **Top-1 esperado:** Atherosclerosis (with peripheral arterial disease + ischemic heart disease).
- **Diferenciales plausibles:** Mönckeberg arteriosclerosis (rule out — usually asymptomatic), Takayasu arteritis, thromboangiitis obliterans (Buerger), chronic venous insufficiency, spinal stenosis (neurogenic claudication).
- **Notas críticas:**
  - The system must **distinguish arteriosclerosis (general) from atherosclerosis (specific)** — the chart provides high LDL, risk factors and plaques, pointing to the atherosclerotic subtype.
  - **Female:** the amaurosis fugax episode suggests carotid embolus — the system should pick it up even though it is not in the question.
  - **Male:** old Q waves on ECG suggest silent MI — risk that the system drifts to "chronic ischemic heart disease" as Top-1 instead of the underlying disease.

---

## 7. Osteoarthritis

### 7.1 Consulta sin chart

```
Elderly patient with pain in both knees that appears when walking and going down stairs, improves with rest, and has been getting worse over the last 2 years. Reports brief morning stiffness (less than 15 minutes), crepitus on movement, and occasional swelling. No redness or fever.
```

### 7.2 Chart — Male Patient

- **Age:** 71
- **Sex:** M
- **Comorbidities:** grade II obesity (BMI 34), hypertension
- **Chief Complaint:** Mechanical pain in right knee of 3 years' evolution, now with varus deformity
- **Vital Signs:** HR 72 · BP 138/82 · RR 14 · SpO2 97 · Temp 36.5
- **Physical Findings:** Right knee with crepitus, limited range of motion (flexion 100°), evident varus deformity. No acute inflammatory signs.
- **Lab Results:** CRP 4 (normal), ESR 18, uric acid 6.2 (normal), RF negative.
- **Imaging:** Right knee X-ray with medial compartment joint space narrowing, marginal osteophytes, subchondral sclerosis, and small cysts.
- **Current Medications:** enalapril, paracetamol PRN
- **Allergies:** NKDA
- **Social History:** Retired bricklayer, history of heavy lifting work for 40 years
- **Family History:** Mother with hand osteoarthritis
- **Additional Notes:** Reports right tibial plateau fracture 25 years ago treated conservatively.

### 7.3 Chart — Female Patient

- **Age:** 64
- **Sex:** F
- **Comorbidities:** obesity, hypothyroidism under treatment
- **Chief Complaint:** Progressive pain and deformity in distal interphalangeal joints of the hands
- **Vital Signs:** HR 70 · BP 132/78 · RR 14 · SpO2 98 · Temp 36.4
- **Physical Findings:** Heberden's nodes at DIP, Bouchard's nodes at PIP, no warm synovitis. Knees with bilateral crepitus.
- **Lab Results:** CRP < 3, ESR 14, RF negative, anti-CCP negative, uric acid normal.
- **Imaging:** Hand X-ray with DIP joint space narrowing, osteophytes, no erosions.
- **Current Medications:** levothyroxine 75 mcg, paracetamol
- **Allergies:** NSAIDs (gastritis)
- **Social History:** Retired seamstress
- **Family History:** Mother and grandmother with "twisted fingers" in old age
- **Additional Notes:** Reports that her fingers look increasingly deformed but she has no prolonged morning stiffness.

### 7.4 Salida esperada

- **Top-1 esperado:** Osteoarthritis
- **Diferenciales plausibles:** Rheumatoid arthritis (ruled out by negative RF/anti-CCP, absence of synovitis), psoriatic arthritis, gout (ruled out by normal uric acid), chondrocalcinosis.
- **Notas críticas:**
  - The female chart is **very specific** for Heberden/Bouchard nodes — the system must name nodal (hand) osteoarthritis.
  - The male's fracture history points to post-traumatic osteoarthritis — a more specific diagnosis than "primary osteoarthritis".

---

## 8. Critical Cases with Negation

> These cases test whether the system correctly handles **explicit negation** in the query and chart. The test: the system must NOT use the negated symptom as evidence in favor.

### 8.1 Negation in query — Acidosis WITHOUT ketones (rules out DKA)

**Query:**
```
Diabetic patient with rapid deep breathing, abdominal pain, and confusion. Glucose is 140 mg/dL, there are NO ketones in urine or blood, and lactate is elevated at 7 mmol/L.
```

- **Chart:** see case 2.2 (male with metformin and CKD).
- **Top-1 esperado:** Lactic acidosis (associated with metformin + CKD).
- **Must NOT come out as Top-1:** Diabetic ketoacidosis.
- **Critical:** if the system answers DKA it completely ignores the negation of ketones.

### 8.2 Negation in query — Goiter WITHOUT hyperthyroidism

**Query:**
```
Woman with palpable diffuse goiter, fatigue, weight gain, cold intolerance, and dry skin. Does NOT present nervousness, does NOT have palpitations, does NOT have weight loss or tremor.
```

- **Top-1 esperado:** Hypothyroidism (probable Hashimoto's thyroiditis).
- **Must NOT come out:** Hyperthyroidism / Graves' disease (although "goiter" is a shared keyword).
- **Critical:** tests whether the system overweights the term "goiter" without considering the negations in the rest of the picture.

### 8.3 Negation in chart — Joint pain WITHOUT inflammatory signs

**Query:**
```
58-year-old woman with polyarticular hand pain of several years' evolution and stiffness. I want to rule out rheumatoid arthritis.
```

- **Chart (key):** normal CRP, normal ESR, RF negative, anti-CCP negative, **no synovitis or inflammatory signs**, Heberden's nodes present.
- **Top-1 esperado:** Nodal hand osteoarthritis.
- **Must NOT come out:** Rheumatoid arthritis.
- **Critical:** the physician **asks about RA**, but the negation of markers and inflammatory signs + bony nodes should lead the system to osteoarthritis.

### 8.4 Negation in query — Anemia WITHOUT bleeding or nutritional deficiency

**Query:**
```
22-year-old man with severe anemia, jaundice, and dark urine. There is NO digestive bleeding, NO melena or hematuria, normal diet with no iron or B12 deficiency.
```

- **Top-1 esperado:** Hemolytic anemia.
- **Must NOT come out:** Iron deficiency anemia, anemia from digestive bleeding, megaloblastic anemia.
- **Critical:** the negations rule out the most frequent causes — the system must reach the hemolytic cause.

---

## 9. Critical Cases with Ambiguity and Overlap

> Cases where two or more diseases in the corpus share symptoms and the system must discriminate.

### 9.1 Hyperthyroidism vs. Acromegaly (shared symptoms: sweating, goiter, fatigue)

**Query:**
```
Patient reporting profuse sweating, fatigue, joint pain, and palpable goiter. Has noticed that rings no longer fit and that the voice is deeper.
```

- **Top-1 esperado:** Acromegaly (the rings + deep voice are the differentiator).
- **Close differential:** Hyperthyroidism (due to sweating + goiter).
- **Notes:** Without a chart with IGF-1 or TSH, the system must lean toward acromegaly because of the specificity of "rings no longer fit" + voice.

### 9.2 Lactic acidosis vs. Ketoacidosis (shared Kussmaul respiration)

**Query:**
```
Type 2 diabetic on treatment, arrives with rapid deep breathing, abdominal pain, and dehydration. pH 7.18.
```

- **Without further data, both are plausible** — the system should list them as differentials and request ketones and lactate.
- **With chart 2.2 (metformin + CKD, no ketones, high lactate):** Top-1 lactic acidosis.
- **With alternative chart (glucose 480, ketonuria +++, normal lactate):** Top-1 diabetic ketoacidosis.
- **Critical:** ideal test to evaluate the weight of the chart in the decision.

### 9.3 Arteriosclerosis vs. Spinal stenosis (claudication)

**Query:**
```
Older man with leg pain on walking that improves with rest.
```

- **Without chart:** ambiguous between vascular and neurogenic claudication.
- **Vascular chart (case 6.2):** Top-1 atherosclerosis / PAD.
- **Alternative chart with pain that improves on leaning forward, preserved pulses:** should switch to spinal stenosis (NOT in corpus → case of system **insufficiency**, should trigger web).

### 9.4 Autoimmune hemolytic anemia vs. G6PD

**Query:**
```
Young person with anemia, jaundice, dark urine, and splenomegaly, no bleeding.
```

- **Without chart:** Top-1 generic "hemolytic anemia".
- **With chart 5.2 (Mediterranean origin + fava beans + sulfa drugs):** G6PD subtype.
- **With chart 5.3 (SLE + Coombs+):** warm antibody autoimmune subtype.
- **Critical:** the same "generic Top-1" must be specified according to the chart.

### 9.5 Congenital hypothyroidism vs. Down syndrome

**Query:**
```
6-week-old infant with hypotonia, large tongue, umbilical hernia, and prolonged jaundice.
```

- **Top-1 esperado por corpus:** Congenital hypothyroidism.
- **Real clinical differential:** Down syndrome (not in corpus — **insufficiency** case, web should trigger).
- **Critical:** tests that the system **does not force** an answer from the corpus if the picture has additional features (typical facial features, single palmar crease — which could be added to the chart to make the test more demanding).

---

## 10. Cases where the Chart may Influence Negatively

> These cases are designed so that the chart contains **realistic but distracting** information that could divert the system from the correct diagnosis.

### 10.1 Acromegaly chart with prominent goiter — risk of hyperthyroidism

**Query:**
```
52-year-old woman with generalized joint pain, paresthesias in the hands, and changes in voice.
```

- **Chart 1.3** (acromegaly female): includes **multinodular goiter, T2DM, normal TSH**.
- **Risk:** the system may give Top-1 subclinical hypothyroidism or multinodular goiter, instead of acromegaly.
- **Correct indicator:** coarse facies, large hands, galactorrhea, amenorrhea → acromegaly with pituitary compression.
- **Critical:** evaluates whether the chart **adds relevant signals** without **silencing the main picture**.

### 10.2 Hyperthyroidism chart with history of anxiety — risk of "psychiatric attribution"

**Query:**
```
41-year-old man with palpitations, insomnia, weight loss, and nervousness.
```

- **Chart 3.2:** prior anxiety, on sertraline and alprazolam.
- **Risk:** the system may lean toward "anxiety attack / panic disorder".
- **Correct indicator in chart:** TSH < 0.01, elevated free T4, diffuse goiter.
- **Critical:** the system must **prioritize biochemical evidence over psychiatric history**.

### 10.3 Lactic acidosis chart with infectious picture — risk of "Sepsis/Pneumonia" Top-1

**Query:**
```
38-year-old woman with vomiting, abdominal pain, and respiratory difficulty.
```

- **Chart 2.3:** fever, leukocytosis, high CRP, pulmonary infiltrate.
- **Risk:** Top-1 "bacterial pneumonia" or "sepsis" (none in corpus → web response).
- **Correct expected:** Top-1 lactic acidosis (with sepsis as underlying cause, mentioned as triggering factor).
- **Critical:** the system must distinguish **primary cause from the corpus (lactic acidosis)** vs. **precipitating factor**.

### 10.4 Hemolytic anemia chart with SLE — risk of "Lupus" as Top-1

**Query:**
```
34-year-old woman with pallor, weakness, and dyspnea.
```

- **Chart 5.3:** SLE under treatment, joint flare, oral aphthae.
- **Risk:** Top-1 "systemic lupus erythematosus" (not in corpus → less pertinent response).
- **Correct expected:** Top-1 autoimmune hemolytic anemia (hematologic manifestation of SLE).
- **Critical:** evaluates whether the system **classifies the main hematologic complaint** without "abandoning" it for the background comorbidity.

### 10.5 Osteoarthritis chart with RA suspicion raised by the physician

**Query:**
```
58-year-old woman with polyarticular hand pain. Could it be rheumatoid arthritis?
```

- **Chart 7.3:** RF negative, anti-CCP negative, normal CRP, Heberden's nodes.
- **Risk:** the system follows the physician and returns "rheumatoid arthritis" or "seronegative RA".
- **Correct expected:** Top-1 nodal hand osteoarthritis. Mention that RA is reasonably ruled out by serological negativity + absence of inflammatory signs.
- **Critical:** measures **resistance to the clinician's confirmation bias**.

### 10.6 Chart with medication that is CAUSE of the disease

**Query:**
```
22-year-old man with acute anemia and jaundice.
```

- **Chart 5.2:** recent intake of **trimethoprim-sulfamethoxazole** + fava bean consumption.
- **Risk:** the system lists generic hemolytic anemia without identifying the trigger.
- **Correct expected:** Top-1 G6PD deficiency hemolytic anemia triggered by sulfa drugs/favism.
- **Critical:** measures whether the system **integrates the chart medication as etiologic agent**, not just as context.

---

## 11. Additional Diseases

> These diseases are **not in `casos.txt`** but are highly clinically prevalent and useful to test the corpus coverage + activation of web mode when the corpus is insufficient. Clinical information based on standard guidelines (ADA, ESC, NICE, UpToDate).

---

### 11.1 Type 2 Diabetes Mellitus

#### Consulta sin chart

```
Patient who in the last few months has lost 6 kilos without trying, has great thirst, urinates several times during the night, and reports intermittent blurry vision. Skin infections have appeared that take a long time to heal, and there is tingling in the feet.
```

#### Chart — Male

- **Age:** 54
- **Sex:** M
- **Comorbidities:** central obesity, hypertension, mixed dyslipidemia
- **Chief Complaint:** Polyuria, polydipsia, and weight loss of 6 kg in 3 months
- **Vital Signs:** HR 84 · BP 148/90 · RR 14 · SpO2 98 · Temp 36.6
- **Physical Findings:** Cervical acanthosis nigricans, abdominal circumference 112 cm, interdigital candidiasis on feet, bilateral stocking hypoesthesia.
- **Lab Results:** Fasting glucose 198 mg/dL, HbA1c 9.2%, LDL 158, triglycerides 280, creatinine 1.1, microalbuminuria 80 mg/g.
- **Imaging:** Not relevant.
- **Current Medications:** losartan 50 mg
- **Allergies:** NKDA
- **Social History:** Salesperson, sedentary, consumes sugary drinks daily
- **Family History:** Father with T2DM and MI at 60
- **Additional Notes:** His wife reports that he snores and sometimes stops breathing (suspected OSA).

#### Chart — Female

- **Age:** 46
- **Sex:** F
- **Comorbidities:** polycystic ovary syndrome, non-alcoholic fatty liver disease
- **Chief Complaint:** Intense fatigue, recurrent urinary infections, and vulvar pruritus
- **Vital Signs:** HR 88 · BP 134/82 · RR 16 · SpO2 98 · Temp 36.7
- **Physical Findings:** BMI 32, acanthosis nigricans on neck and axillae, mild hirsutism.
- **Lab Results:** Glucose 168, HbA1c 8.1%, altered lipid profile, elevated transaminases (ALT 68).
- **Imaging:** Abdominal ultrasound with grade II hepatic steatosis.
- **Current Medications:** combined oral contraceptive (discontinued 1 year ago)
- **Allergies:** NKDA
- **Social History:** Works from home, diet high in refined carbohydrates
- **Family History:** Mother T2DM, maternal grandmother T2DM
- **Additional Notes:** History of gestational diabetes in her second pregnancy (8 years ago).

#### Salida esperada

- **Top-1 esperado:** Type 2 diabetes mellitus.
- **Diferenciales plausibles:** Type 1 diabetes (ruled out by age/context), LADA, secondary diabetes from Cushing's, drug-induced diabetes.
- **Notas críticas:**
  - Female: PCOS + prior gestational diabetes are clear risk factors — the system must integrate them.
  - **Likely Web activation** if the corpus does not cover T2DM.

---

### 11.2 Pulmonary Embolism

#### Consulta sin chart

```
Patient who suddenly presents with pain in the right side of the chest, difficulty breathing, and cough with some blood. Tachycardic with low saturation. A week ago underwent knee surgery and has been on bed rest.
```

#### Chart — Male

- **Age:** 62
- **Sex:** M
- **Comorbidities:** prostate cancer on hormonal therapy, hypertension
- **Chief Complaint:** Sudden dyspnea and pleuritic chest pain for 6 hours
- **Vital Signs:** HR 124 · BP 96/62 · RR 28 · SpO2 88 (room air) · Temp 37.4
- **Physical Findings:** Tachypnea, mild jugular venous distension, edema and pain in left calf with positive Homans' sign.
- **Lab Results:** D-dimer 5800 ng/mL, troponin I 0.08 (slightly elevated), blood gas with hypoxemia and respiratory alkalosis.
- **Imaging:** Chest angio-CT with filling defects in segmental arteries of the right lower lobe. Lower limb Doppler ultrasound with thrombosis in the left superficial femoral vein.
- **Current Medications:** leuprolide, enalapril
- **Allergies:** NKDA
- **Social History:** Retired, sedentary in the last month due to lower back pain
- **Family History:** Brother with DVT
- **Additional Notes:** Reports a 14-hour bus trip 4 days ago.

#### Chart — Female

- **Age:** 34
- **Sex:** F
- **Comorbidities:** none
- **Chief Complaint:** Progressive dyspnea and left chest pain of 12 hours, with one syncopal episode
- **Vital Signs:** HR 118 · BP 102/68 · RR 26 · SpO2 91 · Temp 37.0
- **Physical Findings:** Right leg with asymmetric edema and tenderness on calf palpation.
- **Lab Results:** D-dimer 4200, troponin and BNP slightly elevated.
- **Imaging:** Angio-CT with bilateral submassive pulmonary embolism. Echocardiogram: RV dilation.
- **Current Medications:** combined oral contraceptive
- **Allergies:** NKDA
- **Social History:** Smoker 10 cigarettes/day, transatlantic flight 2 days ago
- **Family History:** Mother with postpartum DVT
- **Additional Notes:** Partner reports she became pale and almost fainted on getting up from the toilet.

#### Salida esperada

- **Top-1 esperado:** Pulmonary embolism (PE).
- **Diferenciales plausibles:** Acute coronary syndrome, pneumonia with effusion, pneumothorax, aortic dissection, pericarditis.
- **Notas críticas:**
  - Combinations of **chart risk factors (contraceptive + flight + tobacco; or cancer + immobilization)** should raise the pre-test probability (implicit Wells criteria).

---

### 11.3 Addison's Disease (Primary Adrenal Insufficiency)

#### Consulta sin chart

```
Patient who for months has presented extreme fatigue, weight loss, vague abdominal pain, nausea, and dizziness on standing up. Has noticed that the skin has darkened, especially in folds, elbows, and gums. Craves salty foods.
```

#### Chart — Male

- **Age:** 36
- **Sex:** M
- **Comorbidities:** vitiligo
- **Chief Complaint:** Fatigue, postural hypotension, and 9 kg weight loss in 4 months
- **Vital Signs:** HR 102 (standing) · BP 92/56 (lying) → 78/48 (standing) · RR 16 · SpO2 98 · Temp 36.4
- **Physical Findings:** Hyperpigmentation in palmar creases, elbows, oral mucosa; scattered achromic patches (vitiligo).
- **Lab Results:** Na 128, K 5.6, glucose 68, urea normal, morning cortisol 2.1 µg/dL, ACTH 480 pg/mL (extremely elevated).
- **Imaging:** Abdominal CT with atrophic adrenal glands.
- **Current Medications:** none
- **Allergies:** NKDA
- **Social History:** Teacher, non-smoker
- **Family History:** Sister with Hashimoto's thyroiditis, aunt with type 1 diabetes
- **Additional Notes:** "Lipothymia" episode 1 month ago at a wedding.

#### Chart — Female

- **Age:** 48
- **Sex:** F
- **Comorbidities:** autoimmune hypothyroidism under treatment
- **Chief Complaint:** Nausea, vomiting, and abdominal pain of insidious onset, "I can't do this anymore" sensation
- **Vital Signs:** HR 110 · BP 86/52 · RR 18 · SpO2 97 · Temp 37.2
- **Physical Findings:** Hyperpigmented mucous membranes, tongue with dark edges, mild dehydration.
- **Lab Results:** Na 124, K 5.9, glucose 62, cortisol < 1, ACTH 720, positive anti-21-hydroxylase antibodies.
- **Imaging:** Atrophic adrenals on CT.
- **Current Medications:** levothyroxine 100 mcg
- **Allergies:** NKDA
- **Social History:** Administrative assistant
- **Family History:** Mother with celiac disease, brother with T1D
- **Additional Notes:** Episode of severe hypotension during gastroenteritis 2 weeks ago (suspected adrenal crisis).

#### Salida esperada

- **Top-1 esperado:** Addison's disease (primary autoimmune adrenal insufficiency, in the context of autoimmune polyglandular syndrome type II).
- **Diferenciales plausibles:** Secondary adrenal insufficiency (ruled out by high ACTH), major depression, anorexia, chronic sepsis, hemochromatosis.
- **Notas críticas:**
  - Hyperpigmentation + low Na + high K + high ACTH = highly specific pattern.
  - The history of vitiligo / Hashimoto orients toward autoimmune etiology (polyglandular syndrome).

---

### 11.4 Cushing's Syndrome

#### Consulta sin chart

```
Patient with weight gain over the past 18 months concentrated in the face and trunk, with thinning arms and legs. A rounded reddish face has appeared, hump on the back, wide red-violet stretch marks on the abdomen, easy bruising, muscle weakness in the thighs, and elevated blood pressure. The patient also reports irregular menstrual cycles and increased facial hair.
```

#### Chart — Male

- **Age:** 44
- **Sex:** M
- **Comorbidities:** difficult-to-control hypertension, newly diagnosed diabetes, osteoporosis at young age
- **Chief Complaint:** Central weight gain, weakness when climbing stairs, and skin changes
- **Vital Signs:** HR 86 · BP 168/102 · RR 14 · SpO2 97 · Temp 36.5
- **Physical Findings:** Moon facies, facial plethora, dorsal hump, atrophy of proximal musculature, violet abdominal striae > 1 cm, forearm bruises.
- **Lab Results:** 24h urinary free cortisol elevated x4, elevated nocturnal salivary cortisol, 1 mg dexamethasone suppression test without suppression, ACTH 85 pg/mL.
- **Imaging:** Pituitary MRI with 6 mm microadenoma.
- **Current Medications:** amlodipine, hydrochlorothiazide, metformin
- **Allergies:** NKDA
- **Social History:** Accountant
- **Family History:** Unremarkable
- **Additional Notes:** 6 months ago stress fracture in foot without clear trauma.

#### Chart — Female

- **Age:** 52
- **Sex:** F
- **Comorbidities:** bronchial asthma
- **Chief Complaint:** Weight gain, weakness, and facial changes
- **Vital Signs:** HR 80 · BP 152/94 · RR 16 · SpO2 98 · Temp 36.6
- **Physical Findings:** Cushingoid, facial hirsutism, acne, red striae, multiple ecchymoses.
- **Lab Results:** Elevated urinary free cortisol, suppressed ACTH (<5), suppression test without response.
- **Imaging:** Abdominal CT with 3.5 cm right adrenal mass.
- **Current Medications:** **chronic prednisone 20 mg/day** for severe asthma for 3 years, salbutamol, inhaled budesonide.
- **Allergies:** NSAIDs
- **Social History:** Housewife
- **Family History:** Unremarkable
- **Additional Notes:** *Real distractor:* the patient uses chronic corticosteroids, but biochemical studies show suppressed ACTH with adrenal mass → **endogenous adrenal Cushing's coexisting with iatrogenic Cushing's**.

#### Salida esperada

- **Top-1 esperado:**
  - **Male:** Cushing's disease (ACTH-dependent pituitary adenoma).
  - **Female:** Iatrogenic Cushing's syndrome (from corticosteroids) — but the finding of the adrenal mass with suppressed ACTH should alert to endogenous adrenal Cushing's.
- **Diferenciales plausibles:** Metabolic syndrome, pseudo-Cushing from depression/alcohol, hypothyroidism, simple obesity with hypertension, congenital adrenal hyperplasia.
- **Notas críticas:**
  - Female: especially complex case to evaluate whether the system **differentiates the two coexisting etiologies**.

---

### 11.5 Parkinson's Disease

#### Consulta sin chart

```
68-year-old patient who over the last two years has developed a tremor in one hand that appears at rest and disappears with movement, slowness of gait with short steps, difficulty initiating gait, and rigidity in right arm. His wife reports that he has become expressionless, speaks more softly, and drools at night. He has also noticed loss of smell.
```

#### Chart — Male

- **Age:** 68
- **Sex:** M
- **Comorbidities:** hypertension, mild depression in follow-up
- **Chief Complaint:** Right-hand tremor and progressive slowing of 2 years
- **Vital Signs:** HR 72 · BP 138/82 (lying) → 116/72 (standing) · RR 14 · SpO2 97 · Temp 36.6
- **Physical Findings:** Bradykinesia, hypomimia, right resting tremor (4-6 Hz), right cogwheel rigidity, short-stepped gait, loss of right arm swing. Non-inhibited glabellar reflex.
- **Lab Results:** Basic biochemistry normal, TSH normal, B12 normal.
- **Imaging:** Brain MRI with nonspecific atrophy, no significant ischemic lesions. DaT-SCAN: left putamen hypocaptation.
- **Current Medications:** enalapril, sertraline 50 mg
- **Allergies:** NKDA
- **Social History:** Retired, non-smoker, occasional alcohol
- **Family History:** Father with "tremor in old age", brother without history
- **Additional Notes:** His wife reports that he has vivid dreams in which he "acts out" what he dreams (suspected RBD), and that he has lost his sense of smell for years.

#### Chart — Female

- **Age:** 73
- **Sex:** F
- **Comorbidities:** osteoporosis, chronic constipation
- **Chief Complaint:** Falls and difficulty writing
- **Vital Signs:** HR 70 · BP 128/76 · RR 14 · SpO2 98 · Temp 36.5
- **Physical Findings:** Evident micrographia, bradykinesia, axial rigidity, flexed posture, festinating gait. No oculomotor involvement.
- **Lab Results:** Normal.
- **Imaging:** Brain CT without lesions; positive DaT-SCAN.
- **Current Medications:** calcium + vit D, weekly alendronate, lactulose
- **Allergies:** NKDA
- **Social History:** Lives alone, retired seamstress
- **Family History:** No neurological history
- **Additional Notes:** Severe constipation for 10 years (classic prodromal symptom).

#### Salida esperada

- **Top-1 esperado:** Idiopathic Parkinson's disease.
- **Diferenciales plausibles:** Vascular parkinsonism, multiple system atrophy (MSA), progressive supranuclear palsy (PSP), drug-induced parkinsonism, essential tremor.
- **Notas críticas:**
  - RBD + anosmia + constipation are **characteristic premotor symptoms** — if the system integrates them, it should prioritize Parkinson's over essential tremor.

---

### 11.6 Multiple Sclerosis

#### Consulta sin chart

```
Young woman who 6 months ago presented vision loss in one eye with pain on moving it, which recovered in weeks. Now consults because for 10 days she has had tingling and weakness in the right leg that is worsening, electric shock sensation in the back on flexing the neck, and problems controlling the bladder.
```

#### Chart — Male

- **Age:** 32
- **Sex:** M
- **Comorbidities:** none
- **Chief Complaint:** Diplopia and gait instability of 2 weeks
- **Vital Signs:** HR 76 · BP 122/78 · RR 14 · SpO2 99 · Temp 36.7
- **Physical Findings:** Left internuclear ophthalmoplegia, 4/4 hyperreflexia in right lower limb, positive right Babinski, positive Lhermitte's sign.
- **Lab Results:** Normal blood count, normal B12, negative HIV, normal thyroid function.
- **Imaging:** Brain and spinal MRI with multiple T2 hyperintense periventricular, juxtacortical, and corpus callosum lesions ("Dawson's fingers"). Active gadolinium-enhancing lesion.
- **Current Medications:** none
- **Allergies:** NKDA
- **Social History:** Engineer, lives at northern latitude (low vitamin D due to lifestyle)
- **Family History:** Maternal aunt with "neurological disease that left her in a wheelchair"
- **Additional Notes:** CSF with positive oligoclonal bands, not present in serum.

#### Chart — Female

- **Age:** 28
- **Sex:** F
- **Comorbidities:** none
- **Chief Complaint:** Paresthesias in right hemibody and bladder dysfunction
- **Vital Signs:** HR 78 · BP 118/72 · RR 14 · SpO2 99 · Temp 36.6
- **Physical Findings:** Right hemibody tactile hypoesthesia below T8, mild ataxia, urinary urgency.
- **Lab Results:** Normal biochemistry, negative anti-AQP4, negative anti-MOG, positive oligoclonal bands in CSF.
- **Imaging:** MRI with demyelinating lesions disseminated in time and space.
- **Current Medications:** oral contraceptive
- **Allergies:** NKDA
- **Social History:** Designer, non-smoker
- **Family History:** No known autoimmune diseases
- **Additional Notes:** 6 months ago optic neuritis of the left eye that partially recovered.

#### Salida esperada

- **Top-1 esperado:** Relapsing-remitting multiple sclerosis.
- **Diferenciales plausibles:** Neuromyelitis optica (NMO/Devic — ruled out by negative anti-AQP4), acute disseminated encephalomyelitis (ADEM), anti-MOG disease, neurosarcoidosis, B12 deficiency, CNS vasculitis.
- **Notas críticas:**
  - Lhermitte + optic neuritis + MRI lesions with Dawson's fingers + oligoclonal bands = McDonald criteria for MS.

---

### 11.7 Systemic Lupus Erythematosus

#### Consulta sin chart

```
Young woman with extreme fatigue, joint pain in hands and wrists without deformity, reddish rash on cheeks that spares the nasolabial folds and worsens with sun, oral aphthae, hair loss, episodes of pallor and pain in the fingers when cold. Also reports chest pain that improves on leaning forward.
```

#### Chart — Male

- **Age:** 29
- **Sex:** M
- **Comorbidities:** none
- **Chief Complaint:** Polyarthritis, fever, and weight loss for 2 months
- **Vital Signs:** HR 96 · BP 138/86 · RR 18 · SpO2 97 · Temp 37.9
- **Physical Findings:** Tenuous malar erythema, painless palatal ulcers, mild right pleural effusion, malleolar edema.
- **Lab Results:** ANA 1:1280 homogeneous pattern, high positive anti-dsDNA, positive anti-Sm, low C3/C4, Coombs+, proteinuria 2.1 g/24h, sediment with red cell casts.
- **Imaging:** Chest X-ray with right pleural effusion. Echocardiogram with mild pericardial effusion.
- **Current Medications:** none
- **Allergies:** NKDA
- **Social History:** PhD student
- **Family History:** Sister with autoimmune thyroiditis
- **Additional Notes:** Pending renal biopsy (suspected class IV lupus nephritis).

#### Chart — Female

- **Age:** 26
- **Sex:** F
- **Comorbidities:** none
- **Chief Complaint:** Facial rash, joint pain, and fatigue of 4 months
- **Vital Signs:** HR 90 · BP 124/78 · RR 16 · SpO2 98 · Temp 37.4
- **Physical Findings:** Malar erythema in "butterfly wings" sparing nasolabial folds, diffuse alopecia, triphasic Raynaud phenomenon in hands.
- **Lab Results:** ANA 1:640, positive anti-dsDNA, positive anti-Ro, low C3, leukopenia 3200, lymphopenia, platelets 95,000.
- **Imaging:** No findings.
- **Current Medications:** combined oral contraceptive (to discontinue)
- **Allergies:** sulfa drugs
- **Social History:** Designer, exposed to intense sun due to hobby
- **Family History:** Aunt with rheumatoid arthritis
- **Additional Notes:** History of 2 first-trimester miscarriages (rule out associated APS: lupus anticoagulant pending).

#### Salida esperada

- **Top-1 esperado:** Systemic lupus erythematosus (EULAR/ACR 2019 criteria).
- **Diferenciales plausibles:** Rheumatoid arthritis, dermatomyositis, mixed connective tissue disease, Sjögren's syndrome, drug-induced lupus.
- **Notas críticas:**
  - Male: atypical presentation due to gender — the system **should not** rule out SLE because the patient is male (represents ~10% of cases).

---

### 11.8 Congestive Heart Failure

#### Consulta sin chart

```
Patient who in the last few weeks presents difficulty breathing on increasingly smaller efforts, must sleep with several pillows because when lying down he suffocates and wakes up at night short of breath that improves on sitting. Has swollen ankles, has gained 4 kilos without dietary changes, and notices palpitations.
```

#### Chart — Male

- **Age:** 70
- **Sex:** M
- **Comorbidities:** MI 5 years ago with LAD stent, hypertension, T2DM, permanent atrial fibrillation
- **Chief Complaint:** Small-effort dyspnea, 3-pillow orthopnea, and edema
- **Vital Signs:** HR 104 (irregular) · BP 102/68 · RR 24 · SpO2 92 · Temp 36.5
- **Physical Findings:** Jugular venous distension, bibasal crackles, pitting edema up to the knees, painful hepatomegaly, positive hepatojugular reflux.
- **Lab Results:** BNP 1850 pg/mL, negative troponin, creatinine 1.7, Na 132, K 4.4.
- **Imaging:** Chest X-ray with cardiomegaly, vascular redistribution, and bilateral pleural effusion. Echocardiogram: LVEF 28%, dilation of left chambers, moderate MR.
- **Current Medications:** ASA, atorvastatin, carvedilol, enalapril, furosemide, dapagliflozin, apixaban
- **Allergies:** NKDA
- **Social History:** Retired, ex-smoker
- **Family History:** Father HF, brother MI
- **Additional Notes:** Reports having stopped taking furosemide 1 week ago because "I had to go to the bathroom too much".

#### Chart — Female

- **Age:** 78
- **Sex:** F
- **Comorbidities:** long-standing hypertension, obesity, T2DM, stage 3 CKD
- **Chief Complaint:** Progressive dyspnea and increased abdominal girth
- **Vital Signs:** HR 88 · BP 168/92 · RR 22 · SpO2 93 · Temp 36.4
- **Physical Findings:** Bibasal crackles, edema, mild ascites, visible JVD.
- **Lab Results:** BNP 720, creatinine 1.6, normal thyroid function.
- **Imaging:** Echocardiogram: **preserved LVEF 60%**, severe LV hypertrophy, grade III diastolic dysfunction, LA dilation.
- **Current Medications:** losartan, amlodipine, metformin, spironolactone
- **Allergies:** NKDA
- **Social History:** Lives with her daughter
- **Family History:** Maternal hypertension
- **Additional Notes:** Case of HF with preserved ejection fraction (HFpEF), an increasingly frequent pattern in older women with hypertension.

#### Salida esperada

- **Top-1 esperado:** Heart failure (HFrEF in the male, HFpEF in the female).
- **Diferenciales plausibles:** Exacerbated COPD, chronic pulmonary embolism, anemia, hypothyroidism, nephrotic syndrome, liver cirrhosis.
- **Notas críticas:**
  - The system must **distinguish HFrEF vs HFpEF** according to chart LVEF — different therapeutic implications.

---

### 11.9 Acute Pancreatitis

#### Consulta sin chart

```
Patient who after a copious meal with alcohol presents intense pain in the epigastrium radiating to the back in a belt pattern, accompanied by nausea, persistent vomiting, and abdominal distension. The pain improves on leaning forward and worsens on lying down.
```

#### Chart — Male

- **Age:** 52
- **Sex:** M
- **Comorbidities:** dyslipidemia (elevated triglycerides), chronic alcoholism
- **Chief Complaint:** Epigastric pain radiating to back, vomiting, and fever of 18 hours
- **Vital Signs:** HR 118 · BP 96/58 · RR 24 · SpO2 94 · Temp 38.4
- **Physical Findings:** Distended and tender abdomen in epigastrium, incipient Grey-Turner sign, no frank peritoneal defense. Cullen periumbilical ecchymosis absent.
- **Lab Results:** Amylase 1840, lipase 4200, leukocytes 18,000, calcium 7.2, LDH 480, AST 320, glucose 220, triglycerides 1,850 mg/dL, CRP 280.
- **Imaging:** Abdominal CT with enlarged pancreas, necrosis areas < 30%, peripancreatic fluid (Balthazar D).
- **Current Medications:** none regular
- **Allergies:** NKDA
- **Social History:** Drinker of 6-8 beers/day for 20 years, smoker
- **Family History:** Unremarkable
- **Additional Notes:** Previous episode of mild pancreatitis 2 years ago.

#### Chart — Female

- **Age:** 58
- **Sex:** F
- **Comorbidities:** known cholelithiasis (not operated)
- **Chief Complaint:** Sudden postprandial abdominal pain in epigastrium, vomiting
- **Vital Signs:** HR 102 · BP 122/78 · RR 18 · SpO2 96 · Temp 37.6
- **Physical Findings:** Mild jaundice, tenderness on palpation in right hypochondrium and epigastrium, positive Murphy's sign.
- **Lab Results:** Amylase 1620, lipase 3800, total bilirubin 4.8 (direct 3.6), ALT 380, AST 290, ALP 420, GGT 380, leukocytes 14,500.
- **Imaging:** Abdominal ultrasound with lithiasic gallbladder, dilated bile duct (8 mm), suspected choledocholithiasis. CT with edematous pancreas without necrosis.
- **Current Medications:** losartan
- **Allergies:** NKDA
- **Social History:** Non-drinker, non-smoker
- **Family History:** Mother cholecystectomized
- **Additional Notes:** Non-drinker — the pancreatitis is of **biliary origin**.

#### Salida esperada

- **Top-1 esperado:** Acute pancreatitis (alcoholic/hypertriglyceridemic in male; biliary in female).
- **Diferenciales plausibles:** Perforated peptic ulcer, acute cholecystitis, inferior myocardial infarction, mesenteric ischemia, aortic aneurysm.
- **Notas críticas:**
  - The system must **identify the etiology** according to the chart (alcohol/TG vs. biliary) — affects management (urgent ERCP in biliary).
  - Female: pain radiating to right shoulder could be confused with pure cholecystitis — extremely high lipase defines pancreatitis.

---

### 11.10 Pheochromocytoma

#### Consulta sin chart

```
Patient with paroxysmal episodes of intense headache, profuse sweating, and palpitations, associated with very high spikes in blood pressure that come and go. Between episodes feels well. Reports anxiety, weight loss, and pallor during the crises. One episode was triggered while straining in the bathroom.
```

#### Chart — Male

- **Age:** 42
- **Sex:** M
- **Comorbidities:** difficult-to-control hypertension (3 drugs without control)
- **Chief Complaint:** Paroxysmal headaches with BP figures of 220/130 mmHg
- **Vital Signs (intercrisis):** HR 88 · BP 154/96 · RR 14 · SpO2 98 · Temp 36.7
- **Vital Signs (crisis):** HR 138 · BP 230/132 · profuse diaphoresis
- **Physical Findings:** Pallor during the crisis, no palpable abdominal masses, fundus with grade II hypertensive retinopathy.
- **Lab Results:** Plasma free metanephrines 3.8 nmol/L (very elevated), 24h urinary normetanephrines x6 the limit, elevated chromogranin A.
- **Imaging:** Abdominal CT with 4.5 cm heterogeneous right adrenal mass. MIBG with intense uptake in the mass.
- **Current Medications:** amlodipine, losartan, hydrochlorothiazide (discontinue beta-blocker due to risk of crisis)
- **Allergies:** NKDA
- **Social History:** Businessman
- **Family History:** Father with hypertension. No known MEN or von Hippel-Lindau history (but pending genetic study).
- **Additional Notes:** Episode of acute pulmonary edema 3 months ago attributed to "hypertensive crisis".

#### Chart — Female

- **Age:** 38
- **Sex:** F
- **Comorbidities:** none known; family history of cerebellar hemangioblastomas
- **Chief Complaint:** Episodes of palpitations, headache, and sweating with sudden hypertension
- **Vital Signs (intercrisis):** HR 80 · BP 132/82 · RR 14 · SpO2 99 · Temp 36.5
- **Physical Findings:** No focal signs, fundus with retinal angiomas (von Hippel-Lindau).
- **Lab Results:** Elevated plasma metanephrines, glucose 138 in crisis.
- **Imaging:** Abdominal MRI with small bilateral adrenal masses (1.8 and 2.2 cm). Brain MRI with cerebellar hemangioblastoma.
- **Current Medications:** none
- **Allergies:** NKDA
- **Social History:** Researcher
- **Family History:** Father and brother with confirmed von Hippel-Lindau disease
- **Additional Notes:** Genetic study confirms VHL mutation — bilateral pheochromocytoma in the syndromic context.

#### Salida esperada

- **Top-1 esperado:** Pheochromocytoma.
- **Diferenciales plausibles:** Resistant essential hypertension, panic crisis, hyperthyroidism, carcinoid syndrome, cocaine/amphetamine abuse, hypoglycemia with adrenergic response.
- **Notas críticas:**
  - Female: case in the context of **von Hippel-Lindau** — the system must recognize that bilateral pheochromocytomas in young patients mandate searching for a genetic syndrome.
  - Important distractor: **panic disorder** shares symptoms — the chart should lean toward pheochromocytoma due to metanephrines and imaging.

---

## 12. Extended Disease Coverage

> Additional cases following the **minimal structure** (query without chart + expected output only). Numbered §12.1 to §12.65. These cases broaden the disease coverage and are intended primarily for automated evaluation against the qrels.

---

### 12.1 Appendicitis

#### 12.1.1 Consulta sin chart

```
Young patient consulting for abdominal pain that started around the navel and within several hours moved to the lower right side of the abdomen. Reports marked loss of appetite, nausea, and one episode of vomiting, with low-grade fever since the previous night. The pain increases when walking or coughing, and on examination there is localized guarding in the right iliac fossa. Does not report significant diarrhea or clear urinary symptoms.
```

#### 12.1.4 Salida esperada

- **Top-1 esperado:** Appendicitis
- **Diferenciales plausibles:** Gastroenteritis, mesenteric adenitis, right renal colic, ectopic pregnancy, pelvic inflammatory disease.
- **Notas críticas:**
  - Case useful for evaluating migration of periumbilical pain to the right iliac fossa.
  - The absence of significant diarrhea helps not to overweight gastroenteritis.
  - In women of childbearing age, the system should keep gynecological differentials without displacing the classic abdominal pattern.

---

### 12.2 Cholecystitis

#### 12.2.1 Consulta sin chart

```
Patient consulting for constant pain in the upper right side of the abdomen, started after a fatty meal. The pain radiates to the back and right shoulder, accompanied by nausea, vomiting, and fever. On examination, the pain increases on deep inspiration while palpating the right costal margin. Reports history of similar but briefer episodes after copious meals.
```

#### 12.2.4 Salida esperada

- **Top-1 esperado:** Cholecystitis
- **Diferenciales plausibles:** Simple biliary colic, pancreatitis, hepatitis, perforated peptic ulcer, right pyelonephritis.
- **Notas críticas:**
  - Persistent pain with fever must be differentiated from uncomplicated biliary colic.
  - The radiation to the right shoulder and pain on deep inspiration are relevant signs.
  - May overlap with biliary pancreatitis; the system should suggest lipase and ultrasound if it responded clinically.

---

### 12.3 Pneumonia

#### 12.3.1 Consulta sin chart

```
Patient who for the past 4 days presents high fever, chills, cough with yellowish expectoration, and chest pain that worsens on deep breathing. Reports difficulty breathing when walking inside the house and intense fatigue. On auscultation, crackles are described localized in the right lung base. Has no oppressive retrosternal pain or leg edema.
```

#### 12.3.4 Salida esperada

- **Top-1 esperado:** Pneumonia
- **Diferenciales plausibles:** Bronchitis, influenza, COVID-19, pulmonary embolism, decompensated heart failure.
- **Notas críticas:**
  - The pattern fever + productive cough + pleuritic pain + localized crackles must outweigh nonspecific respiratory diagnoses.
  - The negation of oppressive pain and edema helps not to shift the case toward cardiac causes.
  - Useful for testing whether the system distinguishes focal pulmonary infection from viral bronchitis.

---

### 12.4 Tuberculosis

#### 12.4.1 Consulta sin chart

```
Patient consulting for cough of more than one month of evolution, initially dry and then with expectoration, with occasional episodes of blood in the sputum. Reports intense night sweats, low-grade afternoon fever, unintentional weight loss, and persistent fatigue. Has recently lived with a person who coughed a lot and did not receive treatment. Does not describe sudden onset or intense pleuritic pain.
```

#### 12.4.4 Salida esperada

- **Top-1 esperado:** Tuberculosis
- **Diferenciales plausibles:** Chronic pneumonia, lung cancer, bronchiectasis, pulmonary mycosis, COPD with exacerbations.
- **Notas críticas:**
  - The chronicity of cough and constitutional symptoms are key.
  - Hemoptysis should not automatically lead to cancer if there is afternoon fever, night sweats, and epidemiological contact.
  - Case useful to trigger web retrieval if the local corpus does not cover chronic infections.

---

### 12.5 Asthma

#### 12.5.1 Consulta sin chart

```
Patient with recurrent episodes of shortness of breath, chest tightness, and wheezing on breathing that appear mainly at night or during exercise. Reports dry cough on exposure to dust and cold air, with periods between crises in which feels practically normal. During the current episode diffuse wheezing is auscultated and breathing improves partially after using a bronchodilator inhaler. Does not report fever or purulent expectoration.
```

#### 12.5.4 Salida esperada

- **Top-1 esperado:** Asthma
- **Diferenciales plausibles:** COPD, bronchitis, heart failure, vocal cord dysfunction, anxiety with hyperventilation.
- **Notas críticas:**
  - Episodic variability and environmental triggers are differentiators.
  - Improvement with bronchodilator supports reversible obstruction.
  - The absence of fever and purulent sputum reduces the probability of respiratory infection as Top-1.

---

### 12.6 Chronic Obstructive Pulmonary Disease

#### 12.6.1 Consulta sin chart

```
Older patient with significant smoking history reporting daily cough for years, with morning expectoration and progressive shortness of breath. In the last months gets tired when climbing one floor and notices wheezing in the chest, but does not present completely reversible crises or long intervals without symptoms. Has had several winter episodes in which the amount of phlegm increases and needs to go to the emergency room. On examination, prolonged expiration and mild use of accessory muscles are appreciated.
```

#### 12.6.4 Salida esperada

- **Top-1 esperado:** Chronic obstructive pulmonary disease
- **Diferenciales plausibles:** Asthma, bronchiectasis, heart failure, lung cancer, pulmonary fibrosis.
- **Notas críticas:**
  - The smoking history and chronic progression must distinguish it from asthma.
  - Chronic productive cough with progressive dyspnea is the core of the case.
  - The system should avoid answering only "bronchitis" if the picture suggests chronic obstructive disease.

---

### 12.7 Acute Myocardial Infarction

#### 12.7.1 Consulta sin chart

```
Patient presenting with intense oppressive pain in the center of the chest, started at rest 45 minutes ago, with radiation to the left arm and jaw. Accompanied by cold sweat, nausea, sense of impending doom, and shortness of breath. The pain does not improve with rest or with antacids. Has history of hypertension, smoking, and elevated cholesterol.
```

#### 12.7.4 Salida esperada

- **Top-1 esperado:** Acute myocardial infarction
- **Diferenciales plausibles:** Unstable angina, aortic dissection, pulmonary embolism, pericarditis, gastroesophageal reflux.
- **Notas críticas:**
  - Prolonged pain at rest with autonomic symptoms must be differentiated from stable angina.
  - Antacids without relief help not to prioritize dyspepsia.
  - High-criticality case: the system must recognize urgency and not limit itself to general atherosclerotic disease.

---

### 12.8 Stroke

#### 12.8.1 Consulta sin chart

```
Patient who suddenly presented deviation of the labial commissure, difficulty speaking, and weakness in the right arm and leg. The family reports that he was well one hour earlier and suddenly started slurring words and could not hold a cup. There were no convulsive movements or prolonged loss of consciousness. Has history of hypertension and atrial fibrillation.
```

#### 12.8.4 Salida esperada

- **Top-1 esperado:** Stroke
- **Diferenciales plausibles:** Transient ischemic attack, intracerebral hemorrhage, epileptic seizure with Todd's paralysis, hypoglycemia, hemiplegic migraine.
- **Notas críticas:**
  - Sudden onset with lateralized focal deficit is the central pattern.
  - Atrial fibrillation functions as a cardioembolic etiologic signal.
  - The negation of seizures helps not to prioritize epilepsy as Top-1.

---

### 12.9 Meningitis

#### 12.9.1 Consulta sin chart

```
Patient who comes for high fever, very intense headache, and marked neck stiffness of acute onset. Reports vomiting, photophobia, and progressive drowsiness, with difficulty answering simple questions. On examination, poor general condition and pain on neck flexion are observed. There is no clear respiratory focus to explain the fever.
```

#### 12.9.4 Salida esperada

- **Top-1 esperado:** Meningitis
- **Diferenciales plausibles:** Encephalitis, severe migraine, subarachnoid hemorrhage, sepsis without focus, brain abscess.
- **Notas críticas:**
  - The triad fever + intense headache + neck stiffness must be highly weighted.
  - The altered sensorium increases severity.
  - Must avoid being confused with migraine due to photophobia if there is fever and meningeal rigidity.

---

### 12.10 Migraine

#### 12.10.1 Consulta sin chart

```
Patient with repeated episodes of intense pulsating pain on one side of the head, lasting several hours and forcing her to lie down in a dark room. Before or during some crises notices blurred vision or flashing lights that disappear afterwards. During the pain presents nausea, intolerance to light and noise, and worsens when climbing stairs. Between episodes is completely asymptomatic.
```

#### 12.10.4 Salida esperada

- **Top-1 esperado:** Migraine
- **Diferenciales plausibles:** Tension headache, cluster headache, transient ischemic attack, brain tumor, meningitis.
- **Notas críticas:**
  - Unilateral pulsating headache with nausea, photophobia, and phonophobia is the differentiator.
  - The absence of persistent neurological deficit helps not to prioritize stroke.
  - The recurrence with complete recovery between crises should outweigh structural causes.

---

### 12.11 Epilepsy

#### 12.11.1 Consulta sin chart

```
Patient who has presented several unprovoked episodes in which loses consciousness, falls to the ground, and has rhythmic movements of arms and legs for one or two minutes. Afterwards remains confused, drowsy, and with muscle pain, without remembering what happened. On one occasion bit the lateral edge of the tongue and presented loss of urine. No fever or recent consumption of alcohol or drugs was documented.
```

#### 12.11.4 Salida esperada

- **Top-1 esperado:** Epilepsy
- **Diferenciales plausibles:** Vasovagal syncope, psychogenic non-epileptic seizures, hypoglycemia, intoxication, cardiac arrhythmia.
- **Notas críticas:**
  - Recurrence of unprovoked crises is more important than an isolated episode.
  - Lateral tongue bite and postictal phase help to distinguish from syncope.
  - The negation of fever avoids orienting toward febrile seizure or acute infection.

---

### 12.12 Celiac Disease

#### 12.12.1 Consulta sin chart

```
Patient who for months has presented chronic diarrhea, abdominal distension, gas, fatigue, and weight loss. Reports persistent anemia that does not improve well with iron and frequent oral aphthae. The symptoms worsen when consuming bread, pasta, or flour-based products, and improve partially when avoiding them. Has a first-degree relative with autoimmune thyroid disease.
```

#### 12.12.4 Salida esperada

- **Top-1 esperado:** Celiac disease
- **Diferenciales plausibles:** Irritable bowel syndrome, inflammatory bowel disease, lactose intolerance, giardiasis, iron deficiency anemia from occult bleeding.
- **Notas críticas:**
  - The combination of malabsorption, anemia, and relationship with gluten should guide the ranking.
  - Should not be classified only as functional diarrhea if there is weight loss and anemia.
  - The autoimmune family history increases plausibility without naming the diagnosis in the query.

---

### 12.13 Crohn's Disease

#### 12.13.1 Consulta sin chart

```
Young patient with colic-type abdominal pain, intermittent chronic diarrhea, weight loss, and low-grade fever during flares. Reports oral aphthae and pain around the anus with occasional discharge. The symptoms appear in periods, improve partially, and then return. On occasions has noticed blood mixed with the stools, but not in all episodes.
```

#### 12.13.4 Salida esperada

- **Top-1 esperado:** Crohn's disease
- **Diferenciales plausibles:** Ulcerative colitis, irritable bowel syndrome, chronic intestinal infection, celiac disease, intestinal tuberculosis.
- **Notas críticas:**
  - The perianal involvement and aphthae orient more to Crohn's than to ulcerative colitis.
  - The flare-based evolution with weight loss helps to distinguish from irritable bowel.
  - The system must accept occasional blood without being forced into ulcerative colitis.

---

### 12.14 Ulcerative Colitis

#### 12.14.1 Consulta sin chart

```
Patient consulting for recurrent episodes of diarrhea with blood and mucus, urgency to defecate, and sensation of incomplete evacuation. Reports colic-type pain in the lower abdomen that improves partially after going to the bathroom. During flares has fatigue, low-grade fever, and loss of appetite. Does not report fistulas or perianal discharge.
```

#### 12.14.4 Salida esperada

- **Top-1 esperado:** Ulcerative colitis
- **Diferenciales plausibles:** Crohn's disease, infectious colitis, hemorrhoids with diarrhea, colorectal cancer, ischemic colitis.
- **Notas críticas:**
  - Bloody diarrhea with urgency and tenesmus is the main pattern.
  - The negation of perianal disease favors ulcerative colitis over Crohn's.
  - Useful case to differentiate two highly overlapping inflammatory bowel diseases.

---

### 12.15 Cystitis

#### 12.15.1 Consulta sin chart

```
Woman consulting for burning on urination, increased urinary frequency, and urinary urgency for one day. Reports mild suprapubic pain and sensation that the bladder does not empty completely. The urine looks cloudy and with strong odor, but has no high fever, chills, or back pain. Does not present vaginal discharge or deep pelvic pain.
```

#### 12.15.4 Salida esperada

- **Top-1 esperado:** Cystitis
- **Diferenciales plausibles:** Pyelonephritis, urethritis, vaginitis, pelvic inflammatory disease, urinary lithiasis.
- **Notas críticas:**
  - Lower urinary syndrome without fever or lumbar pain must be differentiated from pyelonephritis.
  - The absence of vaginal discharge reduces vaginitis as Top-1.
  - A good case to test negation of systemic signs.

---

### 12.16 Pyelonephritis

#### 12.16.1 Consulta sin chart

```
Patient who started with burning on urination and increased urinary frequency, and two days later developed high fever with chills. Reports intense pain in the right flank, nausea, and vomiting. On examination presents pain on right lumbar fist percussion and poor general condition. There is no cough, diarrhea, or other evident infectious focus.
```

#### 12.16.4 Salida esperada

- **Top-1 esperado:** Pyelonephritis
- **Diferenciales plausibles:** Cystitis, infected renal colic, retrocecal appendicitis, cholecystitis, mechanical lumbar pain.
- **Notas críticas:**
  - Fever with chills and flank pain differentiates upper infection from cystitis.
  - Vomiting and poor general condition suggest systemic involvement.
  - The system must relate previous lower urinary symptoms to the ascending infection.

---

### 12.17 Renal Lithiasis

#### 12.17.1 Consulta sin chart

```
Patient who comes for sudden, very intense pain in the left flank, radiating to the groin and coming in waves. He is restless, cannot find a relief position, and presents nausea with one vomiting. Reports visible blood in the urine and mild burning on urination, but has no high fever or chills. Has had a similar episode two years ago.
```

#### 12.17.4 Salida esperada

- **Top-1 esperado:** Renal lithiasis
- **Diferenciales plausibles:** Pyelonephritis, testicular or ovarian torsion, appendicitis, diverticulitis, abdominal aortic aneurysm.
- **Notas críticas:**
  - Colic pain radiating to groin + hematuria is the core of the case.
  - The patient's restlessness differentiates from peritoneal pain, where they usually stay still.
  - The absence of fever helps not to prioritize renal infection as Top-1.

---

### 12.18 Hepatitis

#### 12.18.1 Consulta sin chart

```
Patient who for a week has presented intense fatigue, loss of appetite, nausea, and dull pain in the upper right part of the abdomen. In the last two days the family notices yellow coloration of the eyes, very dark urine, and lighter-than-usual stools. Reports low-grade fever and muscle aches at the start of the picture. There is no sudden abdominal pain or signs of peritoneal irritation.
```

#### 12.18.4 Salida esperada

- **Top-1 esperado:** Hepatitis
- **Diferenciales plausibles:** Cholecystitis, choledocholithiasis, decompensated cirrhosis, drug-induced liver injury, infectious mononucleosis.
- **Notas críticas:**
  - The pseudo-flu prodrome followed by jaundice, choluria, and acholia orients to hepatocellular injury.
  - The absence of sudden intense pain reduces the probability of a surgical abdomen.
  - May be confused with biliary obstruction; the initial systemic symptoms help to discriminate.

---

### 12.19 Cirrhosis

#### 12.19.1 Consulta sin chart

```
Patient with history of chronic alcohol consumption consulting for progressive increase in abdomen size, leg swelling, and marked fatigue. The family reports that in the last few days he is drowsy, disoriented, and with behavioral changes. Presents yellowish coloration of skin and eyes, vascular spiders on the chest, and easy bruising. Also reports vomiting with blood on one recent occasion.
```

#### 12.19.4 Salida esperada

- **Top-1 esperado:** Cirrhosis
- **Diferenciales plausibles:** Right heart failure, nephrotic syndrome, severe hepatitis, liver cancer, chronic pancreatitis with ascites.
- **Notas críticas:**
  - Ascites + jaundice + encephalopathy + digestive bleeding suggest decompensation.
  - The system must integrate cutaneous and neurological data, not just the distended abdomen.
  - Useful case to verify whether complications are recognized: portal hypertension and hepatic encephalopathy.

---

### 12.20 Peptic Ulcer

#### 12.20.1 Consulta sin chart

```
Patient reporting burning pain in the pit of the stomach for several weeks, with nocturnal episodes that wake him up. The pain improves temporarily on eating or taking antacids, but reappears hours later. Has used anti-inflammatories frequently for lower back pain. In the last few days noticed black stools and a sensation of dizziness on standing up.
```

#### 12.20.4 Salida esperada

- **Top-1 esperado:** Peptic ulcer
- **Diferenciales plausibles:** Erosive gastritis, gastroesophageal reflux, pancreatitis, cholelithiasis, gastric cancer.
- **Notas críticas:**
  - Burning epigastric pain related to food/antacids is the key pattern.
  - The use of NSAIDs functions as an etiological factor.
  - Melena and dizziness test whether the system detects hemorrhagic complication.

---

### 12.21 Infectious Mononucleosis

#### 12.21.1 Consulta sin chart

```
Adolescent consulting for fever, intense sore throat, and extreme fatigue for more than a week. Presents enlarged neck lymph nodes, tonsils with exudate, and pain on swallowing. Reports persistent general malaise and a sensation of fullness in the upper left part of the abdomen. Recently had close contact with a new partner.
```

#### 12.21.4 Salida esperada

- **Top-1 esperado:** Infectious mononucleosis
- **Diferenciales plausibles:** Streptococcal pharyngotonsillitis, acute HIV infection, cytomegalovirus, toxoplasmosis, lymphoma.
- **Notas críticas:**
  - Fever + pharyngitis + cervical adenopathies + intense fatigue must dominate the ranking.
  - Fullness in the left hypochondrium suggests splenomegaly.
  - Must be differentiated from simple bacterial pharyngitis, especially by duration and marked fatigue.

---

### 12.22 Rheumatoid Arthritis

#### 12.22.1 Consulta sin chart

```
Patient who for several months has presented pain and inflammation in wrists and small joints of both hands, symmetrically. Reports morning stiffness lasting more than one hour and improving as the day progresses. Has fatigue, slight weight loss, and difficulty closing fists on waking. There are no hard nodules in the distal joints or mechanical pain that clearly improves with rest.
```

#### 12.22.4 Salida esperada

- **Top-1 esperado:** Rheumatoid arthritis
- **Diferenciales plausibles:** Nodal hand osteoarthritis, systemic lupus erythematosus, psoriatic arthritis, polyarticular gout, fibromyalgia.
- **Notas críticas:**
  - Symmetry, small joints, and prolonged stiffness distinguish inflammatory disease from osteoarthritis.
  - The negation of hard distal nodules reduces bias toward osteoarthritis.
  - Useful case to test overlap with SLE and psoriatic arthritis.

---

### 12.23 Gout

#### 12.23.1 Consulta sin chart

```
Patient who wakes up at dawn with sudden and intense pain at the base of the big toe of the right foot. The joint is red, warm, very swollen, and does not tolerate the friction of the sheet. Reports previous similar episodes that resolved on their own, and recent consumption of alcohol and meats at a copious dinner. Has no local trauma or wounds on the foot.
```

#### 12.23.4 Salida esperada

- **Top-1 esperado:** Gout
- **Diferenciales plausibles:** Septic arthritis, cellulitis, pseudogout, trauma of the first toe, reactive arthritis.
- **Notas críticas:**
  - Nocturnal podagra of sudden onset is highly characteristic.
  - The system must keep septic arthritis as a differential due to warm joint, but not as Top-1 if the pattern is recurrent.
  - The dietary/alcohol trigger helps reinforce the expected diagnosis.

---

### 12.24 Psoriasis

#### 12.24.1 Consulta sin chart

```
Patient with chronic skin lesions, well-defined, reddish, and covered with thick whitish scales. The plaques predominate on elbows, knees, and scalp, with variable itching and flares that worsen during periods of stress. Reports that on scratching the scales detach and sometimes small bleeding points appear. Also notices changes in some nails, with small depressions on the surface.
```

#### 12.24.4 Salida esperada

- **Top-1 esperado:** Psoriasis
- **Diferenciales plausibles:** Seborrheic dermatitis, atopic dermatitis, tinea corporis, lichen planus, nummular eczema.
- **Notas críticas:**
  - Well-defined erythematoscalous plaques on extensor surfaces are the main pattern.
  - The nail changes increase specificity.
  - Must be differentiated from atopic dermatitis, which is usually more flexural and less well-defined.

---

### 12.25 Atopic Dermatitis

#### 12.25.1 Consulta sin chart

```
Patient with recurrent history of very dry skin, intense itching, and flares of redness in folds of elbows and behind the knees. Reports that scratching worsens the lesions, produces crusts and sometimes small fissures. The symptoms increase with harsh soaps, sweat, dry weather, and exposure to dust. Has personal history of allergic rhinitis since childhood.
```

#### 12.25.4 Salida esperada

- **Top-1 esperado:** Atopic dermatitis
- **Diferenciales plausibles:** Psoriasis, contact dermatitis, scabies, seborrheic dermatitis, tinea corporis.
- **Notas críticas:**
  - Intense itching + xerosis + flexural distribution orient the case.
  - The atopic history helps to distinguish it from psoriasis.
  - The mention of irritant triggers tests whether the system integrates environmental context without requiring a chart.

---

### 12.26 Alzheimer's Disease

#### 12.26.1 Consulta sin chart

```
Older adult brought by his family due to progressive forgetfulness for more than a year. Repeats the same questions, loses objects inside the house, gets disoriented in known places, and has stopped managing his accounts because he confuses payments and dates. The family notices behavioral changes, irritability, and difficulty finding words, but there was no sudden onset or focal loss of strength. The evolution has been slow and increasingly interferes with his daily activities.
```

#### 12.26.4 Salida esperada

- **Top-1 esperado:** Alzheimer's disease
- **Diferenciales plausibles:** Vascular dementia, depression, delirium, hypothyroidism, vitamin B12 deficiency.
- **Notas críticas:**
  - The slow progression of episodic memory and executive function is the core of the case.
  - The absence of sudden onset reduces the probability of vascular event.
  - Useful case to test that the system distinguishes progressive cognitive deterioration from acute confusion.

---

### 12.27 Sinusitis

#### 12.27.1 Consulta sin chart

```
Patient with persistent nasal congestion, thick discharge, facial pressure-type pain in cheeks and forehead, and pain that increases on tilting the head forward. Reports partial loss of smell, nocturnal cough due to drip toward the throat, bad breath, and fatigue. The picture started after a cold that did not finish improving. Does not present chest pain or lower respiratory difficulty.
```

#### 12.27.4 Salida esperada

- **Top-1 esperado:** Sinusitis
- **Diferenciales plausibles:** Common cold, allergic rhinitis, migraine, dental pain, COVID-19.
- **Notas críticas:**
  - Facial pressure + nasal discharge + retronasal drip must outweigh isolated headache.
  - The relationship with previous cold helps to orient the upper respiratory origin.
  - The negation of lower respiratory symptoms reduces pneumonia or bronchitis as Top-1.

---

### 12.28 Endometriosis

#### 12.28.1 Consulta sin chart

```
Woman of reproductive age with chronic pelvic pain that clearly worsens during menstruation. Reports very painful periods, pain during deep sexual intercourse, and discomfort on defecation during bleeding days. Has tried to become pregnant for more than a year without success. The pain is not accompanied by fever or purulent vaginal discharge.
```

#### 12.28.4 Salida esperada

- **Top-1 esperado:** Endometriosis
- **Diferenciales plausibles:** Pelvic inflammatory disease, uterine fibroids, adenomyosis, irritable bowel syndrome, ovarian cyst.
- **Notas críticas:**
  - Cyclic pain associated with menstruation and deep dyspareunia are key.
  - Infertility increases case specificity.
  - The absence of fever and purulent discharge reduces pelvic infection as Top-1.

---

### 12.29 Benign Prostatic Hyperplasia

#### 12.29.1 Consulta sin chart

```
Older man consulting because for months he has had difficulty initiating urination, the stream comes out weak, and he must get up several times at night to urinate. Reports sensation of incomplete emptying, terminal dribbling, and need to return to the bathroom shortly after having urinated. Has no fever, lumbar pain, or intense burning on urination. Denies visible blood in the urine.
```

#### 12.29.4 Salida esperada

- **Top-1 esperado:** Benign prostatic hyperplasia
- **Diferenciales plausibles:** Prostate cancer, prostatitis, urinary infection, overactive bladder, urethral stenosis.
- **Notas críticas:**
  - Progressive lower obstructive symptoms in older adult are the central pattern.
  - The absence of fever and pain reduces prostatitis or pyelonephritis.
  - The denied hematuria helps not to shift the case toward lithiasis or bladder tumor.

---

### 12.30 Uterine Fibroids

#### 12.30.1 Consulta sin chart

```
Middle-aged woman consulting for increasingly abundant and prolonged menstrual periods, with clots and marked fatigue at the end of each menses. Also reports pressure in the lower abdomen, increased urinary frequency, and colic-type pelvic pain during the period. Does not present fever or foul-smelling vaginal discharge. In the last months has noticed pallor and decreased exercise tolerance.
```

#### 12.30.4 Salida esperada

- **Top-1 esperado:** Uterine fibroids
- **Diferenciales plausibles:** Endometriosis, adenomyosis, endometrial cancer, coagulation disorder, uterine polyps.
- **Notas críticas:**
  - Heavy menstrual bleeding + pelvic pressure + urinary symptoms from mass are key.
  - Pallor and fatigue suggest secondary anemia due to chronic bleeding.
  - The absence of fever and foul-smelling discharge reduces pelvic infection.

---

### 12.31 Otitis Media

#### 12.31.1 Consulta sin chart

```
Child who after several days of nasal congestion and cough starts with intense pain in one ear, fever, and irritability. The parents report that he wakes up crying, pulls his ear, and hears worse on that side. On examination, a reddened and bulging eardrum is observed. There is no neck stiffness or important respiratory difficulty.
```

#### 12.31.4 Salida esperada

- **Top-1 esperado:** Otitis media
- **Diferenciales plausibles:** Otitis externa, pharyngitis, mastoiditis, foreign body in ear, referred dental pain.
- **Notas críticas:**
  - Ear pain with fever after upper respiratory infection orients to middle ear.
  - Bulging eardrum and hearing loss help to distinguish from otitis externa.
  - The negation of neck stiffness reduces meningitis as Top-1.

---

### 12.32 Herpes Zoster

#### 12.32.1 Consulta sin chart

```
Adult patient with burning pain and tingling in a band of skin on the right side of the chest for two days. Then grouped vesicles appear on a reddish base, limited to the same path and without crossing the midline. Reports that the rubbing of clothes produces intense pain. Had no recent contact with irritant substances or similar lesions on both sides of the body.
```

#### 12.32.4 Salida esperada

- **Top-1 esperado:** Herpes zoster
- **Diferenciales plausibles:** Contact dermatitis, herpes simplex, cellulitis, impetigo, intercostal neuralgia.
- **Notas críticas:**
  - Previous neuropathic pain + vesicles in unilateral distribution is the differentiator.
  - The respect for the midline increases specificity.
  - The absence of irritant exposure reduces contact dermatitis.

---

### 12.33 Dengue

#### 12.33.1 Consulta sin chart

```
Patient returning from a tropical area presenting with sudden onset of high fever, intense pain behind the eyes, very marked muscle and joint pains, nausea, and skin rash. Reports extreme fatigue and strong headache. On examination, small spots on the skin and mild nasal bleeding are observed. Has no productive cough or evident bacterial focus.
```

#### 12.33.4 Salida esperada

- **Top-1 esperado:** Dengue
- **Diferenciales plausibles:** Influenza, malaria, chikungunya, zika, typhoid fever.
- **Notas críticas:**
  - High fever + retroocular pain + myalgias/arthralgias + rash is the main pattern.
  - The history of tropical area and mosquitoes increases plausibility.
  - Mild hemorrhagic manifestations test whether the system identifies warning signs.

---

### 12.34 Measles

#### 12.34.1 Consulta sin chart

```
Unvaccinated child who starts with high fever, cough, runny nose, and red eyes with sensitivity to light. After a few days a red rash appears that starts on the face and descends to the trunk and extremities. In the mouth small white spots are observed on the mucosa. The family reports recent contact with another child with fever and rash.
```

#### 12.34.4 Salida esperada

- **Top-1 esperado:** Measles
- **Diferenciales plausibles:** Rubella, chickenpox, scarlet fever, nonspecific viral exanthem, drug reaction.
- **Notas críticas:**
  - Fever + cough + coryza + conjunctivitis + descending exanthem is the classic pattern.
  - The intraoral white spots are a very specific clue.
  - The unvaccinated status should increase the diagnostic weight.

---

### 12.35 Chickenpox

#### 12.35.1 Consulta sin chart

```
Child with low-grade fever, malaise, and loss of appetite who develops very pruritic lesions on face, trunk, and back. The lesions appear in crops: some are red spots, others blisters with fluid, and others already have crusts. The family reports that several school classmates presented a similar picture. There is no distribution in a single band or previous burning pain.
```

#### 12.35.4 Salida esperada

- **Top-1 esperado:** Chickenpox
- **Diferenciales plausibles:** Herpes zoster, impetigo, scabies, allergic reaction, hand-foot-mouth disease.
- **Notas críticas:**
  - Lesions at different evolutionary stages are the key data.
  - The generalized distribution on trunk and face helps to differentiate it from herpes zoster.
  - The school contact reinforces contagious childhood disease.

---

### 12.36 Conjunctivitis

#### 12.36.1 Consulta sin chart

```
Patient consulting for red eye, gritty sensation, tearing, and itching since the morning. Reports discharge that sticks the eyelids on waking and mild burning, but vision is preserved. Does not present intense eye pain, halos around lights, or nausea. On examination, diffuse redness of the white part of the eye is observed.
```

#### 12.36.4 Salida esperada

- **Top-1 esperado:** Conjunctivitis
- **Diferenciales plausibles:** Glaucoma, keratitis, uveitis, foreign body, ocular allergy.
- **Notas críticas:**
  - Red eye with discharge and gritty sensation orients to conjunctival inflammation.
  - Preserved vision and absence of intense pain reduce urgent ophthalmological causes.
  - Useful case to evaluate negations of warning signs.

---

### 12.37 Glaucoma

#### 12.37.1 Consulta sin chart

```
Older patient reporting progressive loss of lateral vision, as if looking through a tunnel, without eye pain initially. On another occasion presented an acute episode with intense pain in one eye, blurred vision, halos around lights, nausea, and red eye. In the consultation, elevated intraocular pressure is documented. There is no purulent discharge or predominant itching.
```

#### 12.37.4 Salida esperada

- **Top-1 esperado:** Glaucoma
- **Diferenciales plausibles:** Cataracts, conjunctivitis, optic neuritis, ocular migraine, retinal detachment.
- **Notas críticas:**
  - Progressive peripheral vision loss is key in chronic forms.
  - Eye pain with halos and nausea suggest an acute episode.
  - The absence of discharge/itching helps not to confuse it with conjunctivitis.

---

### 12.38 Cataracts

#### 12.38.1 Consulta sin chart

```
Older adult reporting increasingly cloudy vision and difficulty reading or driving at night. Notices glare from car headlights, less vivid colors, and need to change glasses prescription frequently. Does not present eye pain, red eye, or sudden vision loss. The deterioration has been slow and affects both eyes, although one more than the other.
```

#### 12.38.4 Salida esperada

- **Top-1 esperado:** Cataracts
- **Diferenciales plausibles:** Glaucoma, macular degeneration, diabetic retinopathy, refractive error, dry eye.
- **Notas críticas:**
  - Progressive cloudy vision and nighttime glare are key.
  - The absence of pain and red eye reduces acute glaucoma or ocular inflammation.
  - The slow bilateral evolution helps to differentiate from vascular events or retinal detachment.

---

### 12.39 Leukemia

#### 12.39.1 Consulta sin chart

```
Patient consulting for intense fatigue, intermittent fever, and night sweats for several weeks. Reports easy appearance of bruises, bleeding from gums on brushing, and small red dots on the skin. Has lost weight and has repeated infections. On examination, enlarged lymph nodes are palpated and the spleen appears enlarged.
```

#### 12.39.4 Salida esperada

- **Top-1 esperado:** Leukemia
- **Diferenciales plausibles:** Lymphoma, aplastic anemia, infectious mononucleosis, thrombocytopenic purpura, chronic infection.
- **Notas críticas:**
  - Fatigue + infections + bleeding/bruises suggests bone marrow failure.
  - Petechiae and gum bleeding test whether the system captures thrombocytopenia.
  - Adenopathies and splenomegaly help to differentiate from isolated anemia.

---

### 12.40 Breast Cancer

#### 12.40.1 Consulta sin chart

```
Woman who detects a hard lump in one breast, with poorly defined edges, that does not disappear after several menstrual cycles. Reports recent nipple retraction and skin changes, with a dimpled appearance. Also notices bloody discharge from the nipple and a palpable lymph node in the axilla on the same side. There is no fever or intense pain as in an abscess.
```

#### 12.40.4 Salida esperada

- **Top-1 esperado:** Breast cancer
- **Diferenciales plausibles:** Fibroadenoma, breast cyst, mastitis, breast abscess, fibrocystic changes.
- **Notas críticas:**
  - Persistent hard mass + nipple retraction + skin changes are warning signs.
  - Axillary adenopathy increases suspicion.
  - The absence of fever and intense pain reduces mastitis/abscess as Top-1.

---

### 12.41 HIV/AIDS

#### 12.41.1 Consulta sin chart

```
Patient with fever, sore throat, enlarged cervical lymph nodes, intense fatigue, and skin rash after a risky sexual exposure several weeks before. Months later reports weight loss, persistent diarrhea, night sweats, and recurrent oral infections with whitish plaques. Does not recall having had a previous chronic illness that would explain the loss of defenses.
```

#### 12.41.4 Salida esperada

- **Top-1 esperado:** HIV/AIDS
- **Diferenciales plausibles:** Infectious mononucleosis, cytomegalovirus, tuberculosis, lymphoma, viral hepatitis.
- **Notas críticas:**
  - Pseudo-flu syndrome after risky exposure orients to initial infection.
  - Weight loss, opportunistic infections, and oral candidiasis suggest advanced immunodeficiency.
  - The system must suggest serological confirmation and not stay only with viral pharyngitis.

---

### 12.42 Endocarditis

#### 12.42.1 Consulta sin chart

```
Patient with persistent fever, chills, and night sweats for two weeks, associated with fatigue, loss of appetite, and joint pain. Has history of recent dental procedure and a previously damaged heart valve. On examination, a new murmur, small hemorrhages under the nails, and red dots on palms and soles are detected. There is no clear respiratory focus.
```

#### 12.42.4 Salida esperada

- **Top-1 esperado:** Endocarditis
- **Diferenciales plausibles:** Sepsis, rheumatic fever, tuberculosis, lymphoma, prolonged viral infection.
- **Notas críticas:**
  - Persistent fever + new murmur + peripheral vascular lesions is the key pattern.
  - The dental and valvular history increases probability.
  - The absence of respiratory focus reduces pneumonia as the main explanation.

---

### 12.43 Allergic Rhinitis

#### 12.43.1 Consulta sin chart

```
Patient who every spring presents repeated sneezing, nasal congestion, itching in nose and eyes, tearing, and clear nasal discharge. The symptoms worsen on going out to the park or dusting and improve when staying in closed environments. Has no fever, intense facial pain, or purulent nasal discharge. Reports personal history of mild asthma and dermatitis in childhood.
```

#### 12.43.4 Salida esperada

- **Top-1 esperado:** Allergic rhinitis
- **Diferenciales plausibles:** Common cold, sinusitis, conjunctivitis, nasal polyps, COVID-19.
- **Notas críticas:**
  - Seasonality + allergen exposure + clear rhinorrhea orient the diagnosis.
  - The absence of fever and purulent discharge reduces infection.
  - Atopic history increases specificity.

---

### 12.44 Herniated Disc

#### 12.44.1 Consulta sin chart

```
Patient consulting for low back pain that radiates down the back of the leg to the foot, with tingling and numbness. The pain worsens on sitting, coughing, or straining, and improves partially on lying down. On raising the extended leg the same radiating pain appears. Does not report fever, unexplained weight loss, or significant recent trauma.
```

#### 12.44.4 Salida esperada

- **Top-1 esperado:** Herniated disc
- **Diferenciales plausibles:** Mechanical low back pain, spinal stenosis, piriformis syndrome, vertebral fracture, spinal tumor.
- **Notas críticas:**
  - Radicular pain with paresthesias and positive straight-leg raise orient to nerve compression.
  - Worsening with cough/effort suggests increased pressure on the nerve root.
  - The negation of fever, weight loss, and trauma reduces infectious, tumoral, or fracture causes.

---

### 12.45 Cervical Cancer

#### 12.45.1 Consulta sin chart

```
Woman consulting for vaginal bleeding after sexual intercourse and bleeding between periods for several months. Reports watery vaginal discharge with strong odor and occasional pelvic pain. In the last weeks notices pain during sexual intercourse and fatigue. Has history of irregular gynecological controls and an altered screening test that was not followed up.
```

#### 12.45.4 Salida esperada

- **Top-1 esperado:** Cervical cancer
- **Diferenciales plausibles:** Cervicitis, cervical polyp, uterine fibroids, endometriosis, endometrial cancer.
- **Notas críticas:**
  - Postcoital bleeding + abnormal discharge + altered screening are central signals.
  - The gradual evolution and history of incomplete controls increase suspicion.
  - The system must differentiate it from benign causes of gynecological bleeding.

---

### 12.46 Gastritis

#### 12.46.1 Consulta sin chart

```
Patient consulting for burning and pain in the upper part of the abdomen, with sensation of early fullness, nausea, and frequent belching. Reports that the discomfort worsens after eating irritants, drinking coffee, or using anti-inflammatories for several days. On occasions presents vomiting without blood and loss of appetite, but does not report oppressive chest pain or radiation to the arm. The abdomen is soft, with mild pain on epigastric palpation.
```

#### 12.46.4 Salida esperada

- **Top-1 esperado:** Gastritis
- **Diferenciales plausibles:** Peptic ulcer, gastroesophageal reflux, functional dyspepsia, pancreatitis, cholecystitis.
- **Notas críticas:**
  - The case evaluates epigastric pain in relation to irritants and NSAIDs.
  - Must be differentiated from peptic ulcer if there is no clear nocturnal pattern or melena.
  - The negation of oppressive chest pain avoids diverting the case toward coronary syndrome.

---

### 12.47 Gastroesophageal Reflux

#### 12.47.1 Consulta sin chart

```
Patient reporting burning sensation behind the sternum, especially after copious meals and on lying down. Notices acid regurgitation toward the throat, bitter taste in the mouth, and nocturnal dry cough. The symptoms improve partially on raising the head of the bed or taking antacids. Does not present fever, pleuritic pain, or progressive respiratory difficulty.
```

#### 12.47.4 Salida esperada

- **Top-1 esperado:** Gastroesophageal reflux
- **Diferenciales plausibles:** Gastritis, peptic ulcer, angina, nocturnal asthma, infectious esophagitis.
- **Notas críticas:**
  - Postprandial heartburn and acid regurgitation are the main signals.
  - The nocturnal cough may act as a respiratory distractor.
  - The absence of systemic symptoms reduces pneumonia or respiratory infection as Top-1.

---

### 12.48 Bronchitis

#### 12.48.1 Consulta sin chart

```
Patient who after a cold starts with persistent cough, initially dry and then with clear or yellowish phlegm. Reports fatigue, mild chest tightness, and occasional wheezing on breathing, but the fever has been low or absent. Does not present intense pleuritic chest pain or focal crackles on auscultation. Saturation remains normal and the picture has lasted less than two weeks.
```

#### 12.48.4 Salida esperada

- **Top-1 esperado:** Bronchitis
- **Diferenciales plausibles:** Pneumonia, asthma, COPD, influenza, COVID-19.
- **Notas críticas:**
  - The history of upper respiratory infection followed by persistent cough is the axis of the case.
  - Must be distinguished from pneumonia by absence of high fever, hypoxemia, and focal findings.
  - May overlap with asthma due to wheezing, but the post-viral temporality orients the diagnosis.

---

### 12.49 Influenza

#### 12.49.1 Consulta sin chart

```
Patient who starts abruptly with high fever, chills, generalized muscle pain, headache, and intense fatigue. Reports dry cough, sore throat, and nasal congestion, with a sensation of being "battered" from the first day. Several people at his work have had a similar picture during the same week. Does not predominantly present loss of smell or important gastrointestinal symptoms.
```

#### 12.49.4 Salida esperada

- **Top-1 esperado:** Influenza
- **Diferenciales plausibles:** COVID-19, common cold, bronchitis, pneumonia, dengue.
- **Notas críticas:**
  - Sudden onset with high fever and intense myalgias must be differentiated from the common cold.
  - The context of an outbreak in close contacts reinforces viral respiratory infection.
  - The negation of predominant anosmia reduces bias toward COVID-19, although it remains a differential.

---

### 12.50 COVID-19

#### 12.50.1 Consulta sin chart

```
Patient consulting for fever, dry cough, sore throat, marked fatigue, and muscle pain for three days. Reports recent loss of smell and taste, in addition to nasal congestion and mild diarrhea. Lives with a person who presented a similar respiratory picture and later had a positive test. There is no focal pleuritic pain or abundant purulent expectoration.
```

#### 12.50.4 Salida esperada

- **Top-1 esperado:** COVID-19
- **Diferenciales plausibles:** Influenza, common cold, bronchitis, pneumonia, allergic rhinitis.
- **Notas críticas:**
  - The loss of smell/taste and close contact are discriminating signals.
  - The case tests overlap with influenza and common cold.
  - The absence of purulent expectoration and focal pain reduces bacterial pneumonia as Top-1.

---

### 12.51 Arterial Hypertension

#### 12.51.1 Consulta sin chart

```
Patient coming for repeated checks of elevated blood pressure at home and in consultation, with figures around 155/95 mmHg for several weeks. Reports occasional headache on waking and tinnitus, although generally feels well. Has overweight, high salt consumption, and family history of cardiovascular problems. Does not present chest pain, focal weakness, or acute respiratory difficulty.
```

#### 12.51.4 Salida esperada

- **Top-1 esperado:** Arterial hypertension
- **Diferenciales plausibles:** White coat hypertension, anxiety, secondary hypertension, hyperthyroidism, pheochromocytoma.
- **Notas críticas:**
  - The persistence of elevated figures is more important than nonspecific symptoms.
  - Should avoid overweighting isolated headache as a neurological diagnosis.
  - The system must recognize that it may be asymptomatic and still clinically relevant.

---

### 12.52 Iron Deficiency Anemia

#### 12.52.1 Consulta sin chart

```
Patient consulting for progressive fatigue, pallor, dizziness on standing up, and shortness of breath on climbing stairs. Reports brittle nails, hair loss, and desire to chew ice. For months has had very abundant and prolonged menstruations. Does not present jaundice, dark urine, or acute abdominal pain.
```

#### 12.52.4 Salida esperada

- **Top-1 esperado:** Iron deficiency anemia
- **Diferenciales plausibles:** Hemolytic anemia, anemia of chronic disease, vitamin B12 deficiency, hypothyroidism, occult digestive bleeding.
- **Notas críticas:**
  - Pica, brittle nails, and chronic menstrual bleeding orient to iron deficiency.
  - The negation of jaundice and dark urine helps not to prioritize hemolytic anemia.
  - Useful case to discriminate anemia from chronic loss versus erythrocyte destruction.

---

### 12.53 Osteoporosis

#### 12.53.1 Consulta sin chart

```
Older patient consulting for dorsal pain after lifting a light bag, without significant fall. Reports progressive loss of height and stooped posture in recent years. On a previous X-ray, vertebral crushing was described, and had a wrist fracture after a fall from her own height. There is no fever, marked weight loss, or persistent nocturnal inflammatory pain.
```

#### 12.53.4 Salida esperada

- **Top-1 esperado:** Osteoporosis
- **Diferenciales plausibles:** Bone metastases, multiple myeloma, osteomalacia, vertebral osteoarthritis, traumatic fracture.
- **Notas críticas:**
  - Low-impact fracture and height loss are key signals.
  - Must be distinguished from simple mechanical low back pain due to bone fragility.
  - The absence of fever and weight loss reduces malignant or infectious processes as Top-1.

---

### 12.54 Fibromyalgia

#### 12.54.1 Consulta sin chart

```
Patient reporting generalized pain in muscles and joints for more than six months, accompanied by intense fatigue and non-restorative sleep. Describes difficulty concentrating, sensation of mental fog, and worsening of symptoms with stress. Previous inflammatory analyses have been normal and there are no warm, red, or deformed joints. The pain changes location and does not follow a single neurological territory.
```

#### 12.54.4 Salida esperada

- **Top-1 esperado:** Fibromyalgia
- **Diferenciales plausibles:** Hypothyroidism, rheumatoid arthritis, systemic lupus erythematosus, depression, chronic fatigue syndrome.
- **Notas críticas:**
  - Chronic generalized pain + fatigue + non-restorative sleep is the central pattern.
  - The absence of synovitis and inflammatory markers should avoid classifying it as inflammatory arthritis.
  - The system must handle overlap with mood disorders without reducing the whole picture to depression.

---

### 12.55 Diverticulitis

#### 12.55.1 Consulta sin chart

```
Adult patient consulting for constant pain in the lower left part of the abdomen, associated with fever, nausea, and recent change in bowel habit. Reports constipation alternating with episodes of mild diarrhea and pain on palpating that area. Does not present burning on urination or flank pain. On occasions has had similar but milder discomfort, but this time the pain is more persistent.
```

#### 12.55.4 Salida esperada

- **Top-1 esperado:** Diverticulitis
- **Diferenciales plausibles:** Infectious colitis, colorectal cancer, irritable bowel syndrome, pyelonephritis, left appendicitis due to anatomical variation.
- **Notas críticas:**
  - Lower left quadrant pain with fever and bowel change is the core.
  - The absence of urinary symptoms reduces upper urinary infection as Top-1.
  - Must be differentiated from irritable bowel due to fever and persistent localized pain.

---

### 12.56 Hemorrhoids

#### 12.56.1 Consulta sin chart

```
Patient reporting bright red bleeding at the end of evacuation and on cleaning, without blood mixed uniformly with the stools. Presents anal itching, sensation of a lump that appears on pushing, and pain on sitting when the lump becomes inflamed. The symptoms worsen with constipation and prolonged efforts in the bathroom. Does not report weight loss, fever, or progressive change in stool caliber.
```

#### 12.56.4 Salida esperada

- **Top-1 esperado:** Hemorrhoids
- **Diferenciales plausibles:** Anal fissure, colorectal cancer, proctitis, rectal polyps, inflammatory bowel disease.
- **Notas críticas:**
  - Bright red bleeding related to defecation and prolapsing mass orient the diagnosis.
  - The absence of weight loss and progressive changes reduces colorectal cancer as Top-1, although it must remain as a differential.
  - Must be distinguished from anal fissure if the pain is not cutting and pruritus/lump predominate.

---

### 12.57 Prostatitis

#### 12.57.1 Consulta sin chart

```
Male consulting for pelvic pain and discomfort between the scrotum and anus, accompanied by burning on urination and frequent need to go to the bathroom. Reports fever, chills, and pain on ejaculation since two days ago. On examination, aggressive exploration is avoided because the rectal touch causes intense pain. There is no evident urethral discharge or visible genital lesions.
```

#### 12.57.4 Salida esperada

- **Top-1 esperado:** Prostatitis
- **Diferenciales plausibles:** Cystitis, STD urethritis, benign prostatic hyperplasia, epididymitis, pyelonephritis.
- **Notas críticas:**
  - Perineal/pelvic pain with urinary symptoms and fever orients to prostatic inflammation/infection.
  - Must be differentiated from simple cystitis due to perineal pain and pain on ejaculation.
  - The absence of urethral discharge reduces urethritis as Top-1.

---

### 12.58 Vaginitis

#### 12.58.1 Consulta sin chart

```
Woman consulting for abnormal vaginal discharge, intense itching, burning, and discomfort on urination without fever. Reports vulvar redness and pain during sexual intercourse. The discharge has changed in appearance and odor compared to her usual, and the symptoms appeared after recent antibiotic use. Does not present deep pelvic pain or abundant uterine bleeding.
```

#### 12.58.4 Salida esperada

- **Top-1 esperado:** Vaginitis
- **Diferenciales plausibles:** Cystitis, pelvic inflammatory disease, chlamydia, gonorrhea, contact dermatitis.
- **Notas críticas:**
  - Abnormal discharge + vulvovaginal itching/burning must weigh more than isolated dysuria.
  - The history of antibiotics may orient to candidiasis as subtype, but the expected generic Top-1 is vaginitis.
  - The absence of deep pelvic pain reduces pelvic inflammatory disease.

---

### 12.59 Chlamydia

#### 12.59.1 Consulta sin chart

```
Sexually active patient consulting for burning on urination and scant genital discharge, with mild pelvic discomfort. Reports bleeding after sexual intercourse and pain during them, although the symptoms have been discrete and progressive. Had a new partner recently and did not use a condom in all encounters. Does not present painful ulcers or grouped vesicles on genitals.
```

#### 12.59.4 Salida esperada

- **Top-1 esperado:** Chlamydia
- **Diferenciales plausibles:** Gonorrhea, cystitis, vaginitis, genital herpes simplex, pelvic inflammatory disease.
- **Notas críticas:**
  - Mild urogenital symptoms with recent sexual exposure orient to frequent STD.
  - The absence of ulcers or vesicles reduces herpes simplex as Top-1.
  - Gonorrhea must be kept as a close differential due to clinical overlap.

---

### 12.60 Colorectal Cancer

#### 12.60.1 Consulta sin chart

```
Older patient consulting for progressive change in bowel habit, with constipation alternating with diarrhea and sensation of incomplete evacuation. Reports blood in the stools, unintentional weight loss, and fatigue. On analysis, iron deficiency anemia of unclear cause has been found. Does not present high fever or acute sudden-onset abdominal pain.
```

#### 12.60.4 Salida esperada

- **Top-1 esperado:** Colorectal cancer
- **Diferenciales plausibles:** Hemorrhoids, inflammatory bowel disease, diverticulitis, colorectal polyps, irritable bowel syndrome.
- **Notas críticas:**
  - Progressive change in bowel habit + blood + iron deficiency anemia is an alarm pattern.
  - Must avoid attributing everything to hemorrhoids if there is weight loss and anemia.
  - The absence of fever and acute pain reduces diverticulitis as Top-1.

---

### 12.61 Lung Cancer

#### 12.61.1 Consulta sin chart

```
Patient with significant smoking history consulting for persistent cough of several months, increasingly intense. Reports weight loss, fatigue, dull chest pain, and episodes of blood in the sputum. In recent weeks notices shortness of breath on exertion and new hoarseness. Does not describe sudden onset with high fever or clear improvement with cold treatments.
```

#### 12.61.4 Salida esperada

- **Top-1 esperado:** Lung cancer
- **Diferenciales plausibles:** Tuberculosis, pneumonia, COPD, bronchiectasis, pulmonary embolism.
- **Notas críticas:**
  - Chronic cough with hemoptysis, weight loss, and smoking is the axis of the case.
  - Must be differentiated from tuberculosis by absence of predominant afternoon fever/night sweats.
  - The new hoarseness may suggest advanced local involvement.

---

### 12.62 Depression

#### 12.62.1 Consulta sin chart

```
Patient who for more than a month has presented persistent sadness, loss of interest in activities she previously enjoyed, and marked fatigue. Reports sleeping poorly, difficulty concentrating, feelings of guilt, and changes in appetite with weight loss. Her symptoms affect work and family relationships almost every day. Denies substance use and does not present periods of excessive energy or marked decrease in need to sleep.
```

#### 12.62.4 Salida esperada

- **Top-1 esperado:** Depression
- **Diferenciales plausibles:** Bipolar disorder, hypothyroidism, normal grief, anxiety disorder, anemia.
- **Notas críticas:**
  - Duration, anhedonia, and functional impact must weigh more than transient sadness.
  - The negation of elevated energy episodes helps not to prioritize bipolar disorder.
  - The system must keep medical causes of fatigue as differentials, not as Top-1.

---

### 12.63 Anxiety Disorder

#### 12.63.1 Consulta sin chart

```
Patient reporting excessive worry almost daily about work, family, and health topics, difficult to control. Presents restlessness, muscle tension, irritability, difficulty sleeping, and sensation of always being on alert. On occasions has palpitations and mild chest tightness during moments of stress, but basic cardiological studies have been normal. The symptoms have lasted several months and affect his daily performance.
```

#### 12.63.4 Salida esperada

- **Top-1 esperado:** Anxiety disorder
- **Diferenciales plausibles:** Hyperthyroidism, panic disorder, depression, pheochromocytoma, arrhythmia.
- **Notas críticas:**
  - Persistent and difficult-to-control worry is more specific than isolated palpitations.
  - Must be differentiated from hyperthyroidism if there is no weight loss, persistent tremor, or goiter.
  - The cardiac symptoms function as a distractor, but should not dominate if the pattern is chronic and situational.

---

### 12.64 Scabies

#### 12.64.1 Consulta sin chart

```
Patient consulting for very intense itching that worsens at night and affects spaces between the fingers, wrists, waist, and genitals. On examination, small papules and fine lines are observed on the skin, some with excoriations from scratching. Several cohabitants have started with similar itching in recent days. There is no fever or thick well-defined plaques with silvery scales.
```

#### 12.64.4 Salida esperada

- **Top-1 esperado:** Scabies
- **Diferenciales plausibles:** Atopic dermatitis, contact dermatitis, urticaria, psoriasis, pediculosis.
- **Notas críticas:**
  - Nocturnal pruritus + interdigital involvement + contagion in cohabitants is the main pattern.
  - The absence of typical scaly plaques reduces psoriasis.
  - Must avoid being confused with atopic dermatitis if there is characteristic distribution and contagion.

---

### 12.65 Herpes Simplex

#### 12.65.1 Consulta sin chart

```
Patient presenting with painful grouped lesions in the form of small blisters on a red base, with burning sensation and tingling before they appear. Has had similar episodes in the same area, especially during periods of stress or fever. Some vesicles break and leave superficial erosions that later form crusts. There are no extensive plaques with dermatomal distribution or persistent intense neuralgic pain.
```

#### 12.65.4 Salida esperada

- **Top-1 esperado:** Herpes simplex
- **Diferenciales plausibles:** Herpes zoster, aphthae, impetigo, contact dermatitis, primary syphilis.
- **Notas críticas:**
  - Recurrent grouped vesicles with prodrome of burning/tingling orient the diagnosis.
  - The negation of dermatomal distribution reduces herpes zoster as Top-1.
  - The recurrence in the same site is a key signal.

---

### 12.66 Pharyngitis

#### 12.66.1 Consulta sin chart

```
Patient consulting for sore throat, fever, general malaise, and pain on swallowing. On examination, reddened tonsils with exudate and tender lymph nodes in the front of the neck are observed. Does not present significant cough, intense nasal congestion, or marked hoarseness. The picture started two days ago and several classmates have had similar sore throat.
```

#### 12.66.4 Salida esperada

- **Top-1 esperado:** Pharyngitis
- **Diferenciales plausibles:** Infectious mononucleosis, influenza, COVID-19, bacterial tonsillitis, peritonsillar abscess.
- **Notas críticas:**
  - Pharyngeal pain with fever, anterior adenopathies, and absence of cough orients to pharyngeal infection.
  - Must be differentiated from mononucleosis if there is no prolonged fatigue or splenomegaly.
  - The system should not answer only "influenza" if pharyngeal findings predominate.

---

### 12.67 Otitis Externa

#### 12.67.1 Consulta sin chart

```
Patient consulting for intense pain in one ear after several days of swimming. The pain worsens on touching or moving the auricle and is accompanied by itching, sensation of clogged ear, and scant discharge. Does not report high fever or significant cold symptoms. On examination, the external auditory canal is observed red, inflamed, and sensitive.
```

#### 12.67.4 Salida esperada

- **Top-1 esperado:** Otitis externa
- **Diferenciales plausibles:** Otitis media, cerumen impaction, foreign body, mastoiditis, referred pain from temporomandibular disorder.
- **Notas críticas:**
  - Pain on moving the auricle and history of water in the ear are key.
  - Must be distinguished from otitis media, where the pain does not depend so much on manipulating the ear.
  - The absence of high fever and respiratory symptoms reduces middle ear infection as Top-1.

---

### 12.68 Tinea

#### 12.68.1 Consulta sin chart

```
Patient presenting with rounded skin lesions, with red, raised, and scaly border, while the center looks clearer. Reports itching and slow growth of the lesions over several weeks. Has frequent contact with pets and shares towels at the gym. There are no thick symmetrical plaques on elbows and knees, nor painful vesicular lesions.
```

#### 12.68.4 Salida esperada

- **Top-1 esperado:** Tinea
- **Diferenciales plausibles:** Psoriasis, atopic dermatitis, contact dermatitis, pityriasis rosea, impetigo.
- **Notas críticas:**
  - Annular lesion with active scaly border and central clearing is the key pattern.
  - Contact with pets or shared surfaces helps to reinforce superficial infectious etiology.
  - The negation of thick extensor plaques reduces psoriasis.

---

### 12.69 Hypoglycemia

#### 12.69.1 Consulta sin chart

```
Patient presenting with sudden episodes of cold sweating, tremor, palpitations, intense hunger, and sensation of anxiety. In some episodes adds confusion, blurred vision, and difficulty speaking, which improve quickly on taking juice or eating something sweet. The symptoms appear when she skips meals or after applying more medication than usual to control blood sugar. There is no fever or prolonged loss of consciousness with postictal phase.
```

#### 12.69.4 Salida esperada

- **Top-1 esperado:** Hypoglycemia
- **Diferenciales plausibles:** Panic crisis, epilepsy, vasovagal syncope, arrhythmia, transient ischemic attack.
- **Notas críticas:**
  - Adrenergic + neuroglycopenic symptoms that correct with sugar are very characteristic.
  - The history of glucose-lowering medication functions as an etiological signal.
  - The negation of postictal phase helps not to prioritize epilepsy.

---

## Appendix — Results Recording Template

For each case, record:

```
Case: [name]
Mode: [no chart | with male chart | with female chart]
Search mode: [standard | web | positioned]

Top-1 obtained: ___________________
Top-3 obtained: ___________________
Matches expected? [yes | no | partial]
Valid citations? [yes | no]
Did it trigger the insufficiency banner? [yes | no]
Did it trigger web enrichment? [yes | no]

Observations:
-
-
```
