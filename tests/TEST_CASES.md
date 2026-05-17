# Casos de Prueba — Diagnosis Retrieval System

> Documento de pruebas reproducibles para el sistema RAG clínico. Cada enfermedad incluye:
> - **Consulta sin chart** (sólo párrafo de síntomas, como un médico general describiría al paciente).
> - **Chart de paciente Hombre** y **Chart de paciente Mujer** (realistas, no obvios).
> - **Salida esperada (Top-1)** y diagnósticos diferenciales plausibles.
> - **Notas críticas** sobre lo que se pone a prueba.
>
> **Cómo usar:** copiar el "Chief Complaint" en el formulario *Patient Chart*, llenar los campos del chart, y pegar la **Consulta** en la barra de búsqueda. Probar primero **sin chart** (sólo la consulta) y luego **con chart**.
>
> **Idioma del usuario:** español (médico general, no especialista).

---

## Índice

1. [Acromegalia](#1-acromegalia)
2. [Acidosis Láctica](#2-acidosis-láctica)
3. [Hipertiroidismo](#3-hipertiroidismo)
4. [Hipotiroidismo Congénito](#4-hipotiroidismo-congénito)
5. [Anemia Hemolítica](#5-anemia-hemolítica)
6. [Arteriosclerosis / Aterosclerosis](#6-arteriosclerosis--aterosclerosis)
7. [Artrosis](#7-artrosis)
8. [Casos Críticos con Negación](#8-casos-críticos-con-negación)
9. [Casos Críticos con Ambigüedad y Solapamiento](#9-casos-críticos-con-ambigüedad-y-solapamiento)
10. [Casos donde el Chart puede Influir Negativamente](#10-casos-donde-el-chart-puede-influir-negativamente)
11. [Enfermedades Adicionales](#11-enfermedades-adicionales)
    - 11.1 [Diabetes Mellitus tipo 2](#111-diabetes-mellitus-tipo-2)
    - 11.2 [Embolia Pulmonar](#112-embolia-pulmonar)
    - 11.3 [Enfermedad de Addison (Insuficiencia Suprarrenal Primaria)](#113-enfermedad-de-addison-insuficiencia-suprarrenal-primaria)
    - 11.4 [Síndrome de Cushing](#114-síndrome-de-cushing)
    - 11.5 [Enfermedad de Parkinson](#115-enfermedad-de-parkinson)
    - 11.6 [Esclerosis Múltiple](#116-esclerosis-múltiple)
    - 11.7 [Lupus Eritematoso Sistémico](#117-lupus-eritematoso-sistémico)
    - 11.8 [Insuficiencia Cardíaca Congestiva](#118-insuficiencia-cardíaca-congestiva)
    - 11.9 [Pancreatitis Aguda](#119-pancreatitis-aguda)
    - 11.10 [Feocromocitoma](#1110-feocromocitoma)

---

## 1. Acromegalia

### 1.1 Consulta sin chart (RAG simple)

```
Paciente que desde hace varios años ha notado que su talla de zapatos ha aumentado y que los anillos ya no le entran. Refiere que sus rasgos faciales se han vuelto más toscos, con la mandíbula más prominente y separación de los dientes. Se queja de dolor de cabeza persistente, hormigueo en las manos compatible con túnel carpiano, sudoración excesiva y ronquidos intensos con apnea del sueño. Además presenta dolor articular generalizado y disminución de la libido.
```

### 1.2 Chart — Paciente HOMBRE

- **Age:** 47
- **Sex:** M
- **Comorbidities:** hipertensión arterial, intolerancia a la glucosa, síndrome de apnea del sueño
- **Chief Complaint:** Cambio progresivo de talla de zapatos y anillos en los últimos 4 años, con cefalea diaria
- **Vital Signs:** HR 78 · BP 148/92 · RR 14 · SpO2 96 · Temp 36.7
- **Physical Findings:** Manos y pies aumentados de tamaño, rasgos faciales toscos, prognatismo, macroglosia leve, piel engrosada con hiperhidrosis. Signo de Tinel positivo bilateral.
- **Lab Results:** Glucosa en ayunas 128 mg/dL, HbA1c 6.7%. No se han solicitado IGF-1 ni GH.
- **Imaging:** Ninguna disponible.
- **Current Medications:** enalapril 20 mg/día, ibuprofeno PRN
- **Allergies:** NKDA
- **Social History:** No fumador, alcohol social, conductor de camión
- **Family History:** Padre con HTA. Sin antecedentes endocrinos conocidos.
- **Additional Notes:** Refiere que su esposa nota que ronca cada vez más fuerte y que ha tenido que cambiar la alianza matrimonial dos veces.

### 1.3 Chart — Paciente MUJER

- **Age:** 52
- **Sex:** F
- **Comorbidities:** bocio multinodular, diabetes tipo 2
- **Chief Complaint:** Dolor articular generalizado, parestesias en manos y cambio en la voz
- **Vital Signs:** HR 82 · BP 142/88 · RR 16 · SpO2 97 · Temp 36.8
- **Physical Findings:** Voz ronca y grave, facies tosca, arcos superciliares prominentes, manos grandes con dedos en salchicha. Bocio palpable.
- **Lab Results:** Glucosa 156 mg/dL, HbA1c 7.4%, TSH 1.2 mUI/L (normal). No IGF-1.
- **Imaging:** Ecografía tiroidea con nódulos múltiples benignos.
- **Current Medications:** metformina 1g BID
- **Allergies:** NKDA
- **Social History:** Ama de casa, no fuma
- **Family History:** Madre con DM2 e hipertensión
- **Additional Notes:** Refiere amenorrea desde hace 8 meses (atribuida a menopausia) y galactorrea ocasional.

### 1.4 Salida esperada

- **Top-1 esperado:** Acromegalia
- **Diferenciales plausibles:** Hipotiroidismo (por voz ronca / facies), gigantismo (descartar por edad adulta), síndrome de túnel carpiano idiopático, artrosis primaria.
- **Notas críticas:**
  - La paciente mujer tiene comorbilidades (bocio, DM2) que **distraen** hacia hipertiroidismo/hipotiroidismo. El sistema debe priorizar la acromegalia por la facies + manos grandes + galactorrea.
  - El hombre tiene chart "obvio endocrinológico" sin que el médico haya pedido IGF-1 — prueba que el sistema sugiera el diagnóstico correcto y la prueba diagnóstica adecuada.

---

## 2. Acidosis Láctica

### 2.1 Consulta sin chart

```
Paciente que llega a urgencias con dolor abdominal intenso, náuseas y vómitos. Presenta respiración rápida y profunda, somnolencia y confusión. Refiere haber tomado más medicación de la habitual en los últimos días por sentirse mal. La gasometría muestra pH 7.18 y lactato sérico de 7.2 mmol/L.
```

### 2.2 Chart — Paciente HOMBRE

- **Age:** 64
- **Sex:** M
- **Comorbidities:** diabetes tipo 2 de larga evolución, enfermedad renal crónica estadio 3b, hipertensión
- **Chief Complaint:** Dolor abdominal, náuseas y respiración agitada de 24 horas de evolución
- **Vital Signs:** HR 118 · BP 92/58 · RR 32 · SpO2 95 · Temp 36.2
- **Physical Findings:** Letárgico, mucosas secas, respiración de Kussmaul, abdomen difusamente doloroso sin signos peritoneales.
- **Lab Results:** pH 7.17, HCO3 9 mEq/L, lactato 8.1 mmol/L, glucosa 142 mg/dL (sin cetonas), creatinina 2.8 mg/dL, K 5.6.
- **Imaging:** Rx abdomen sin hallazgos agudos.
- **Current Medications:** metformina 1g BID, enalapril 20 mg, atorvastatina 40 mg
- **Allergies:** NKDA
- **Social History:** Jubilado, bebedor moderado
- **Family History:** Padre fallecido por IAM
- **Additional Notes:** En la última semana tuvo gastroenteritis con disminución de la ingesta hídrica.

### 2.3 Chart — Paciente MUJER

- **Age:** 38
- **Sex:** F
- **Comorbidities:** ninguna conocida
- **Chief Complaint:** Vómitos persistentes, dolor de estómago y dificultad para respirar
- **Vital Signs:** HR 124 · BP 88/52 · RR 34 · SpO2 94 · Temp 38.6
- **Physical Findings:** Diaforesis, palidez, taquipnea con respiración profunda, abdomen blando con leve dolor difuso. Sin focalidad neurológica.
- **Lab Results:** pH 7.20, HCO3 10, lactato 6.8 mmol/L, glucosa 88 mg/dL, leucocitos 18.500 con neutrofilia, PCR 220, hemocultivos pendientes.
- **Imaging:** Rx tórax con infiltrado basal derecho.
- **Current Medications:** anticonceptivo oral
- **Allergies:** penicilina
- **Social History:** Profesora, no fumadora, alcohol ocasional
- **Family History:** Sin relevancia
- **Additional Notes:** Hace 3 días con fiebre y tos productiva, automedicación con paracetamol e ibuprofeno.

### 2.4 Salida esperada

- **Top-1 esperado:** Acidosis láctica
- **Diferenciales plausibles:** Cetoacidosis diabética (descartar por ausencia de cetonas en hombre), sepsis (mujer — coexiste), shock séptico, intoxicación por salicilatos.
- **Notas críticas:**
  - **Hombre:** chart fuerza al sistema a no pasar por alto la metformina + ERC (factor desencadenante clásico).
  - **Mujer:** la sepsis es **causa** de la acidosis láctica — el sistema no debe dar "neumonía" como Top-1 sino reconocer la acidosis láctica con sepsis como factor desencadenante.

---

## 3. Hipertiroidismo

### 3.1 Consulta sin chart

```
Paciente que refiere desde hace 3 meses pérdida de peso a pesar de comer más, nerviosismo, temblor fino en las manos, palpitaciones y sudoración excesiva. Tolera mal el calor, tiene tendencia a la diarrea y duerme mal. Al examen presenta taquicardia y un bocio difuso. Refiere también caída de cabello y alteraciones menstruales.
```

### 3.2 Chart — Paciente HOMBRE

- **Age:** 41
- **Sex:** M
- **Comorbidities:** trastorno de ansiedad generalizada (diagnóstico previo)
- **Chief Complaint:** Pérdida de 8 kg en 2 meses, palpitaciones e insomnio
- **Vital Signs:** HR 112 · BP 138/72 · RR 18 · SpO2 98 · Temp 37.4
- **Physical Findings:** Piel caliente y húmeda, temblor distal fino, mirada brillante con leve protrusión ocular, bocio difuso no doloroso, reflejos vivos.
- **Lab Results:** TSH < 0.01 mUI/L, T4L 3.8 ng/dL (elevada), T3L 9.2 pg/mL (elevada).
- **Imaging:** Pendiente ecografía tiroidea.
- **Current Medications:** sertralina 50 mg/día, alprazolam PRN
- **Allergies:** NKDA
- **Social History:** Fumador 1 paquete/día, ingeniero, alcohol social
- **Family History:** Hermana con tiroiditis de Hashimoto
- **Additional Notes:** Inicialmente atribuyó los síntomas a una crisis de ansiedad y aumentó alprazolam, sin mejoría.

### 3.3 Chart — Paciente MUJER

- **Age:** 29
- **Sex:** F
- **Comorbidities:** ninguna
- **Chief Complaint:** Sensación constante de calor, pérdida de peso y ciclos menstruales irregulares
- **Vital Signs:** HR 108 · BP 128/68 · RR 16 · SpO2 99 · Temp 37.2
- **Physical Findings:** Bocio difuso simétrico, exoftalmos leve bilateral, piel fina y caliente, eritema pretibial discreto.
- **Lab Results:** TSH < 0.01, T4L elevada, T3L elevada, anticuerpos TSI positivos.
- **Imaging:** Ecografía tiroidea con glándula aumentada e hipervascularizada.
- **Current Medications:** ninguna
- **Allergies:** NKDA
- **Social History:** Diseñadora gráfica, no fuma, alcohol ocasional
- **Family History:** Madre con enfermedad de Graves, abuela con vitíligo
- **Additional Notes:** Embarazo descartado (β-hCG negativa).

### 3.4 Salida esperada

- **Top-1 esperado:** Hipertiroidismo (Enfermedad de Graves para la mujer dado el exoftalmos + TSI+; primario para el hombre)
- **Diferenciales plausibles:** Ansiedad/trastorno de pánico (en hombre, distractor por antecedente), feocromocitoma, bocio multinodular tóxico, tirotoxicosis facticia.
- **Notas críticas:**
  - **Hombre:** chart con ansiedad previa pone a prueba si el sistema "se queda" con la explicación psiquiátrica o reconoce el patrón endocrino con TSH suprimida.
  - **Mujer:** caso de libro — el reto es que el Top-1 sea suficientemente específico ("Enfermedad de Graves") y no quede sólo en "hipertiroidismo".

---

## 4. Hipotiroidismo Congénito

### 4.1 Consulta sin chart

```
Recién nacido de 3 semanas de vida que la madre trae a consulta porque "no se despierta para comer", llora poco y mama con dificultad. Presenta ictericia prolongada, estreñimiento desde el nacimiento, hernia umbilical y abdomen distendido. Al examen tiene fontanela posterior amplia, hipotonía y lengua prominente. No se realizó tamiz neonatal por parto domiciliario.
```

### 4.2 Chart — Paciente HOMBRE (lactante)

- **Age:** 0 (28 días de vida)
- **Sex:** M
- **Comorbidities:** ninguna conocida
- **Chief Complaint:** Letargia, succión débil y estreñimiento desde el nacimiento
- **Vital Signs:** HR 102 · BP 70/40 · RR 32 · SpO2 97 · Temp 36.1
- **Physical Findings:** Ictericia persistente, fontanela posterior amplia, macroglosia, hernia umbilical, hipotonía generalizada, llanto ronco.
- **Lab Results:** Bilirrubina total 9 mg/dL (mayor indirecta), Hb normal, TSH y T4 no realizadas.
- **Imaging:** Ninguna.
- **Current Medications:** ninguna
- **Allergies:** desconocidas
- **Social History:** Parto domiciliario atendido por partera, no recibió tamiz metabólico neonatal
- **Family History:** Madre con tiroiditis postparto en embarazo anterior
- **Additional Notes:** Madre refiere que el bebé duerme casi todo el día y debe ser despertado para alimentarse.

### 4.3 Chart — Paciente MUJER (lactante)

- **Age:** 0 (2 meses)
- **Sex:** F
- **Comorbidities:** ninguna
- **Chief Complaint:** Escaso aumento de peso y constipación
- **Vital Signs:** HR 110 · BP 72/42 · RR 36 · SpO2 98 · Temp 36.3
- **Physical Findings:** Piel seca y fría, llanto ronco, hipotonía, lengua que protruye, abdomen prominente con hernia umbilical. Reflejos disminuidos.
- **Lab Results:** TSH del tamiz neonatal "alterada" (informe verbal de la madre, sin papel). No se realizó confirmación.
- **Imaging:** Ninguna.
- **Current Medications:** ninguna
- **Allergies:** desconocidas
- **Social History:** Lactancia materna exclusiva
- **Family History:** Sin antecedentes tiroideos conocidos
- **Additional Notes:** Ganancia ponderal de 280 g en el último mes (subóptima).

### 4.4 Salida esperada

- **Top-1 esperado:** Hipotiroidismo congénito
- **Diferenciales plausibles:** Síndrome de Down (por hipotonía + macroglosia), enfermedad de Hirschsprung (por estreñimiento), ictericia neonatal prolongada por leche materna, atresia de vías biliares.
- **Notas críticas:**
  - Caso especialmente sensible a **edad** del paciente — el sistema debe usar la edad del chart para inferir que se trata de la forma congénita, no del hipotiroidismo del adulto.
  - El antecedente de "tiroiditis postparto materna" en el hombre es un distractor que puede empujar hacia "hipotiroidismo neonatal transitorio por anticuerpos maternos" — diferencial válido pero no el Top-1.

---

## 5. Anemia Hemolítica

### 5.1 Consulta sin chart

```
Paciente que consulta por cansancio progresivo desde hace 2 semanas, palidez intensa, dolor de cabeza y dificultad para respirar al subir escaleras. En los últimos días ha notado que la piel y los ojos se le han puesto amarillentos y que la orina es muy oscura, casi como Coca-Cola. Al examen presenta esplenomegalia palpable.
```

### 5.2 Chart — Paciente HOMBRE

- **Age:** 22
- **Sex:** M
- **Comorbidities:** ninguna
- **Chief Complaint:** Astenia, ictericia y orina oscura desde hace 5 días
- **Vital Signs:** HR 110 · BP 110/68 · RR 20 · SpO2 96 · Temp 36.9
- **Physical Findings:** Palidez mucocutánea, ictericia escleral, esplenomegalia 3 cm bajo reborde costal, sin adenopatías.
- **Lab Results:** Hb 7.2 g/dL, VCM 96, reticulocitos 11%, LDH 980, bilirrubina indirecta 4.2 mg/dL, haptoglobina < 10, Coombs directo negativo. G6PD pendiente.
- **Imaging:** Ecografía abdominal con esplenomegalia homogénea.
- **Current Medications:** ninguna habitual. **Hace 4 días tomó trimetoprim-sulfametoxazol** por infección urinaria.
- **Allergies:** NKDA
- **Social History:** Origen mediterráneo, estudiante universitario
- **Family History:** Tío materno con "anemia rara" desde la infancia
- **Additional Notes:** Comió habas en una reunión familiar la semana pasada.

### 5.3 Chart — Paciente MUJER

- **Age:** 34
- **Sex:** F
- **Comorbidities:** lupus eritematoso sistémico
- **Chief Complaint:** Debilidad, palidez y disnea de esfuerzo progresiva
- **Vital Signs:** HR 116 · BP 102/64 · RR 22 · SpO2 95 · Temp 37.1
- **Physical Findings:** Palidez intensa, ictericia leve, esplenomegalia, sin adenopatías.
- **Lab Results:** Hb 6.8 g/dL, VCM 102, reticulocitos 13%, LDH 1100, bilirrubina indirecta 3.8, haptoglobina indetectable, Coombs directo POSITIVO (IgG).
- **Imaging:** Ecografía con esplenomegalia.
- **Current Medications:** hidroxicloroquina 200 mg/día, prednisona 5 mg/día
- **Allergies:** sulfas
- **Social History:** Trabaja en oficina
- **Family History:** Madre con artritis reumatoide
- **Additional Notes:** Refiere brote articular reciente y aparición de aftas orales.

### 5.4 Salida esperada

- **Top-1 esperado:**
  - **Hombre:** Anemia hemolítica por déficit de G6PD (favismo / fármaco desencadenante).
  - **Mujer:** Anemia hemolítica autoinmune por anticuerpos calientes (IgG) asociada a LES.
- **Diferenciales plausibles:** Hepatitis aguda (por ictericia + orina oscura), síndrome hemolítico urémico, anemia por sangrado oculto, anemia megaloblástica.
- **Notas críticas:**
  - **Hombre:** los datos del chart (origen mediterráneo, habas, sulfas) son claves diagnósticas que sin chart NO están en la consulta. **Excelente caso para comparar RAG con vs. sin chart.**
  - **Mujer:** Coombs+ y LES sólo aparecen en chart. Sin chart, el sistema sólo puede llegar a "anemia hemolítica"; con chart debe especificar el subtipo autoinmune.

---

## 6. Arteriosclerosis / Aterosclerosis

### 6.1 Consulta sin chart

```
Paciente que refiere desde hace varios meses dolor opresivo en el pecho que aparece al caminar deprisa o subir cuestas y cede con el reposo en pocos minutos. También nota calambres en las pantorrillas tras caminar dos cuadras que mejoran al pararse. Ha notado los pies fríos y le cuesta cicatrizar una pequeña herida en el dedo gordo.
```

### 6.2 Chart — Paciente HOMBRE

- **Age:** 68
- **Sex:** M
- **Comorbidities:** hipertensión arterial, dislipidemia, diabetes tipo 2, EPOC leve
- **Chief Complaint:** Dolor torácico de esfuerzo y claudicación intermitente a 100 metros
- **Vital Signs:** HR 76 · BP 158/92 · RR 16 · SpO2 95 · Temp 36.6
- **Physical Findings:** Soplo carotídeo derecho, pulsos pedios disminuidos bilateralmente, úlcera superficial en primer ortejo derecho, piel atrófica y brillante en piernas.
- **Lab Results:** LDL 168, HDL 32, triglicéridos 220, glucosa 152, HbA1c 7.8%, creatinina 1.2.
- **Imaging:** ECG con ondas Q en cara inferior (antiguas, no documentadas previamente).
- **Current Medications:** enalapril 20 mg, metformina 1g BID, AAS 100 mg
- **Allergies:** NKDA
- **Social History:** Fumador 40 paquetes-año (activo), sedentario, dieta rica en grasas
- **Family History:** Padre IAM a los 55, hermano con bypass coronario
- **Additional Notes:** Refiere disfunción eréctil progresiva de 2 años de evolución.

### 6.3 Chart — Paciente MUJER

- **Age:** 72
- **Sex:** F
- **Comorbidities:** hipertensión, dislipidemia, artritis reumatoide
- **Chief Complaint:** Calambres en piernas al caminar y dolor torácico ocasional
- **Vital Signs:** HR 82 · BP 162/88 · RR 18 · SpO2 96 · Temp 36.5
- **Physical Findings:** Pulsos tibiales posteriores disminuidos, soplo abdominal, xantelasmas palpebrales, deformidades articulares en manos.
- **Lab Results:** LDL 184, HDL 48, triglicéridos 198, glucosa 108, HbA1c 5.9%, VSG 38, PCR 12.
- **Imaging:** Ecodoppler de carótidas con placas bilaterales y estenosis del 50% derecha.
- **Current Medications:** losartán 50 mg, metotrexate 15 mg/semana, ácido fólico, prednisona 5 mg
- **Allergies:** NKDA
- **Social History:** Ex-fumadora (dejó hace 10 años), camina poco por dolor articular
- **Family History:** Madre con ictus a los 70
- **Additional Notes:** En los últimos meses ha notado pérdida de visión transitoria en el ojo derecho ("como si bajara una cortina").

### 6.4 Salida esperada

- **Top-1 esperado:** Aterosclerosis (con enfermedad arterial periférica + cardiopatía isquémica).
- **Diferenciales plausibles:** Arteriosclerosis de Mönckeberg (descartar — usualmente asintomática), arteritis de Takayasu, tromboangeítis obliterante (Buerger), insuficiencia venosa crónica, estenosis raquídea (claudicación neurógena).
- **Notas críticas:**
  - El sistema debe **distinguir arteriosclerosis (general) de aterosclerosis (específica)** — el chart provee LDL alto, factores de riesgo y placas, que apuntan al subtipo aterosclerótico.
  - **Mujer:** el episodio de amaurosis fugax sugiere émbolo carotídeo — el sistema debe captarlo aunque no esté en la pregunta.
  - **Hombre:** las ondas Q antiguas en ECG sugieren IAM silente — riesgo de que el sistema se desvíe hacia "cardiopatía isquémica crónica" como Top-1 en lugar de la enfermedad subyacente.

---

## 7. Artrosis

### 7.1 Consulta sin chart

```
Paciente de edad avanzada con dolor en ambas rodillas que aparece al caminar y al bajar escaleras, mejora con el reposo, y que se ha ido haciendo más intenso en los últimos 2 años. Refiere rigidez matutina breve (menos de 15 minutos), crepitación al moverlas y ocasional inflamación. No hay enrojecimiento ni fiebre.
```

### 7.2 Chart — Paciente HOMBRE

- **Age:** 71
- **Sex:** M
- **Comorbidities:** obesidad grado II (IMC 34), HTA
- **Chief Complaint:** Dolor mecánico en rodilla derecha de 3 años de evolución, ahora con deformidad en varo
- **Vital Signs:** HR 72 · BP 138/82 · RR 14 · SpO2 97 · Temp 36.5
- **Physical Findings:** Rodilla derecha con crepitación, arcos de movimiento limitados (flexión 100°), deformidad en varo evidente. Sin signos inflamatorios agudos.
- **Lab Results:** PCR 4 (normal), VSG 18, ácido úrico 6.2 (normal), FR negativo.
- **Imaging:** Rx rodilla derecha con pinzamiento del compartimento medial, osteofitos marginales, esclerosis subcondral y quistes pequeños.
- **Current Medications:** enalapril, paracetamol PRN
- **Allergies:** NKDA
- **Social History:** Albañil jubilado, antecedente de trabajos de carga durante 40 años
- **Family History:** Madre con artrosis de manos
- **Additional Notes:** Refiere fractura de meseta tibial derecha hace 25 años tratada conservadoramente.

### 7.3 Chart — Paciente MUJER

- **Age:** 64
- **Sex:** F
- **Comorbidities:** obesidad, hipotiroidismo en tratamiento
- **Chief Complaint:** Dolor y deformidad progresiva en articulaciones interfalángicas distales de las manos
- **Vital Signs:** HR 70 · BP 132/78 · RR 14 · SpO2 98 · Temp 36.4
- **Physical Findings:** Nódulos de Heberden en IFD, nódulos de Bouchard en IFP, sin sinovitis caliente. Rodillas con crepitación bilateral.
- **Lab Results:** PCR < 3, VSG 14, FR negativo, anti-CCP negativo, ácido úrico normal.
- **Imaging:** Rx manos con pinzamiento de IFD, osteofitos, sin erosiones.
- **Current Medications:** levotiroxina 75 mcg, paracetamol
- **Allergies:** AINEs (gastritis)
- **Social History:** Costurera retirada
- **Family History:** Madre y abuela con "dedos torcidos" en la vejez
- **Additional Notes:** Refiere que sus dedos se ven cada vez más deformes pero no tiene rigidez matutina prolongada.

### 7.4 Salida esperada

- **Top-1 esperado:** Artrosis (osteoartritis)
- **Diferenciales plausibles:** Artritis reumatoide (descartada por FR/anti-CCP negativos, ausencia de sinovitis), artritis psoriásica, gota (descartada por úrico normal), condrocalcinosis.
- **Notas críticas:**
  - El chart de la mujer es **muy específico** para nódulos de Heberden/Bouchard — el sistema debe nombrar la artrosis nodal (de manos).
  - El antecedente de fractura del hombre apunta a artrosis postraumática — diagnóstico más específico que "artrosis primaria".

---

## 8. Casos Críticos con Negación

> Estos casos prueban si el sistema maneja correctamente la **negación explícita** en la consulta y el chart. El test es: el sistema NO debe usar el síntoma negado como evidencia a favor.

### 8.1 Negación en consulta — Acidosis SIN cetonas (excluye CAD)

**Consulta:**
```
Paciente diabético con respiración rápida y profunda, dolor abdominal y confusión. La glucosa está en 140 mg/dL, NO hay cetonas en orina ni en sangre, y el lactato está elevado en 7 mmol/L.
```

- **Chart:** ver caso 2.2 (hombre con metformina y ERC).
- **Top-1 esperado:** Acidosis láctica (asociada a metformina + ERC).
- **Lo que NO debe salir como Top-1:** Cetoacidosis diabética.
- **Crítico:** si el sistema responde CAD ignora completamente la negación de cetonas.

### 8.2 Negación en consulta — Bocio SIN hipertiroidismo

**Consulta:**
```
Mujer con bocio difuso palpable, cansancio, aumento de peso, intolerancia al frío y piel seca. NO presenta nerviosismo, NO tiene palpitaciones, NO tiene pérdida de peso ni temblor.
```

- **Top-1 esperado:** Hipotiroidismo (probable tiroiditis de Hashimoto).
- **Lo que NO debe salir:** Hipertiroidismo / enfermedad de Graves (aunque "bocio" es palabra clave compartida).
- **Crítico:** prueba si el sistema sobrepondera el término "bocio" sin considerar las negaciones del resto del cuadro.

### 8.3 Negación en chart — Dolor articular SIN signos inflamatorios

**Consulta:**
```
Mujer de 58 años con dolor poliarticular en manos de varios años de evolución y rigidez. Quiero descartar artritis reumatoide.
```

- **Chart (clave):** PCR normal, VSG normal, FR negativo, anti-CCP negativo, **NO hay sinovitis ni signos inflamatorios**, nódulos de Heberden presentes.
- **Top-1 esperado:** Artrosis nodal de manos.
- **Lo que NO debe salir:** Artritis reumatoide.
- **Crítico:** el médico **pregunta por AR**, pero la negación de marcadores y signos inflamatorios + nódulos óseos debe llevar al sistema a la artrosis.

### 8.4 Negación en consulta — Anemia SIN sangrado ni déficit nutricional

**Consulta:**
```
Hombre de 22 años con anemia severa, ictericia y orina oscura. NO hay sangrado digestivo, NO hay melenas ni hematuria, dieta normal sin déficit de hierro ni B12.
```

- **Top-1 esperado:** Anemia hemolítica.
- **Lo que NO debe salir:** Anemia ferropénica, anemia por sangrado digestivo, anemia megaloblástica.
- **Crítico:** las negaciones eliminan las causas más frecuentes — el sistema debe llegar a la causa hemolítica.

---

## 9. Casos Críticos con Ambigüedad y Solapamiento

> Casos donde dos o más enfermedades del corpus comparten síntomas y el sistema debe discriminar.

### 9.1 Hipertiroidismo vs. Acromegalia (síntomas compartidos: sudoración, bocio, fatiga)

**Consulta:**
```
Paciente que refiere sudoración profusa, fatiga, dolor articular y bocio palpable. Ha notado que ya no le entran los anillos y que su voz es más grave.
```

- **Top-1 esperado:** Acromegalia (los anillos + voz grave son el diferenciador).
- **Diferencial cercano:** Hipertiroidismo (por sudoración + bocio).
- **Notas:** Sin chart con IGF-1 o TSH, el sistema debe inclinarse por acromegalia por la especificidad del "no entran los anillos" + voz.

### 9.2 Acidosis láctica vs. Cetoacidosis (respiración de Kussmaul compartida)

**Consulta:**
```
Diabético tipo 2 en tratamiento, llega con respiración rápida y profunda, dolor abdominal y deshidratación. pH 7.18.
```

- **Sin más datos, ambos son plausibles** — el sistema debería listarlos como diferenciales y pedir cetonas y lactato.
- **Con chart 2.2 (metformina + ERC, sin cetonas, lactato alto):** Top-1 acidosis láctica.
- **Con chart alternativo (glucosa 480, cetonuria +++, lactato normal):** Top-1 cetoacidosis diabética.
- **Crítico:** test ideal para evaluar el peso del chart en la decisión.

### 9.3 Arteriosclerosis vs. Estenosis raquídea (claudicación)

**Consulta:**
```
Hombre mayor con dolor en piernas al caminar que mejora con el reposo.
```

- **Sin chart:** ambiguo entre claudicación vascular y neurógena.
- **Chart vascular (caso 6.2):** Top-1 aterosclerosis / EAP.
- **Chart alternativo con dolor que mejora al inclinarse hacia adelante, pulsos conservados:** debería virar a estenosis raquídea (NO está en corpus → caso de **insuficiencia** del sistema, debe activar web).

### 9.4 Anemia hemolítica autoinmune vs. por G6PD

**Consulta:**
```
Joven con anemia, ictericia, orina oscura y esplenomegalia, sin sangrado.
```

- **Sin chart:** Top-1 "anemia hemolítica" genérica.
- **Con chart 5.2 (origen mediterráneo + habas + sulfas):** subtipo G6PD.
- **Con chart 5.3 (LES + Coombs+):** subtipo autoinmune por anticuerpos calientes.
- **Crítico:** mismo "Top-1 genérico" debe especificarse según chart.

### 9.5 Hipotiroidismo congénito vs. síndrome de Down

**Consulta:**
```
Lactante de 6 semanas con hipotonía, lengua grande, hernia umbilical e ictericia prolongada.
```

- **Top-1 esperado por corpus:** Hipotiroidismo congénito.
- **Diferencial clínico real:** Síndrome de Down (no está en corpus — caso de **insuficiencia**, web debe activarse).
- **Crítico:** prueba que el sistema **no fuerce** una respuesta del corpus si el cuadro tiene rasgos extras (rasgos faciales típicos, pliegue palmar único — que se podrían añadir al chart para hacer el test más exigente).

---

## 10. Casos donde el Chart puede Influir Negativamente

> Estos casos están diseñados para que el chart contenga información **realista pero distractora** que podría desviar al sistema del diagnóstico correcto.

### 10.1 Chart de Acromegalia con bocio prominente — riesgo de hipertiroidismo

**Consulta:**
```
Mujer de 52 años con dolor articular generalizado, parestesias en manos y cambios en la voz.
```

- **Chart 1.3** (acromegalia mujer): incluye **bocio multinodular, DM2, TSH normal**.
- **Riesgo:** el sistema puede dar Top-1 hipotiroidismo subclínico o bocio multinodular, en vez de acromegalia.
- **Indicador correcto:** facies tosca, manos grandes, galactorrea, amenorrea → acromegalia con compresión hipofisaria.
- **Crítico:** evalúa si el chart **suma señales relevantes** sin **silenciar el cuadro principal**.

### 10.2 Chart de Hipertiroidismo con antecedente de ansiedad — riesgo de "atribución psiquiátrica"

**Consulta:**
```
Hombre de 41 años con palpitaciones, insomnio, pérdida de peso y nerviosismo.
```

- **Chart 3.2:** ansiedad previa, en tratamiento con sertralina y alprazolam.
- **Riesgo:** el sistema puede inclinarse a "crisis de ansiedad / trastorno de pánico".
- **Indicador correcto en chart:** TSH < 0.01, T4L elevada, bocio difuso.
- **Crítico:** el sistema debe **priorizar evidencia bioquímica sobre antecedente psiquiátrico**.

### 10.3 Chart de Acidosis Láctica con cuadro infeccioso — riesgo de Top-1 "Sepsis/Neumonía"

**Consulta:**
```
Mujer de 38 años con vómitos, dolor abdominal y dificultad respiratoria.
```

- **Chart 2.3:** fiebre, leucocitosis, PCR alta, infiltrado pulmonar.
- **Riesgo:** Top-1 "neumonía bacteriana" o "sepsis" (ninguna en corpus → respuesta web).
- **Esperado correcto:** Top-1 acidosis láctica (con sepsis como causa subyacente, mencionada como factor desencadenante).
- **Crítico:** el sistema debe distinguir **causa primaria del corpus (acidosis láctica)** vs. **factor precipitante**.

### 10.4 Chart de Anemia Hemolítica con LES — riesgo de "Lupus" como Top-1

**Consulta:**
```
Mujer de 34 años con palidez, debilidad y disnea.
```

- **Chart 5.3:** LES en tratamiento, brote articular, aftas orales.
- **Riesgo:** Top-1 "lupus eritematoso sistémico" (no en corpus → respuesta menos pertinente).
- **Esperado correcto:** Top-1 anemia hemolítica autoinmune (manifestación hematológica del LES).
- **Crítico:** evalúa si el sistema **clasifica la queja principal hematológica** sin "abandonarla" por la comorbilidad de fondo.

### 10.5 Chart de Artrosis con sospecha de AR planteada por el médico

**Consulta:**
```
Mujer de 58 años con dolor poliarticular en manos. ¿Podría ser artritis reumatoide?
```

- **Chart 7.3:** FR negativo, anti-CCP negativo, PCR normal, nódulos de Heberden.
- **Riesgo:** el sistema sigue al médico y devuelve "artritis reumatoide" o "AR seronegativa".
- **Esperado correcto:** Top-1 artrosis nodal de manos. Mencionar que la AR es razonablemente descartada por la negatividad serológica + ausencia de signos inflamatorios.
- **Crítico:** mide la **resistencia al sesgo de confirmación** del clínico.

### 10.6 Chart con medicación que es CAUSA de la enfermedad

**Consulta:**
```
Hombre de 22 años con anemia aguda e ictericia.
```

- **Chart 5.2:** ingesta reciente de **trimetoprim-sulfametoxazol** + consumo de habas.
- **Riesgo:** el sistema lista la anemia hemolítica genérica sin identificar el desencadenante.
- **Esperado correcto:** Top-1 anemia hemolítica por déficit de G6PD desencadenada por sulfas/favismo.
- **Crítico:** mide si el sistema **integra la medicación del chart como agente etiológico**, no solo como contexto.

---

## 11. Enfermedades Adicionales

> Estas enfermedades **no están en `casos.txt`** pero son de alta prevalencia clínica y útiles para probar la cobertura del corpus + la activación del modo web cuando el corpus es insuficiente. Información clínica basada en guías estándar (ADA, ESC, NICE, UpToDate).

---

### 11.1 Diabetes Mellitus tipo 2

#### Consulta sin chart

```
Paciente que en los últimos meses ha bajado 6 kilos sin proponérselo, tiene mucha sed, orina varias veces durante la noche y refiere visión borrosa intermitente. Le han aparecido infecciones en la piel que tardan en curar y tiene hormigueo en los pies.
```

#### Chart — HOMBRE

- **Age:** 54
- **Sex:** M
- **Comorbidities:** obesidad central, hipertensión, dislipidemia mixta
- **Chief Complaint:** Poliuria, polidipsia y pérdida ponderal de 6 kg en 3 meses
- **Vital Signs:** HR 84 · BP 148/90 · RR 14 · SpO2 98 · Temp 36.6
- **Physical Findings:** Acantosis nigricans cervical, perímetro abdominal 112 cm, candidiasis interdigital en pies, hipoestesia en calcetín bilateral.
- **Lab Results:** Glucosa en ayunas 198 mg/dL, HbA1c 9.2%, LDL 158, triglicéridos 280, creatinina 1.1, microalbuminuria 80 mg/g.
- **Imaging:** No relevante.
- **Current Medications:** losartán 50 mg
- **Allergies:** NKDA
- **Social History:** Comercial, sedentario, consume bebidas azucaradas a diario
- **Family History:** Padre con DM2 e IAM a los 60
- **Additional Notes:** Su esposa refiere que ronca y a veces deja de respirar (sospecha SAHOS).

#### Chart — MUJER

- **Age:** 46
- **Sex:** F
- **Comorbidities:** síndrome de ovario poliquístico, hígado graso no alcohólico
- **Chief Complaint:** Cansancio intenso, infecciones urinarias recurrentes y prurito vulvar
- **Vital Signs:** HR 88 · BP 134/82 · RR 16 · SpO2 98 · Temp 36.7
- **Physical Findings:** IMC 32, acantosis nigricans en cuello y axilas, hirsutismo leve.
- **Lab Results:** Glucosa 168, HbA1c 8.1%, perfil lipídico alterado, transaminasas elevadas (ALT 68).
- **Imaging:** Ecografía abdominal con esteatosis hepática grado II.
- **Current Medications:** anticonceptivo combinado (suspendido hace 1 año)
- **Allergies:** NKDA
- **Social History:** Trabaja desde casa, dieta alta en hidratos refinados
- **Family History:** Madre DM2, abuela materna DM2
- **Additional Notes:** Antecedente de diabetes gestacional en su segundo embarazo (hace 8 años).

#### Salida esperada

- **Top-1 esperado:** Diabetes mellitus tipo 2.
- **Diferenciales plausibles:** Diabetes tipo 1 (descartar por edad/contexto), LADA, diabetes secundaria a Cushing, diabetes inducida por fármacos.
- **Notas críticas:**
  - Mujer: SOP + diabetes gestacional previa son factores de riesgo claros — el sistema debe integrarlos.
  - **Probable activación de Web** si el corpus no cubre DM2.

---

### 11.2 Embolia Pulmonar

#### Consulta sin chart

```
Paciente que de forma brusca presenta dolor en el costado derecho del pecho, dificultad para respirar y tos con un poco de sangre. Está taquicárdica y con saturación baja. Hace una semana tuvo una operación de rodilla y ha estado en reposo.
```

#### Chart — HOMBRE

- **Age:** 62
- **Sex:** M
- **Comorbidities:** cáncer de próstata en tratamiento hormonal, HTA
- **Chief Complaint:** Disnea súbita y dolor torácico pleurítico de 6 horas
- **Vital Signs:** HR 124 · BP 96/62 · RR 28 · SpO2 88 (aire ambiente) · Temp 37.4
- **Physical Findings:** Taquipnea, ingurgitación yugular leve, edema y dolor en pantorrilla izquierda con signo de Homans+.
- **Lab Results:** D-dímero 5800 ng/mL, troponina I 0.08 (levemente elevada), gasometría con hipoxemia y alcalosis respiratoria.
- **Imaging:** Angio-TC tórax con defectos de repleción en arterias segmentarias del lóbulo inferior derecho. Eco-Doppler MMII con trombosis en vena femoral superficial izquierda.
- **Current Medications:** leuprolide, enalapril
- **Allergies:** NKDA
- **Social History:** Jubilado, sedentario en el último mes por dolor lumbar
- **Family History:** Hermano con TVP
- **Additional Notes:** Refiere viaje en autobús de 14 horas hace 4 días.

#### Chart — MUJER

- **Age:** 34
- **Sex:** F
- **Comorbidities:** ninguna
- **Chief Complaint:** Disnea progresiva y dolor torácico izquierdo de 12 horas, con un episodio de síncope
- **Vital Signs:** HR 118 · BP 102/68 · RR 26 · SpO2 91 · Temp 37.0
- **Physical Findings:** Pierna derecha con edema asimétrico y dolor a la palpación de pantorrilla.
- **Lab Results:** D-dímero 4200, troponina y BNP levemente elevados.
- **Imaging:** Angio-TC con embolia pulmonar bilateral submasiva. Ecocardio: dilatación de VD.
- **Current Medications:** anticonceptivo oral combinado
- **Allergies:** NKDA
- **Social History:** Fumadora 10 cigarrillos/día, vuelo trasatlántico hace 2 días
- **Family History:** Madre con TVP postparto
- **Additional Notes:** Pareja refiere que palideció y casi se desmaya al levantarse del baño.

#### Salida esperada

- **Top-1 esperado:** Embolia pulmonar (TEP).
- **Diferenciales plausibles:** Síndrome coronario agudo, neumonía con derrame, neumotórax, disección aórtica, pericarditis.
- **Notas críticas:**
  - Combinaciones de **factores de riesgo del chart (anticonceptivo + vuelo + tabaco; o cáncer + inmovilización)** deben elevar la probabilidad pre-test (criterios de Wells implícitos).

---

### 11.3 Enfermedad de Addison (Insuficiencia Suprarrenal Primaria)

#### Consulta sin chart

```
Paciente que desde hace meses presenta cansancio extremo, pérdida de peso, dolor abdominal vago, náuseas y mareo al ponerse de pie. Ha notado que la piel se le ha oscurecido, sobre todo en pliegues, codos y encías. Tiene antojo de cosas saladas.
```

#### Chart — HOMBRE

- **Age:** 36
- **Sex:** M
- **Comorbidities:** vitíligo
- **Chief Complaint:** Astenia, hipotensión postural y pérdida de 9 kg en 4 meses
- **Vital Signs:** HR 102 (de pie) · BP 92/56 (acostado) → 78/48 (de pie) · RR 16 · SpO2 98 · Temp 36.4
- **Physical Findings:** Hiperpigmentación en pliegues palmares, codos, mucosa oral; manchas acrómicas dispersas (vitíligo).
- **Lab Results:** Na 128, K 5.6, glucosa 68, urea normal, cortisol matutino 2.1 µg/dL, ACTH 480 pg/mL (elevadísima).
- **Imaging:** TC abdomen con suprarrenales atróficas.
- **Current Medications:** ninguna
- **Allergies:** NKDA
- **Social History:** Profesor, no fumador
- **Family History:** Hermana con tiroiditis de Hashimoto, tía con diabetes tipo 1
- **Additional Notes:** Episodio de "lipotimia" hace 1 mes en una boda.

#### Chart — MUJER

- **Age:** 48
- **Sex:** F
- **Comorbidities:** hipotiroidismo autoinmune en tratamiento
- **Chief Complaint:** Náuseas, vómitos y dolor abdominal de inicio insidioso, sensación de "no poder más"
- **Vital Signs:** HR 110 · BP 86/52 · RR 18 · SpO2 97 · Temp 37.2
- **Physical Findings:** Mucosas hiperpigmentadas, lengua con bordes oscuros, deshidratación leve.
- **Lab Results:** Na 124, K 5.9, glucosa 62, cortisol < 1, ACTH 720, anticuerpos anti-21-hidroxilasa positivos.
- **Imaging:** Suprarrenales atróficas en TC.
- **Current Medications:** levotiroxina 100 mcg
- **Allergies:** NKDA
- **Social History:** Auxiliar administrativa
- **Family History:** Madre con enfermedad celíaca, hermano con DM1
- **Additional Notes:** Episodio de hipotensión grave durante una gastroenteritis hace 2 semanas (sospecha de crisis adrenal).

#### Salida esperada

- **Top-1 esperado:** Enfermedad de Addison (insuficiencia suprarrenal primaria autoinmune, en el contexto de síndrome poliglandular autoinmune tipo II).
- **Diferenciales plausibles:** Insuficiencia suprarrenal secundaria (descartada por ACTH alta), depresión mayor, anorexia, sepsis crónica, hemocromatosis.
- **Notas críticas:**
  - Hiperpigmentación + Na bajo + K alto + ACTH alta = patrón muy específico.
  - El antecedente de vitíligo / Hashimoto orienta a etiología autoinmune (síndrome poliglandular).

---

### 11.4 Síndrome de Cushing

#### Consulta sin chart

```
Paciente con aumento de peso en los últimos 18 meses concentrado en cara y tronco, con brazos y piernas adelgazadas. Ha aparecido cara redondeada y rojiza, joroba en la espalda, estrías rojo-vinosas anchas en el abdomen, hematomas fáciles, debilidad muscular en muslos y elevación de la presión arterial. La paciente refiere también ciclos menstruales irregulares y aumento del vello facial.
```

#### Chart — HOMBRE

- **Age:** 44
- **Sex:** M
- **Comorbidities:** HTA de difícil control, diabetes recién diagnosticada, osteoporosis a edad joven
- **Chief Complaint:** Aumento de peso central, debilidad para subir escaleras y cambios en la piel
- **Vital Signs:** HR 86 · BP 168/102 · RR 14 · SpO2 97 · Temp 36.5
- **Physical Findings:** Facies de luna llena, plétora facial, giba dorsal, atrofia de musculatura proximal, estrías violáceas abdominales > 1 cm, hematomas en antebrazos.
- **Lab Results:** Cortisol libre urinario 24h elevado x4, cortisol salival nocturno elevado, test de supresión con 1 mg de dexametasona sin supresión, ACTH 85 pg/mL.
- **Imaging:** RM hipófisis con microadenoma de 6 mm.
- **Current Medications:** amlodipino, hidroclorotiazida, metformina
- **Allergies:** NKDA
- **Social History:** Contador
- **Family History:** Sin relevancia
- **Additional Notes:** Hace 6 meses fractura por estrés en pie sin trauma claro.

#### Chart — MUJER

- **Age:** 52
- **Sex:** F
- **Comorbidities:** asma bronquial
- **Chief Complaint:** Aumento de peso, debilidad y cambios en el rostro
- **Vital Signs:** HR 80 · BP 152/94 · RR 16 · SpO2 98 · Temp 36.6
- **Physical Findings:** Cushingoide, hirsutismo facial, acné, estrías rojas, equimosis múltiples.
- **Lab Results:** Cortisol urinario libre elevado, ACTH suprimida (<5), test de supresión sin respuesta.
- **Imaging:** TC abdomen con masa suprarrenal derecha de 3.5 cm.
- **Current Medications:** **prednisona 20 mg/día crónica** por asma severa desde hace 3 años, salbutamol, budesonida inhalada.
- **Allergies:** AINEs
- **Social History:** Ama de casa
- **Family History:** Sin relevancia
- **Additional Notes:** *Distractor real:* la paciente usa corticoides crónicos, pero los estudios bioquímicos muestran ACTH suprimida con masa suprarrenal → **Cushing endógeno suprarrenal coexistente con Cushing iatrogénico**.

#### Salida esperada

- **Top-1 esperado:**
  - **Hombre:** Enfermedad de Cushing (adenoma hipofisario ACTH-dependiente).
  - **Mujer:** Síndrome de Cushing iatrogénico (por corticoides) — pero el hallazgo de la masa suprarrenal con ACTH suprimida debe alertar de Cushing endógeno suprarrenal.
- **Diferenciales plausibles:** Síndrome metabólico, pseudo-Cushing por depresión/alcohol, hipotiroidismo, obesidad simple con HTA, hiperplasia suprarrenal congénita.
- **Notas críticas:**
  - Mujer: caso especialmente complejo para evaluar si el sistema **diferencia las dos etiologías coexistentes**.

---

### 11.5 Enfermedad de Parkinson

#### Consulta sin chart

```
Paciente de 68 años que en los últimos dos años ha desarrollado temblor en una mano que aparece en reposo y desaparece al moverla, lentitud al caminar con pasos cortos, dificultad para iniciar la marcha y rigidez en brazo derecho. Su esposa refiere que se ha vuelto inexpresivo, habla más bajo y se le cae la saliva por la noche. También nota que ha perdido el olfato.
```

#### Chart — HOMBRE

- **Age:** 68
- **Sex:** M
- **Comorbidities:** HTA, depresión leve en seguimiento
- **Chief Complaint:** Temblor en mano derecha y enlentecimiento progresivo de 2 años
- **Vital Signs:** HR 72 · BP 138/82 (acostado) → 116/72 (de pie) · RR 14 · SpO2 97 · Temp 36.6
- **Physical Findings:** Bradicinesia, hipomimia, temblor en reposo derecho (4-6 Hz), rigidez en rueda dentada derecha, marcha con pasos cortos, pérdida del braceo derecho. Reflejo glabelar no inhibido.
- **Lab Results:** Bioquímica básica normal, TSH normal, B12 normal.
- **Imaging:** RM cerebral con atrofia inespecífica, sin lesiones isquémicas significativas. DaT-SCAN: hipocaptación en putamen izquierdo.
- **Current Medications:** enalapril, sertralina 50 mg
- **Allergies:** NKDA
- **Social History:** Jubilado, no fuma, alcohol ocasional
- **Family History:** Padre con "temblor en la vejez", hermano sin antecedentes
- **Additional Notes:** Su esposa refiere que tiene sueños vívidos donde "actúa" lo que sueña (sospecha de RBD), y que ha perdido el olfato desde hace años.

#### Chart — MUJER

- **Age:** 73
- **Sex:** F
- **Comorbidities:** osteoporosis, estreñimiento crónico
- **Chief Complaint:** Caídas y dificultad para escribir
- **Vital Signs:** HR 70 · BP 128/76 · RR 14 · SpO2 98 · Temp 36.5
- **Physical Findings:** Micrografía evidente, bradicinesia, rigidez axial, postura en flexión, marcha festinante. Sin afectación oculomotora.
- **Lab Results:** Normal.
- **Imaging:** TC craneal sin lesiones; DaT-SCAN positivo.
- **Current Medications:** calcio + vit D, alendronato semanal, lactulosa
- **Allergies:** NKDA
- **Social History:** Vive sola, costurera retirada
- **Family History:** Sin antecedentes neurológicos
- **Additional Notes:** Estreñimiento severo desde hace 10 años (síntoma prodrómico clásico).

#### Salida esperada

- **Top-1 esperado:** Enfermedad de Parkinson idiopática.
- **Diferenciales plausibles:** Parkinsonismo vascular, atrofia multisistémica (AMS), parálisis supranuclear progresiva (PSP), parkinsonismo inducido por fármacos, temblor esencial.
- **Notas críticas:**
  - El RBD + anosmia + estreñimiento son **síntomas premotores característicos** — si el sistema los integra, debe priorizar Parkinson sobre temblor esencial.

---

### 11.6 Esclerosis Múltiple

#### Consulta sin chart

```
Mujer joven que hace 6 meses presentó pérdida de visión en un ojo con dolor al moverlo, que se recuperó en semanas. Ahora consulta porque desde hace 10 días tiene hormigueo y debilidad en la pierna derecha que va empeorando, sensación de descarga eléctrica en la espalda al flexionar el cuello, y problemas para controlar la vejiga.
```

#### Chart — HOMBRE

- **Age:** 32
- **Sex:** M
- **Comorbidities:** ninguna
- **Chief Complaint:** Diplopía e inestabilidad de la marcha de 2 semanas
- **Vital Signs:** HR 76 · BP 122/78 · RR 14 · SpO2 99 · Temp 36.7
- **Physical Findings:** Oftalmoplejía internuclear izquierda, hiperreflexia 4/4 en MID, Babinski derecho positivo, signo de Lhermitte+.
- **Lab Results:** Hemograma normal, B12 normal, VIH negativo, función tiroidea normal.
- **Imaging:** RM cerebral y medular con múltiples lesiones T2 hiperintensas periventriculares, yuxtacorticales y en cuerpo calloso ("dedos de Dawson"). Lesión activa con realce en gadolinio.
- **Current Medications:** ninguna
- **Allergies:** NKDA
- **Social History:** Ingeniero, vive en latitud norte (vitamina D baja por estilo de vida)
- **Family History:** Tía materna con "enfermedad neurológica que la dejó en silla de ruedas"
- **Additional Notes:** LCR con bandas oligoclonales positivas, no presentes en suero.

#### Chart — MUJER

- **Age:** 28
- **Sex:** F
- **Comorbidities:** ninguna
- **Chief Complaint:** Parestesias en hemicuerpo derecho y disfunción vesical
- **Vital Signs:** HR 78 · BP 118/72 · RR 14 · SpO2 99 · Temp 36.6
- **Physical Findings:** Hipoestesia táctil hemicorporal derecha por debajo de D8, ataxia leve, urgencia miccional.
- **Lab Results:** Bioquímica normal, anti-AQP4 negativos, anti-MOG negativos, bandas oligoclonales positivas en LCR.
- **Imaging:** RM con lesiones desmielinizantes diseminadas en tiempo y espacio.
- **Current Medications:** anticonceptivo oral
- **Allergies:** NKDA
- **Social History:** Diseñadora, no fumadora
- **Family History:** Sin enfermedades autoinmunes conocidas
- **Additional Notes:** Hace 6 meses neuritis óptica del ojo izquierdo que se recuperó parcialmente.

#### Salida esperada

- **Top-1 esperado:** Esclerosis múltiple recurrente-remitente.
- **Diferenciales plausibles:** Neuromielitis óptica (NMO/Devic — descartada por anti-AQP4 negativo), encefalomielitis aguda diseminada (ADEM), enfermedad por anti-MOG, sarcoidosis neurológica, déficit de B12, vasculitis del SNC.
- **Notas críticas:**
  - Lhermitte + neuritis óptica + lesiones en RM con dedos de Dawson + bandas oligoclonales = criterios de McDonald para EM.

---

### 11.7 Lupus Eritematoso Sistémico

#### Consulta sin chart

```
Mujer joven con cansancio extremo, dolor en articulaciones de manos y muñecas sin deformidad, erupción rojiza en mejillas que respeta los surcos nasogenianos y empeora con el sol, aftas en boca, caída de cabello, episodios de palidez y dolor en los dedos al frío. Refiere también dolor torácico que mejora al inclinarse hacia adelante.
```

#### Chart — HOMBRE

- **Age:** 29
- **Sex:** M
- **Comorbidities:** ninguna
- **Chief Complaint:** Poliartritis, fiebre y pérdida de peso de 2 meses
- **Vital Signs:** HR 96 · BP 138/86 · RR 18 · SpO2 97 · Temp 37.9
- **Physical Findings:** Eritema malar tenue, úlceras palatinas indoloras, derrame pleural derecho leve, edema maleolar.
- **Lab Results:** ANA 1:1280 patrón homogéneo, anti-dsDNA positivos altos, anti-Sm positivos, C3/C4 bajos, Coombs+, proteinuria 2.1 g/24h, sedimento con cilindros hemáticos.
- **Imaging:** Rx tórax con derrame pleural derecho. Ecocardio con derrame pericárdico leve.
- **Current Medications:** ninguna
- **Allergies:** NKDA
- **Social History:** Estudiante de doctorado
- **Family History:** Hermana con tiroiditis autoinmune
- **Additional Notes:** Biopsia renal pendiente (sospecha de nefritis lúpica clase IV).

#### Chart — MUJER

- **Age:** 26
- **Sex:** F
- **Comorbidities:** ninguna
- **Chief Complaint:** Erupción facial, dolor articular y fatiga de 4 meses
- **Vital Signs:** HR 90 · BP 124/78 · RR 16 · SpO2 98 · Temp 37.4
- **Physical Findings:** Eritema malar en "alas de mariposa" que respeta surcos nasogenianos, alopecia difusa, fenómeno de Raynaud trifásico en manos.
- **Lab Results:** ANA 1:640, anti-dsDNA positivos, anti-Ro positivos, C3 bajo, leucopenia 3200, linfopenia, plaquetas 95.000.
- **Imaging:** Sin hallazgos.
- **Current Medications:** anticonceptivo combinado (a suspender)
- **Allergies:** sulfas
- **Social History:** Diseñadora, expuesta a sol intenso por hobby
- **Family History:** Tía con artritis reumatoide
- **Additional Notes:** Antecedente de 2 abortos espontáneos en primer trimestre (descartar SAF asociado: anticoagulante lúpico pendiente).

#### Salida esperada

- **Top-1 esperado:** Lupus eritematoso sistémico (criterios EULAR/ACR 2019).
- **Diferenciales plausibles:** Artritis reumatoide, dermatomiositis, enfermedad mixta del tejido conectivo, síndrome de Sjögren, lupus inducido por fármacos.
- **Notas críticas:**
  - Hombre: presentación atípica por género — el sistema **no** debe descartar LES por ser varón (representa ~10% de casos).

---

### 11.8 Insuficiencia Cardíaca Congestiva

#### Consulta sin chart

```
Paciente que en las últimas semanas presenta dificultad para respirar al hacer esfuerzos cada vez menores, debe dormir con varias almohadas porque al acostarse se ahoga y se despierta de noche con falta de aire que mejora al sentarse. Tiene los tobillos hinchados, ha aumentado 4 kilos sin cambios en la dieta y nota palpitaciones.
```

#### Chart — HOMBRE

- **Age:** 70
- **Sex:** M
- **Comorbidities:** IAM hace 5 años con stent en DA, HTA, DM2, fibrilación auricular permanente
- **Chief Complaint:** Disnea de pequeños esfuerzos, ortopnea de 3 almohadas y edemas
- **Vital Signs:** HR 104 (irregular) · BP 102/68 · RR 24 · SpO2 92 · Temp 36.5
- **Physical Findings:** Ingurgitación yugular, crepitantes bibasales, edema con fóvea hasta rodillas, hepatomegalia dolorosa, reflujo hepatoyugular+.
- **Lab Results:** BNP 1850 pg/mL, troponina negativa, creatinina 1.7, Na 132, K 4.4.
- **Imaging:** Rx tórax con cardiomegalia, redistribución vascular y derrame pleural bilateral. Ecocardio: FEVI 28%, dilatación de cavidades izquierdas, IM moderada.
- **Current Medications:** AAS, atorvastatina, carvedilol, enalapril, furosemida, dapagliflozina, apixabán
- **Allergies:** NKDA
- **Social History:** Jubilado, ex-fumador
- **Family History:** Padre IC, hermano IAM
- **Additional Notes:** Refiere haber dejado de tomar furosemida hace 1 semana por "ir mucho al baño".

#### Chart — MUJER

- **Age:** 78
- **Sex:** F
- **Comorbidities:** HTA de larga evolución, obesidad, DM2, ERC estadio 3
- **Chief Complaint:** Disnea progresiva y aumento del perímetro abdominal
- **Vital Signs:** HR 88 · BP 168/92 · RR 22 · SpO2 93 · Temp 36.4
- **Physical Findings:** Crepitantes bibasales, edemas, ascitis leve, IY visible.
- **Lab Results:** BNP 720, creatinina 1.6, función tiroidea normal.
- **Imaging:** Ecocardio: **FEVI 60% conservada**, hipertrofia VI severa, disfunción diastólica grado III, dilatación AI.
- **Current Medications:** losartán, amlodipino, metformina, espironolactona
- **Allergies:** NKDA
- **Social History:** Vive con su hija
- **Family History:** HTA materna
- **Additional Notes:** Caso de IC con fracción de eyección preservada (HFpEF), patrón cada vez más frecuente en mujeres mayores con HTA.

#### Salida esperada

- **Top-1 esperado:** Insuficiencia cardíaca (HFrEF en el hombre, HFpEF en la mujer).
- **Diferenciales plausibles:** EPOC reagudizada, embolia pulmonar crónica, anemia, hipotiroidismo, síndrome nefrótico, cirrosis hepática.
- **Notas críticas:**
  - El sistema debe **distinguir HFrEF vs HFpEF** según FEVI del chart — implicaciones terapéuticas distintas.

---

### 11.9 Pancreatitis Aguda

#### Consulta sin chart

```
Paciente que tras una comida copiosa con alcohol presenta dolor intenso en epigastrio que irradia hacia la espalda en cinturón, acompañado de náuseas, vómitos persistentes y distensión abdominal. El dolor mejora al inclinarse hacia adelante y empeora al acostarse.
```

#### Chart — HOMBRE

- **Age:** 52
- **Sex:** M
- **Comorbidities:** dislipidemia (triglicéridos elevados), alcoholismo crónico
- **Chief Complaint:** Dolor epigástrico irradiado a espalda, vómitos y fiebre de 18 horas
- **Vital Signs:** HR 118 · BP 96/58 · RR 24 · SpO2 94 · Temp 38.4
- **Physical Findings:** Abdomen distendido y doloroso en epigastrio, signo de Grey-Turner incipiente, sin defensa peritoneal franca. Equimosis periumbilical (Cullen) ausente.
- **Lab Results:** Amilasa 1840, lipasa 4200, leucocitos 18.000, calcio 7.2, LDH 480, AST 320, glucosa 220, triglicéridos 1.850 mg/dL, PCR 280.
- **Imaging:** TC abdomen con páncreas aumentado, áreas de necrosis < 30%, líquido peripancreático (Balthazar D).
- **Current Medications:** ninguna habitual
- **Allergies:** NKDA
- **Social History:** Bebedor de 6-8 cervezas/día durante 20 años, fumador
- **Family History:** Sin relevancia
- **Additional Notes:** Episodio previo de pancreatitis leve hace 2 años.

#### Chart — MUJER

- **Age:** 58
- **Sex:** F
- **Comorbidities:** colelitiasis conocida (no operada)
- **Chief Complaint:** Dolor abdominal súbito en epigastrio postprandial, vómitos
- **Vital Signs:** HR 102 · BP 122/78 · RR 18 · SpO2 96 · Temp 37.6
- **Physical Findings:** Ictericia leve, dolor a la palpación en hipocondrio derecho y epigastrio, Murphy positivo.
- **Lab Results:** Amilasa 1620, lipasa 3800, bilirrubina total 4.8 (directa 3.6), ALT 380, AST 290, FA 420, GGT 380, leucocitos 14.500.
- **Imaging:** Eco abdominal con vesícula litiásica, vía biliar dilatada (8 mm), coledocolitiasis sospechada. TC con páncreas edematoso sin necrosis.
- **Current Medications:** losartán
- **Allergies:** NKDA
- **Social History:** No bebe, no fuma
- **Family History:** Madre colecistectomizada
- **Additional Notes:** No es bebedora — la pancreatitis es de **origen biliar**.

#### Salida esperada

- **Top-1 esperado:** Pancreatitis aguda (alcohólica/hipertrigliceridémica en hombre; biliar en mujer).
- **Diferenciales plausibles:** Úlcera péptica perforada, colecistitis aguda, infarto agudo de miocardio inferior, isquemia mesentérica, aneurisma aórtico.
- **Notas críticas:**
  - El sistema debe **identificar la etiología** según chart (alcohol/TG vs. biliar) — afecta el manejo (CPRE urgente en biliar).
  - Mujer: dolor irradiado al hombro derecho podría confundir con colecistitis pura — la lipasa altísima define pancreatitis.

---

### 11.10 Feocromocitoma

#### Consulta sin chart

```
Paciente con episodios paroxísticos de cefalea intensa, sudoración profusa y palpitaciones, asociados a picos de presión arterial muy altos que aparecen y desaparecen. Entre los episodios se siente bien. Refiere ansiedad, pérdida de peso y palidez durante las crisis. Un episodio se desencadenó al hacer fuerza en el baño.
```

#### Chart — HOMBRE

- **Age:** 42
- **Sex:** M
- **Comorbidities:** HTA de difícil control (3 fármacos sin control)
- **Chief Complaint:** Cefaleas paroxísticas con cifras tensionales de 220/130 mmHg
- **Vital Signs (intercrisis):** HR 88 · BP 154/96 · RR 14 · SpO2 98 · Temp 36.7
- **Vital Signs (crisis):** HR 138 · BP 230/132 · diaforesis profusa
- **Physical Findings:** Palidez durante la crisis, sin masas palpables abdominales, fondo de ojo con retinopatía hipertensiva grado II.
- **Lab Results:** Metanefrinas plasmáticas libres 3.8 nmol/L (muy elevadas), normetanefrinas urinarias 24h x6 el límite, cromogranina A elevada.
- **Imaging:** TC abdomen con masa suprarrenal derecha de 4.5 cm heterogénea. MIBG con captación intensa en la masa.
- **Current Medications:** amlodipino, losartán, hidroclorotiazida (suspender betabloqueante por riesgo de crisis)
- **Allergies:** NKDA
- **Social History:** Empresario
- **Family History:** Padre con HTA. Sin antecedentes de NEM o von Hippel-Lindau conocidos (pero pendiente estudio genético).
- **Additional Notes:** Episodio de edema agudo de pulmón hace 3 meses atribuido a "crisis hipertensiva".

#### Chart — MUJER

- **Age:** 38
- **Sex:** F
- **Comorbidities:** ninguna conocida; antecedente familiar de hemangioblastomas cerebelosos
- **Chief Complaint:** Crisis de palpitaciones, cefalea y sudoración con HTA súbita
- **Vital Signs (intercrisis):** HR 80 · BP 132/82 · RR 14 · SpO2 99 · Temp 36.5
- **Physical Findings:** Sin focalidad, fondo de ojo con angiomas retinianos (von Hippel-Lindau).
- **Lab Results:** Metanefrinas plasmáticas elevadas, glucosa 138 en crisis.
- **Imaging:** RM abdomen con masas suprarrenales bilaterales pequeñas (1.8 y 2.2 cm). RM cerebral con hemangioblastoma cerebeloso.
- **Current Medications:** ninguna
- **Allergies:** NKDA
- **Social History:** Investigadora
- **Family History:** Padre y hermano con enfermedad de von Hippel-Lindau confirmada
- **Additional Notes:** Estudio genético confirma mutación VHL — feocromocitoma bilateral en el contexto sindrómico.

#### Salida esperada

- **Top-1 esperado:** Feocromocitoma.
- **Diferenciales plausibles:** HTA esencial resistente, crisis de pánico, hipertiroidismo, síndrome carcinoide, abuso de cocaína/anfetaminas, hipoglucemia con respuesta adrenérgica.
- **Notas críticas:**
  - Mujer: caso en el contexto de **von Hippel-Lindau** — el sistema debe reconocer que los feocromocitomas bilaterales jóvenes obligan a buscar síndrome genético.
  - Distractor importante: **trastorno de pánico** comparte síntomas — el chart debe inclinar hacia feocromocitoma por las metanefrinas y la imagen.

---

## Apéndice — Plantilla de Registro de Resultados

Para cada caso, registrar:

```
Caso: [nombre]
Modo: [sin chart | con chart hombre | con chart mujer]
Search mode: [standard | web | positioned]

Top-1 obtenido: ___________________
Top-3 obtenidos: ___________________
¿Coincide con esperado? [sí | no | parcial]
¿Citaciones válidas? [sí | no]
¿Activó banner de insuficiencia? [sí | no]
¿Activó web enrichment? [sí | no]

Observaciones:
- 
- 
```
