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
