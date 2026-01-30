import streamlit as st
import pandas as pd

# ==========================================
# 0. CONFIGURARE & STILIZARE
# ==========================================
st.set_page_config(
    page_title="Precision Diabetes Architect",
    page_icon="🧬",
    layout="wide"
)

# CSS Avansat pentru a diferenția acțiunile
st.markdown("""
    <style>
    .action-stop { border-left: 6px solid #d9534f; background-color: #fff5f5; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-start { border-left: 6px solid #28a745; background-color: #f0fff4; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-switch { border-left: 6px solid #007bff; background-color: #eef7ff; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .citation { font-size: 0.85em; color: #666; font-style: italic; margin-top: 5px; }
    .metric-box { text-align: center; padding: 10px; background: #f8f9fa; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

DISCLAIMER = "⚠️ **CLINICAL DECISION SUPPORT**: Acest algoritm aplică strict ghidurile ADA/EASD 2024. Nu înlocuiește judecata clinică. Verificați toleranța individuală."

# ==========================================
# 1. CLASE DE DEFINIȚIE (BAZA DE CUNOȘTINȚE)
# ==========================================
# Aici definim "inteligența" despre medicamente
DRUG_CLASSES = {
    "Metformin": {"type": "Oral", "contra_egfr": 30, "warning_egfr": 45},
    "SGLT2i": {"type": "Oral", "contra_egfr": 20, "benefit": ["HF", "CKD", "ASCVD"]},
    "GLP1_RA": {"type": "Injectable", "contra_egfr": 0, "benefit": ["ASCVD", "Weight", "CKD_Secondary"]}, # eGFR limits vary by agent, safe generally
    "DPP4i": {"type": "Oral", "contra_egfr": 0, "conflict": "GLP1_RA"},
    "SU": {"type": "Oral", "contra_egfr": 60, "risk": "Hypo"}, # Gliclazide safe lower, but general rule
    "TZD": {"type": "Oral", "contra": "HF"},
    "Insulin_Basal": {"type": "Injectable", "risk": "Hypo"},
    "Insulin_Prandial": {"type": "Injectable", "risk": "Hypo"}
}

# ==========================================
# 2. UI - INPUT DATE (SIDEBAR)
# ==========================================
st.sidebar.title("🧬 Clinical Input")

st.sidebar.subheader("Profil Biologic")
c1, c2 = st.sidebar.columns(2)
weight = c1.number_input("Greutate (kg)", 40, 250, 95)
height = c2.number_input("Înălțime (cm)", 100, 240, 175)
bmi = weight / ((height/100)**2)

st.sidebar.subheader("Laborator")
hba1c = st.sidebar.number_input("HbA1c (%)", 4.0, 18.0, 8.2, step=0.1)
target_a1c = st.sidebar.selectbox("Țintă HbA1c", [6.5, 7.0, 7.5, 8.0], index=1)
egfr = st.sidebar.number_input("eGFR (mL/min)", 5, 140, 45)
acr = st.sidebar.selectbox("Albuminurie (uACR)", ["A1 Normal (<30)", "A2 Micro (30-300)", "A3 Macro (>300)"])

st.sidebar.subheader("Fenotip & Comorbidități")
ascvd = st.sidebar.checkbox("ASCVD (Infarct, AVC, PAD)")
hf = st.sidebar.checkbox("Insuficiență Cardiacă (HFrEF/pEF)")
ckd_dx = st.sidebar.checkbox("Diagnostic CKD (Rinichi)")
if acr != "A1 Normal (<30)": ckd_dx = True # Logic override

st.sidebar.subheader("Schema Actuală")
# Folosim o listă simplă pentru procesare
current_meds = []
if st.sidebar.checkbox("Metformin"): current_meds.append("Metformin")
if st.sidebar.checkbox("SGLT2i (Dapa/Empa/Cana)"): current_meds.append("SGLT2i")
if st.sidebar.checkbox("GLP-1 RA (Sema/Dula/Lira)"): current_meds.append("GLP1_RA")
if st.sidebar.checkbox("DPP-4i (Sita/Lina/Vilda)"): current_meds.append("DPP4i")
if st.sidebar.checkbox("Sulfoniluree (SU)"): current_meds.append("SU")
if st.sidebar.checkbox("TZD (Pioglitazona)"): current_meds.append("TZD")
if st.sidebar.checkbox("Insulină Bazală"): current_meds.append("Insulin_Basal")
if st.sidebar.checkbox("Insulină Prandială"): current_meds.append("Insulin_Prandial")

# ==========================================
# 3. MOTORUL DE DECIZIE (ALGORITM SECVENȚIAL)
# ==========================================
def generate_plan(meds, hba1c, target, egfr, bmi, ascvd, hf, ckd):
    plan = [] 
    # Planul este o listă de dicționare: {action_type: 'STOP'|'START'|'SWITCH', text: str, reason: str, ref: str}
    
    # Copie locală a medicamentelor pentru simulare
    simulated_meds = meds.copy()
    
    # -----------------------------------------------------
    # PASUL 1: SANITIZARE & SIGURANȚĂ (Hard Stops)
    # -----------------------------------------------------
    
    # 1.1 Verificare eGFR Metformin
    if "Metformin" in simulated_meds:
        if egfr < 30:
            plan.append({
                "type": "STOP",
                "text": "OPRIȚI Metformin",
                "reason": "Contraindicație absolută: eGFR < 30 mL/min (Risc Acidoză Lactică).",
                "ref": "ADA Standards 2024 Sec. 9"
            })
            simulated_meds.remove("Metformin")
        elif egfr < 45:
            plan.append({
                "type": "ALERT", # Nu stop, dar avertisment
                "text": "Reduceți doza Metformin (Max 1000mg)",
                "reason": "eGFR 30-45 necesită ajustare doză.",
                "ref": "FDA Labeling"
            })

    # 1.2 Verificare eGFR SGLT2i
    if "SGLT2i" in simulated_meds and egfr < 20:
        plan.append({
            "type": "STOP",
            "text": "OPRIȚI SGLT2i",
            "reason": "eGFR < 20: eficacitate glicemică nulă și date de siguranță limitate pentru inițiere.",
            "ref": "EMPA-KIDNEY / DAPA-CKD exclusion criteria"
        })
        simulated_meds.remove("SGLT2i")

    # 1.3 Verificare TZD în HF
    if "TZD" in simulated_meds and hf:
        plan.append({
            "type": "STOP",
            "text": "OPRIȚI Pioglitazona (TZD)",
            "reason": "Contraindicație majoră: Retenție hidrosalină agravează Insuficiența Cardiacă.",
            "ref": "AHA/ADA Guidelines"
        })
        simulated_meds.remove("TZD")
        
    # 1.4 Conflict DPP-4i + GLP-1 RA (Cazul menționat de tine!)
    # Verificăm dacă pacientul a venit DEJA cu ambele (eroare de prescripție anterioară)
    if "DPP4i" in simulated_meds and "GLP1_RA" in simulated_meds:
        plan.append({
            "type": "STOP",
            "text": "OPRIȚI DPP-4i imediat",
            "reason": "Duplicitate terapeutică cu GLP-1 RA. Nu există beneficiu adăugat, doar costuri.",
            "ref": "ADA Standards - Pharmacology"
        })
        simulated_meds.remove("DPP4i")

    # -----------------------------------------------------
    # PASUL 2: PROTECȚIE DE ORGAN (Indicație obligatorie)
    # -----------------------------------------------------
    # Aici adăugăm medicamentele care TREBUIE să existe, indiferent de A1c.
    
    # 2.1 Insuficiență Cardiacă (HF) -> SGLT2i este MANDATORY
    if hf and "SGLT2i" not in simulated_meds and egfr >= 20:
        plan.append({
            "type": "START",
            "text": "INIȚIAȚI SGLT2i (Dapagliflozin/Empagliflozin)",
            "reason": "Indicație Clasa A pentru HFrEF și HFpEF indiferent de diabet.",
            "ref": "DAPA-HF, DELIVER, EMPEROR-Reduced/Preserved"
        })
        simulated_meds.append("SGLT2i") # Simulăm adăugarea pentru a nu dubla la pasul 3
    
    # 2.2 CKD -> SGLT2i (Primary)
    if ckd_dx and "SGLT2i" not in simulated_meds and egfr >= 20:
        plan.append({
            "type": "START",
            "text": "INIȚIAȚI SGLT2i",
            "reason": "Încetinirea progresiei bolii renale cronice.",
            "ref": "DAPA-CKD, EMPA-KIDNEY"
        })
        simulated_meds.append("SGLT2i")

    # 2.3 ASCVD -> GLP-1 RA (Preferat) sau SGLT2i
    if ascvd:
        has_protection = ("SGLT2i" in simulated_meds) or ("GLP1_RA" in simulated_meds)
        if not has_protection:
            # Alegem între ele. Dacă BMI e mare -> GLP1.
            if bmi > 27:
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI GLP-1 RA (cu beneficiu CV dovedit)",
                    "reason": "ASCVD prezent + Obezitate. GLP-1 (Sema/Lira/Dula) reduce MACE (Mortalitate CV, AVC, IM).",
                    "ref": "SUSTAIN-6, PIONEER-6, REWIND, LEADER"
                })
                simulated_meds.append("GLP1_RA")
                
                # Aici intervine "Switch-ul" inteligent: Dacă inițiem GLP1, trebuie să verificăm dacă are DPP4
                if "DPP4i" in simulated_meds:
                    plan.append({
                        "type": "STOP",
                        "text": "OPRIȚI DPP-4i (concomitent cu inițierea GLP-1)",
                        "reason": "Mecanisme redundante. GLP-1 înlocuiește DPP-4i.",
                        "ref": "Ghid practic farmacologie"
                    })
                    simulated_meds.remove("DPP4i")
            else:
                # Dacă nu e obez, poate SGLT2 e ok
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI SGLT2i sau GLP-1 RA",
                    "reason": "ASCVD necesită acoperire. Alegeți în funcție de cost/toleranță.",
                    "ref": "ADA Standards Sec 9"
                })
                simulated_meds.append("SGLT2i")

    # -----------------------------------------------------
    # PASUL 3: INTENSIFICARE GLICEMICĂ (Glycemic Gap)
    # -----------------------------------------------------
    gap = hba1c - target
    
    if gap > 0:
        # Avem nevoie de scădere suplimentară
        
        # 3.1 Nu are Metformin?
        if "Metformin" not in simulated_meds and egfr >= 30:
            plan.append({
                "type": "START",
                "text": "ADĂUGAȚI Metformin",
                "reason": "Baza tratamentului (eficacitate mare, cost mic, fără hipo).",
                "ref": "UKPDS"
            })
            simulated_meds.append("Metformin")
            
        # 3.2 Are Metformin, dar nu e la țintă. Are DPP-4i și vrem putere mai mare?
        # AICI REZOLVĂM CONTRADICȚIA: "Upgrade" de la DPP4 la GLP1
        elif "DPP4i" in simulated_meds and "GLP1_RA" not in simulated_meds:
            plan.append({
                "type": "SWITCH",
                "text": "ÎNLOCUIȚI DPP-4i cu GLP-1 RA",
                "reason": "GLP-1 RA are eficacitate mult superioară (high efficacy) față de DPP-4i (intermediate).",
                "ref": "Studii head-to-head (ex. SUSTAIN)"
            })
            simulated_meds.remove("DPP4i")
            simulated_meds.append("GLP1_RA")
            
        # 3.3 Nu are nici SGLT2, nici GLP1 (și nu are indicație de organ, e doar glicemie)
        elif "SGLT2i" not in simulated_meds and "GLP1_RA" not in simulated_meds:
            if bmi > 25:
                 plan.append({
                    "type": "START",
                    "text": "ADĂUGAȚI GLP-1 RA (sau Dual GIP/GLP-1)",
                    "reason": "Preferat pentru eficacitate glicemică mare și control ponderal.",
                    "ref": "SURPASS / SUSTAIN"
                })
            else:
                 plan.append({
                    "type": "START",
                    "text": "ADĂUGAȚI SGLT2i",
                    "reason": "Opțiune orală sigură, fără risc hipoglicemie.",
                    "ref": ""
                })
        
        # 3.4 Are deja GLP1 + Metformin + SGLT2 și tot nu e controlat? -> Insulina
        elif "GLP1_RA" in simulated_meds and "Metformin" in simulated_meds and gap > 0.5:
             if "Insulin_Basal" not in simulated_meds:
                 plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI Insulină Bazală",
                    "reason": "Terapia injectabilă combinată este necesară. GLP-1 RA maximizat.",
                    "ref": "ADA Standards - Intensification"
                })
                 if "SU" in simulated_meds:
                     plan.append({
                        "type": "STOP",
                        "text": "CONSIDERAȚI OPRIREA Sulfonilureei",
                        "reason": "Risc crescut de hipoglicemie la adăugarea insulinei.",
                        "ref": ""
                    })

    # -----------------------------------------------------
    # PASUL 4: DE-ESCALADARE (Over-treatment)
    # -----------------------------------------------------
    if hba1c < 6.5:
        if "SU" in simulated_meds:
            plan.append({
                "type": "STOP",
                "text": "DE-ESCALADARE: Opriți/Reduceți Sulfonilureea",
                "reason": "HbA1c < 6.5% indică risc de hipoglicemie. SU are beneficiu limitat cardiovascular.",
                "ref": "Deprescribing guidelines"
            })
        if "Insulin_Basal" in simulated_meds and hba1c < 6.0:
             plan.append({
                "type": "ALERT",
                "text": "DE-ESCALADARE: Reduceți Insulina Bazală cu 20%",
                "reason": "Control foarte strict, risc major de hipoglicemie.",
                "ref": ""
            })

    return plan

# ==========================================
# 4. AFIȘARE REZULTATE
# ==========================================
plan_actions = generate_plan(current_meds, hba1c, target_a1c, egfr, bmi, ascvd, hf, ckd_dx)

st.divider()

# TABURI PENTRU CLARITATE
tab1, tab2 = st.tabs(["📋 PLAN DE ACȚIUNE", "📚 Tutorial & Logică"])

with tab1:
    col_main, col_detail = st.columns([1.5, 1])
    
    with col_main:
        st.subheader("Plan Terapeutic Secvențial")
        
        if not plan_actions and hba1c <= target_a1c:
            st.success("✅ Pacientul este echilibrat și tratat conform ghidurilor. Continuați monitorizarea.")
        elif not plan_actions and hba1c > target_a1c:
            st.warning("⚠️ Caz complex. Opțiunile standard sunt epuizate. Necesită consult diabetologic avansat (ex. pompe insulină).")

        # Randare Acțiuni
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
                css_class = "action-switch" # Fallback
            
            st.markdown(f"""
            <div class="{css_class}">
                <strong>{icon} {item['type']}: {item['text']}</strong><br>
                <span style="font-size:0.95em">{item['reason']}</span><br>
                <div class="citation">Ref: {item['ref']}</div>
            </div>
            """, unsafe_allow_html=True)

    with col_detail:
        st.subheader("Sumar Clinic")
        st.markdown(f"**Glicemie**: {hba1c}% (Țintă {target_a1c}%)")
        st.markdown(f"**eGFR**: {egfr} ml/min")
        st.markdown("**Status Organ:**")
        if hf: st.badge("Insuficiență Cardiacă")
        if ckd_dx: st.badge("Boală Renală (CKD)")
        if ascvd: st.badge("ASCVD (Vascular)")
        if not (hf or ckd_dx or ascvd): st.write("Fără risc înalt specificat.")
        
        st.markdown("---")
        st.write("Acest plan prioritizează:")
        st.write("1. Eliminarea medicamentelor periculoase.")
        st.write("2. Protecția de organ obligatorie.")
        st.write("3. Intensificarea glicemică inteligentă (Switch > Add).")

with tab2:
    st.markdown("""
    ### Cum Gândește Algoritmul (Tutorial)
    
    Acest sistem urmărește cercul de decizie ADA/EASD "Holistic person-centered approach":
    
    #### Pasul 1: Siguranța Înainte de Toate
    Înainte de a adăuga ceva, verificăm dacă ce ia pacientul îl omoară.
    *   *Exemplu:* Dacă eGFR < 30, Metforminul dispare din lista virtuală de medicamente *înainte* de a calcula următorul pas.
    *   *Exemplu:* Dacă pacientul are DPP-4i și algoritmul vrea să dea GLP-1, va genera o comandă de **SWITCH (Înlocuire)**, nu de ADĂUGARE, pentru a evita redundanța.
    
    #### Pasul 2: "Organ Protection" (Coloana din Stânga a Ghidului)
    Dacă pacientul are Insuficiență Cardiacă sau Boală Renală, SGLT2i este **obligatoriu** (Category 1A Evidence), indiferent dacă HbA1c este 6.5% sau 9%.
    *   Algoritmul forțează această indicație.
    
    #### Pasul 3: Intensificarea Glicemică (Coloana din Dreapta a Ghidului)
    Dacă organele sunt protejate, dar zahărul e mare:
    *   Folosim agenți cu "High Efficacy" (GLP-1, Dual Agonists, Insulină).
    *   Sistemul preferă GLP-1 în fața Insulinei bazale (mai puțină îngrășare, fără hipoglicemie).
    
    ### Studii de Referință
    *   **DAPA-HF / EMPEROR-Reduced**: SGLT2i în HF.
    *   **DAPA-CKD / EMPA-KIDNEY**: SGLT2i în CKD.
    *   **SUSTAIN-6 / REWIND**: GLP-1 RA în ASCVD.
    *   **VERIFY**: Beneficiul combinației precoce.
    """)
