import streamlit as st
import pandas as pd

# ==========================================
# 0. CONFIGURARE & STILIZARE
# ==========================================
st.set_page_config(
    page_title="ADA/EASD 2022 Diabetes Architect",
    page_icon="🧬",
    layout="wide"
)

# CSS Avansat pentru a diferenția acțiunile
st.markdown("""
    <style>
    .action-stop { border-left: 6px solid #d9534f; background-color: #fff5f5; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-start { border-left: 6px solid #28a745; background-color: #f0fff4; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-switch { border-left: 6px solid #007bff; background-color: #eef7ff; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-alert { border-left: 6px solid #ffc107; background-color: #fffbf0; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .citation { font-size: 0.85em; color: #666; font-style: italic; margin-top: 5px; }
    .metric-box { text-align: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

DISCLAIMER = "⚠️ **CLINICAL DECISION SUPPORT**: Algoritm bazat pe Raportul de Consens ADA/EASD 2022. Nu înlocuiește judecata clinică."

# ==========================================
# 1. CLASE DE DEFINIȚIE (BAZA DE CUNOȘTINȚE)
# ==========================================
# Definiții bazate pe textul furnizat (Table 1 & Text)
DRUG_CLASSES = {
    "Metformin": {"type": "Oral", "contra_egfr": 30, "warning_egfr": 45},
    "SGLT2i": {"type": "Oral", "contra_egfr": 20, "benefit": ["HF", "CKD", "ASCVD"]}, # Text: eGFR initiated >=20 for CKD
    "GLP1_RA": {"type": "Injectable", "contra_egfr": 15, "benefit": ["ASCVD", "Weight", "CKD_Secondary"]}, 
    "GIP_GLP1": {"type": "Injectable", "contra_egfr": 15, "benefit": ["Weight++", "Glycemia++"]}, # Tirzepatide
    "DPP4i": {"type": "Oral", "contra_egfr": 0, "conflict": ["GLP1_RA", "GIP_GLP1"]},
    "SU": {"type": "Oral", "contra_egfr": 60, "risk": "Hypo"}, 
    "TZD": {"type": "Oral", "contra": "HF"},
    "Insulin_Basal": {"type": "Injectable", "risk": "Hypo"},
    "Insulin_Prandial": {"type": "Injectable", "risk": "Hypo"}
}

# ==========================================
# 2. UI - INPUT DATE (SIDEBAR)
# ==========================================
st.sidebar.title("🧬 Clinical Input")
st.sidebar.caption("Conform ADA/EASD Consensus 2022")

st.sidebar.subheader("Profil Pacient")
c1, c2 = st.sidebar.columns(2)
age = c1.number_input("Vârsta (ani)", 18, 100, 55)
weight = c2.number_input("Greutate (kg)", 40, 250, 95)
height = st.sidebar.number_input("Înălțime (cm)", 100, 240, 175)
bmi = weight / ((height/100)**2)
st.sidebar.markdown(f"**BMI:** {bmi:.1f} kg/m²")

st.sidebar.subheader("Laborator")
hba1c = st.sidebar.number_input("HbA1c (%)", 4.0, 18.0, 8.2, step=0.1)
target_a1c = st.sidebar.selectbox("Țintă HbA1c", [6.5, 7.0, 7.5, 8.0], index=1)
egfr = st.sidebar.number_input("eGFR (mL/min)", 5, 140, 45)
acr = st.sidebar.selectbox("Albuminurie (uACR)", ["A1 Normal (<30 mg/g)", "A2 Micro (30-300 mg/g)", "A3 Macro (>300 mg/g)"])

st.sidebar.subheader("Comorbidități (Cardiorenal)")
ascvd = st.sidebar.checkbox("ASCVD (Infarct, AVC, PAD)")
hf = st.sidebar.checkbox("Insuficiență Cardiacă (HF)")
ckd_dx = st.sidebar.checkbox("Diagnostic CKD (Boală Renală)")
if acr != "A1 Normal (<30 mg/g)": ckd_dx = True 

st.sidebar.subheader("Schema Actuală")
current_meds = []
if st.sidebar.checkbox("Metformin"): current_meds.append("Metformin")
if st.sidebar.checkbox("SGLT2i (Dapa/Empa/Cana)"): current_meds.append("SGLT2i")
if st.sidebar.checkbox("GLP-1 RA (Sema/Dula/Lira)"): current_meds.append("GLP1_RA")
if st.sidebar.checkbox("GIP/GLP-1 RA (Tirzepatide)"): current_meds.append("GIP_GLP1")
if st.sidebar.checkbox("DPP-4i (Sita/Lina/Vilda)"): current_meds.append("DPP4i")
if st.sidebar.checkbox("Sulfoniluree (SU)"): current_meds.append("SU")
if st.sidebar.checkbox("TZD (Pioglitazona)"): current_meds.append("TZD")
if st.sidebar.checkbox("Insulină Bazală"): current_meds.append("Insulin_Basal")
if st.sidebar.checkbox("Insulină Prandială"): current_meds.append("Insulin_Prandial")

# ==========================================
# 3. MOTORUL DE DECIZIE
# ==========================================
def generate_plan(meds, hba1c, target, egfr, bmi, ascvd, hf, ckd, age):
    plan = [] 
    simulated_meds = meds.copy()
    
    # -----------------------------------------------------
    # PASUL 1: SIGURANȚĂ & SANITIZARE
    # -----------------------------------------------------
    
    # Metformin eGFR
    if "Metformin" in simulated_meds:
        if egfr < 30:
            plan.append({
                "type": "STOP",
                "text": "OPRIȚI Metformin",
                "reason": "Contraindicație: eGFR < 30 ml/min.",
                "ref": "Consensus Report: Table 1"
            })
            simulated_meds.remove("Metformin")
        elif egfr < 45:
            plan.append({
                "type": "ALERT",
                "text": "Reduceți doza Metformin",
                "reason": "Considerați reducerea dozei la eGFR < 45.",
                "ref": "Consensus Report: Other glucose-lowering medications"
            })

    # SGLT2i eGFR
    if "SGLT2i" in simulated_meds and egfr < 20:
        plan.append({
            "type": "STOP",
            "text": "STOP SGLT2i",
            "reason": "Inițierea nu este recomandată la eGFR < 20 (deși unele studii permit continuarea până la dializă).",
            "ref": "DAPA-CKD / EMPA-KIDNEY criteria"
        })
        simulated_meds.remove("SGLT2i")

    # TZD in HF
    if "TZD" in simulated_meds and hf:
        plan.append({
            "type": "STOP",
            "text": "OPRIȚI TZD (Pioglitazona)",
            "reason": "Risc de retenție lichidiană și agravare HF.",
            "ref": "Consensus Report: Thiazolidinediones"
        })
        simulated_meds.remove("TZD")
        
    # Redundanță Incretinică (DPP4 + GLP1 sau DPP4 + Tirzepatide)
    has_potent_incretin = ("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds)
    if "DPP4i" in simulated_meds and has_potent_incretin:
        plan.append({
            "type": "STOP",
            "text": "OPRIȚI DPP-4i",
            "reason": "Nu combinați DPP-4i cu GLP-1 RA sau GIP/GLP-1 RA (mecanisme similare, eficacitate net superioară la injectabile).",
            "ref": "Consensus Report: Principles of Care"
        })
        simulated_meds.remove("DPP4i")

    # -----------------------------------------------------
    # PASUL 2: PROTECȚIE DE ORGAN (Independent de A1c & Metformin)
    # -----------------------------------------------------
    
    # HF -> SGLT2i Mandatory
    if hf and "SGLT2i" not in simulated_meds and egfr >= 20:
        plan.append({
            "type": "START",
            "text": "INIȚIAȚI SGLT2i (Dapa/Empa)",
            "reason": "Beneficiu dovedit în reducerea HHF și mortalității CV în HF.",
            "ref": "Consensus Rec: People with HF"
        })
        simulated_meds.append("SGLT2i")
    
    # CKD -> SGLT2i Preferred
    if ckd and "SGLT2i" not in simulated_meds and egfr >= 20:
        plan.append({
            "type": "START",
            "text": "INIȚIAȚI SGLT2i",
            "reason": "Preferat pentru încetinirea progresiei CKD și reducerea HHF.",
            "ref": "Consensus Rec: People with CKD"
        })
        simulated_meds.append("SGLT2i")
    elif ckd and "SGLT2i" not in simulated_meds and egfr < 20:
        # Fallback to GLP1 if SGLT2 contraindicated
        if "GLP1_RA" not in simulated_meds and "GIP_GLP1" not in simulated_meds:
             plan.append({
                "type": "START",
                "text": "INIȚIAȚI GLP-1 RA",
                "reason": "Alternativă pentru reducerea riscului MACE și albuminuriei când SGLT2i nu poate fi folosit.",
                "ref": "Consensus Rec: CKD alternative"
            })

    # ASCVD -> GLP-1 RA or SGLT2i
    if ascvd:
        has_protection = ("SGLT2i" in simulated_meds) or ("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds)
        if not has_protection:
            plan.append({
                "type": "START",
                "text": "INIȚIAȚI GLP-1 RA sau SGLT2i",
                "reason": "Pacienții cu ASCVD trebuie să primească agent cu beneficiu CV dovedit, independent de A1c.",
                "ref": "Consensus Rec: People with established CVD"
            })
            # Logic: prefer GLP-1 if BMI high, else SGLT2
            if bmi > 27:
                simulated_meds.append("GLP1_RA")
            else:
                simulated_meds.append("SGLT2i")

    # -----------------------------------------------------
    # PASUL 3: INTENSIFICARE GLICEMICĂ & PONDERALĂ
    # -----------------------------------------------------
    gap = hba1c - target
    
    # Regula pentru Tineri (<40 ani) - Early Combination
    if age < 40 and len(simulated_meds) < 2 and hba1c > target:
         plan.append({
            "type": "START",
            "text": "Considerați Terapie Combinată Precoce",
            "reason": "La tineri (<40 ani), progresia bolii e rapidă. Combinația timpurie (ex. Metformin + inhibitor) e superioară (VERIFY Trial).",
            "ref": "Consensus Report: Age/Younger people"
        })

    if gap > 0:
        # 3.1 Metformin Base
        if "Metformin" not in simulated_meds and egfr >= 30:
            plan.append({
                "type": "START",
                "text": "ADĂUGAȚI Metformin",
                "reason": "Terapie de primă linie, eficacitate înaltă, cost redus.",
                "ref": "Consensus Report: Other medications"
            })
            simulated_meds.append("Metformin")
            
        # 3.2 Managementul Greutății este "Primary Target"
        # Dacă nu e pe un agent potent de slăbit și are BMI mare
        has_weight_drug = ("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds) or ("SGLT2i" in simulated_meds)
        
        if bmi >= 30 and not has_weight_drug:
             plan.append({
                "type": "START",
                "text": "ADĂUGAȚI GLP-1 RA sau GIP/GLP-1 RA",
                "reason": "Obezitatea este țintă primară. Tirzepatide (GIP/GLP-1) sau Semaglutide au eficacitate 'Very High' pe greutate.",
                "ref": "Consensus Report: Weight management"
            })
             simulated_meds.append("GIP_GLP1")

        # 3.3 Switch DPP-4i la GLP-1/Tirzepatide
        elif "DPP4i" in simulated_meds and gap > 0.5:
             plan.append({
                "type": "SWITCH",
                "text": "ÎNLOCUIȚI DPP-4i cu GLP-1 RA sau Tirzepatide",
                "reason": "DPP-4i are eficacitate modestă. GLP-1/GIP-GLP1 au eficacitate înaltă/foarte înaltă.",
                "ref": "Consensus Report: Comparative efficacy"
            })
             simulated_meds.remove("DPP4i")
             simulated_meds.append("GLP1_RA")
        
        # 3.4 Bariera Insulinei (Regula "GLP-1 First")
        elif "Insulin_Basal" not in simulated_meds and ("GLP1_RA" not in simulated_meds and "GIP_GLP1" not in simulated_meds):
             # Dacă am ajuns aici și glicemia e mare, înainte de insulină, verificăm GLP-1
             if hba1c < 10: # Dacă e >10 poate e nevoie direct de insulină
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI GLP-1 RA (înainte de Insulină)",
                    "reason": "Considerați GLP-1 RA înaintea insulinei bazale (eficacitate similară/superioară, fără hipoglicemie, scădere ponderală).",
                    "ref": "Consensus Report: Place of Insulin"
                })
             else:
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI Insulină Bazală (+ GLP-1 RA)",
                    "reason": "HbA1c sever (>10%). Combinația Insulină + GLP-1 (Fixed Ratio) este ideală.",
                    "ref": "Consensus Report: Place of Insulin"
                })
                
        # 3.5 Intensificare la Insulină (dacă deja are GLP-1)
        elif ("GLP1_RA" in simulated_meds or "GIP_GLP1" in simulated_meds) and gap > 0:
             if "Insulin_Basal" not in simulated_meds:
                  plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI Insulină Bazală",
                    "reason": "Eșec pe terapie non-insulinică maximizată.",
                    "ref": "Consensus Report: Fig 5"
                })
             elif "Insulin_Prandial" not in simulated_meds and gap > 0:
                  plan.append({
                    "type": "START",
                    "text": "ADĂUGAȚI Insulină Prandială",
                    "reason": "Basal 'Failure'. Trecere la Basal-Bolus.",
                    "ref": ""
                })

    return plan

# ==========================================
# 4. AFIȘARE REZULTATE
# ==========================================
plan_actions = generate_plan(current_meds, hba1c, target_a1c, egfr, bmi, ascvd, hf, ckd_dx, age)

st.divider()

col_main, col_detail = st.columns([1.5, 1])

with col_main:
    st.header("📋 Plan de Acțiune Personalizat")
    
    if not plan_actions and hba1c <= target_a1c:
        st.success("✅ Pacientul este la țintă și pe medicație optimizată pentru protecția organelor.")
    elif not plan_actions and hba1c > target_a1c:
        st.warning("⚠️ Caz refractar. Opțiunile standard epuizate. Evaluare specialist pentru pompe/tehnologii avansate.")

    for item in plan_actions:
        icon = ""
        css_class = ""
        if item['type'] == 'STOP':
            icon = "⛔"
            css_class = "action-stop"
        elif item['type'] == 'START':
            icon = "✅"
            css_class = "action-start"
        elif item['type'] == 'SWITCH':
            icon = "🔄"
            css_class = "action-switch"
        else:
            icon = "⚠️"
            css_class = "action-alert"
        
        st.markdown(f"""
        <div class="{css_class}">
            <strong>{icon} {item['type']}: {item['text']}</strong><br>
            <span style="font-size:0.95em">{item['reason']}</span><br>
            <div class="citation">Sursă: {item['ref']}</div>
        </div>
        """, unsafe_allow_html=True)

with col_detail:
    st.subheader("Sumar Clinic & Fenotip")
    st.metric("Glicemie (HbA1c)", f"{hba1c}%", delta=f"{hba1c-target_a1c:.1f}% vs Țintă", delta_color="inverse")
    
    st.markdown("**Status Organ:**")
    if hf: st.warning("Insuficiență Cardiacă (Prioritate SGLT2i)")
    elif ckd_dx: st.warning("Boală Renală (Prioritate SGLT2i)")
    elif ascvd: st.warning("ASCVD (Prioritate GLP-1/SGLT2i)")
    else: st.success("Fără boală cardiorenală stabilită")
    
    if age < 40:
        st.info("ℹ️ Pacient Tânăr (<40 ani): Risc crescut de complicații pe termen lung. Agresivitate terapeutică necesară.")
    
    if bmi > 30:
        st.info("ℹ️ Obezitate: Managementul greutății este țintă primară (Tirzepatide/Semaglutide).")

st.divider()
st.markdown("### 📚 Logică Extrasă din ADA/EASD Consensus 2022")
with st.expander("Vezi detaliile algoritmului"):
    st.markdown("""
    1.  **Safety First:** Excluderea medicamentelor contraindicate pe baza eGFR (Metformin <30, SGLT2i <20 la inițiere) sau comorbidități (TZD în HF).
    2.  **Organ Protection:** Adăugarea agenților dovediți (SGLT2i, GLP-1 RA) *independent* de HbA1c sau utilizarea Metforminului, dacă există HF, CKD sau ASCVD.
    3.  **Tirzepatide (Nou):** Textul evidențiază Tirzepatide (GIP/GLP-1) ca având eficacitate superioară pe glicemie și greutate față de GLP-1 RA clasic.
    4.  **Insulin Positioning:** Algoritmul forțează evaluarea GLP-1 RA *înainte* de a trece la insulină, conform Fig. 5 din raport.
    5.  **De-Prescribing:** Identificarea redundanțelor (DPP-4i + GLP-1) și oprirea lor.
    """)
