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

# CSS Avansat
st.markdown("""
    <style>
    .action-stop { border-left: 6px solid #d9534f; background-color: #fff5f5; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-start { border-left: 6px solid #28a745; background-color: #f0fff4; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-switch { border-left: 6px solid #007bff; background-color: #eef7ff; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .action-alert { border-left: 6px solid #ffc107; background-color: #fffbf0; padding: 15px; margin-bottom: 10px; border-radius: 4px; }
    .citation { font-size: 0.85em; color: #666; font-style: italic; margin-top: 5px; }
    .med-card { border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .med-header { color: #2c3e50; font-size: 1.5em; font-weight: bold; margin-bottom: 10px; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
    .tag { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; margin-right: 5px; color: white;}
    .tag-high { background-color: #27ae60; }
    .tag-med { background-color: #f39c12; }
    .tag-low { background-color: #c0392b; }
    </style>
""", unsafe_allow_html=True)

DISCLAIMER = "⚠️ **CLINICAL DECISION SUPPORT**: Algoritm bazat pe Raportul de Consens ADA/EASD 2022. Nu înlocuiește judecata clinică."

# ==========================================
# 1. BAZA DE DATE (ALGORITM & COMPENDIU)
# ==========================================

# Date pentru Compendiul Farmacologic (Digitizate din imagine)
MED_DETAILS = {
    "Metformin": {
        "efficacy": "High",
        "hypo": "No",
        "weight": "Neutral (modest loss)",
        "cv_effect": "Potential Benefit",
        "hf_effect": "Neutral",
        "renal_effect": "Neutral",
        "cost": "Low",
        "route": "Oral",
        "dosing": "Contraindicat eGFR <30. Monitorizare Vit B12.",
        "clinical": [
            "Efecte secundare GI frecvente (diaree, greață).",
            "Considerați formule XR și administrare cu alimente.",
            "Deficiență potențială de Vitamina B12 la utilizare lungă."
        ]
    },
    "SGLT2 Inhibitors": {
        "efficacy": "Intermediate to High",
        "hypo": "No",
        "weight": "Loss (Intermediate)",
        "cv_effect": "Benefit (MACE)",
        "hf_effect": "Benefit (Dapa/Empa/Cana/Ertu)",
        "renal_effect": "Benefit (Progression of DKD)",
        "cost": "High",
        "route": "Oral",
        "dosing": "Eficacitate glicemică redusă la eGFR mic, dar beneficiu renal păstrat.",
        "clinical": [
            "Risc rar de DKA (euglicemică). Oprire cu 3-4 zile înainte de operații.",
            "Risc crescut de infecții micotice genitale.",
            "Risc Fournier's gangrene (rar).",
            "Atenție la volum (hipotensiune) și diuretice."
        ]
    },
    "GLP-1 RAs": {
        "efficacy": "High to Very High",
        "hypo": "No",
        "weight": "Loss (Intermediate to Very High)",
        "cv_effect": "Benefit (Dula/Lira/Sema)",
        "hf_effect": "Neutral",
        "renal_effect": "Benefit (Albuminuria outcomes)",
        "cost": "High",
        "route": "SQ / Oral (Sema)",
        "dosing": "Ajustare doză renală (Lixi/Exenatide). Fără ajustare: Lira/Sema/Dula.",
        "clinical": [
            "Risc tumori celule C tiroidiene (rozătoare). Contraindicat în MEN2.",
            "Efecte GI frecvente (greață). Titrare lentă recomandată.",
            "Risc potențial pancreatită / Boli vezică biliară.",
            "Retinopatie (asociată cu scăderea rapidă a glicemiei - ex. SUSTAIN-6)."
        ]
    },
    "GIP and GLP-1 RA": {
        "efficacy": "Very High",
        "hypo": "No",
        "weight": "Loss (Very High)",
        "cv_effect": "Under investigation",
        "hf_effect": "Under investigation",
        "renal_effect": "Under investigation",
        "cost": "High",
        "route": "SQ",
        "dosing": "Fără ajustare doză renală. Monitorizare funcție renală la GI adverse.",
        "clinical": [
            "Profil similar GLP-1 RA (Greață, Vărsături).",
            "Eficacitate superioară pe greutate și glicemie față de GLP-1 RA.",
            "Contraindicat în istoric de cancer medular tiroidian / MEN2.",
            "Atenție la colelitiază/colecistită."
        ]
    },
    "DPP-4 Inhibitors": {
        "efficacy": "Intermediate",
        "hypo": "No",
        "weight": "Neutral",
        "cv_effect": "Neutral",
        "hf_effect": "Neutral (Risc potențial: Saxagliptin)",
        "renal_effect": "Neutral",
        "cost": "High",
        "route": "Oral",
        "dosing": "Ajustare renală necesară (excepție Linagliptin).",
        "clinical": [
            "Bine tolerat, efecte secundare rare.",
            "Pancreatită (raportată rar).",
            "Dureri articulare (Joint pain).",
            "Pemphigoid bulos (rar)."
        ]
    },
    "Thiazolidinediones (TZD)": {
        "efficacy": "High",
        "hypo": "No",
        "weight": "Gain",
        "cv_effect": "Potential Benefit (Pio)",
        "hf_effect": "Increased Risk",
        "renal_effect": "Neutral",
        "cost": "Low",
        "route": "Oral",
        "dosing": "Nu se recomandă în insuficiență renală din cauza retenției fluide.",
        "clinical": [
            "Risc major: Insuficiență Cardiacă (Edeme).",
            "Beneficiu în NASH (Steatohepatită).",
            "Risc de fracturi osoase.",
            "Creștere în greutate."
        ]
    },
    "Sulfonylureas": {
        "efficacy": "High",
        "hypo": "Yes",
        "weight": "Gain",
        "cv_effect": "Neutral",
        "hf_effect": "Neutral",
        "renal_effect": "Neutral",
        "cost": "Low",
        "route": "Oral",
        "dosing": "Gliburide contraindicat în CKD. Glipizide/Glimepiride preferate.",
        "clinical": [
            "Risc HIPOGLICEMIE (atenție la vârstnici).",
            "Eficacitate durabilă limitată în timp.",
            "Atenție la FDA Warning pe mortalitate CV (bazat pe studii vechi tolbutamidă)."
        ]
    },
    "Insulin": {
        "efficacy": "High to Very High",
        "hypo": "Yes",
        "weight": "Gain",
        "cv_effect": "Neutral",
        "hf_effect": "Neutral",
        "renal_effect": "Neutral",
        "cost": "Low (Human) - High (Analog)",
        "route": "SQ / Inhaled",
        "dosing": "Doze mai mici necesare la eGFR scăzut (risc hipo crescut).",
        "clinical": [
            "Cel mai puternic agent hipoglicemiant.",
            "Reacții la locul injecției.",
            "Analogi vs Human: Risc hipoglicemie mai mic cu analogi.",
            "Necesită instruire complexă pacient."
        ]
    }
}

# ==========================================
# 2. LOGICĂ ALGORITM (Funcția anterioară)
# ==========================================
def generate_plan(meds, hba1c, target, egfr, bmi, ascvd, hf, ckd, age):
    plan = [] 
    simulated_meds = meds.copy()
    
    # 1. SAFETY
    if "Metformin" in simulated_meds:
        if egfr < 30:
            plan.append({"type": "STOP", "text": "OPRIȚI Metformin", "reason": "Contraindicație: eGFR < 30 ml/min.", "ref": "Tabel 1: Contraindicated"})
            simulated_meds.remove("Metformin")
        elif egfr < 45:
            plan.append({"type": "ALERT", "text": "Reduceți doza Metformin", "reason": "Ajustare necesară eGFR 30-45.", "ref": "Tabel 1: Considerations"})

    if "SGLT2i" in simulated_meds and egfr < 20:
        plan.append({"type": "STOP", "text": "STOP SGLT2i", "reason": "Inițiere nerecomandată eGFR < 20.", "ref": "DAPA-CKD criteria"})
        simulated_meds.remove("SGLT2i")

    if "TZD" in simulated_meds and hf:
        plan.append({"type": "STOP", "text": "OPRIȚI TZD", "reason": "Risc de agravare HF.", "ref": "Tabel 1: Increased risk HF"})
        simulated_meds.remove("TZD")
        
    if "DPP4i" in simulated_meds and (("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds)):
        plan.append({"type": "STOP", "text": "OPRIȚI DPP-4i", "reason": "Redundanță terapeutică cu GLP-1/GIP.", "ref": "Ghid ADA"})
        simulated_meds.remove("DPP4i")

    # 2. ORGAN PROTECTION
    if hf and "SGLT2i" not in simulated_meds and egfr >= 20:
        plan.append({"type": "START", "text": "INIȚIAȚI SGLT2i", "reason": "Beneficiu: HF (Empa/Dapa/Cana/Ertu).", "ref": "Tabel 1: CV Effects"})
        simulated_meds.append("SGLT2i")
    
    if ckd and "SGLT2i" not in simulated_meds and egfr >= 20:
        plan.append({"type": "START", "text": "INIȚIAȚI SGLT2i", "reason": "Beneficiu: Progresia DKD.", "ref": "Tabel 1: Renal Effects"})
        simulated_meds.append("SGLT2i")

    if ascvd:
        has_protection = any(x in simulated_meds for x in ["SGLT2i", "GLP1_RA", "GIP_GLP1"])
        if not has_protection:
            plan.append({"type": "START", "text": "INIȚIAȚI GLP-1 RA sau SGLT2i", "reason": "Beneficiu MACE dovedit.", "ref": "Tabel 1: CV Effects"})
            if bmi > 27: simulated_meds.append("GLP1_RA")
            else: simulated_meds.append("SGLT2i")

    # 3. GLYCEMIC GAP
    gap = hba1c - target
    if age < 40 and len(simulated_meds) < 2 and hba1c > target:
         plan.append({"type": "START", "text": "Terapie Combinată Precoce", "reason": "Tinerii au progresie rapidă (VERIFY).", "ref": "Text: Age < 40"})

    if gap > 0:
        if "Metformin" not in simulated_meds and egfr >= 30:
            plan.append({"type": "START", "text": "ADĂUGAȚI Metformin", "reason": "Eficacitate High, Cost Low.", "ref": "Tabel 1"})
            simulated_meds.append("Metformin")
            
        elif bmi >= 30 and not any(x in simulated_meds for x in ["GLP1_RA", "GIP_GLP1", "SGLT2i"]):
             plan.append({"type": "START", "text": "ADĂUGAȚI GIP/GLP-1 sau GLP-1", "reason": "Eficacitate 'Very High' pe greutate.", "ref": "Tabel 1: Weight Change"})
        
        elif "DPP4i" in simulated_meds and gap > 0.5:
             plan.append({"type": "SWITCH", "text": "Switch DPP-4i -> GLP-1 RA", "reason": "Upgrade de eficacitate (Intermediate -> High/Very High).", "ref": "Tabel 1: Efficacy"})
        
        elif "Insulin_Basal" not in simulated_meds and not any(x in simulated_meds for x in ["GLP1_RA", "GIP_GLP1"]):
             if hba1c < 10:
                plan.append({"type": "START", "text": "INIȚIAȚI GLP-1 RA (pre-Insulină)", "reason": "Eficacitate similară insulinei, fără hipo.", "ref": "Fig 5"})
             else:
                plan.append({"type": "START", "text": "INIȚIAȚI Insulină (+ GLP-1)", "reason": "Eficacitate 'Very High' necesară.", "ref": "Tabel 1"})

    return plan

# ==========================================
# 3. INTERFAȚĂ PRINCIPALĂ (TABURI)
# ==========================================

# Meniul principal cu Tab-uri
tab_algo, tab_compendium = st.tabs(["🧬 Algoritm Decizional", "💊 Compendiu Farmacologic (Tabel 1)"])

# ----------------------------------------------------
# TAB 1: ALGORITMUL (Codul Vechi)
# ----------------------------------------------------
with tab_algo:
    c_sidebar, c_content = st.columns([1, 3])
    
    with c_sidebar:
        st.subheader("Profil Clinic")
        age = st.number_input("Vârsta", 18, 100, 55)
        weight = st.number_input("Greutate (kg)", 40, 250, 95)
        height = st.number_input("Înălțime (cm)", 100, 240, 175)
        bmi = weight / ((height/100)**2)
        st.caption(f"BMI: {bmi:.1f}")
        
        hba1c = st.number_input("HbA1c (%)", 4.0, 18.0, 8.2, step=0.1)
        target_a1c = st.selectbox("Țintă HbA1c", [6.5, 7.0, 7.5, 8.0], index=1)
        egfr = st.number_input("eGFR", 5, 140, 45)
        
        ascvd = st.checkbox("ASCVD")
        hf = st.checkbox("Insuficiență Cardiacă")
        ckd = st.checkbox("CKD (Albuminurie/eGFR)")
        
        st.markdown("**Meds Actuale:**")
        meds_list = list(MED_DETAILS.keys())
        # Mapping UI names to Logic keys if different, but here keys match MED_DETAILS mostly
        # We need to map checkbox to logic keys used in generate_plan
        selected_meds = []
        if st.checkbox("Metformin"): selected_meds.append("Metformin")
        if st.checkbox("SGLT2i"): selected_meds.append("SGLT2i")
        if st.checkbox("GLP-1 RA"): selected_meds.append("GLP1_RA")
        if st.checkbox("GIP/GLP-1 (Tirzepatide)"): selected_meds.append("GIP_GLP1")
        if st.checkbox("DPP-4i"): selected_meds.append("DPP4i")
        if st.checkbox("Sulfoniluree"): selected_meds.append("SU")
        if st.checkbox("TZD"): selected_meds.append("TZD")
        if st.checkbox("Insulină"): selected_meds.append("Insulin_Basal")

    with c_content:
        st.markdown("### Plan Generat (ADA/EASD 2022)")
        actions = generate_plan(selected_meds, hba1c, target_a1c, egfr, bmi, ascvd, hf, ckd, age)
        
        if not actions and hba1c <= target_a1c:
            st.success("✅ Pacient controlat. Continuați monitorizarea.")
        
        for item in actions:
            icon = "⛔" if item['type'] == 'STOP' else "✅" if item['type'] == 'START' else "🔄"
            color_class = "action-stop" if item['type'] == 'STOP' else "action-start" if item['type'] == 'START' else "action-switch"
            
            st.markdown(f"""
            <div class="{color_class}">
                <strong>{icon} {item['type']}: {item['text']}</strong><br>
                {item['reason']}<br>
                <div class="citation">Ref: {item['ref']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.divider()
        st.info("💡 Navighează în tab-ul **'Compendiu Farmacologic'** pentru detalii despre doze, costuri și reacții adverse din Tabelul 1.")


# ----------------------------------------------------
# TAB 2: COMPENDIU INTERACTIV (NOU! Bazat pe Imagine)
# ----------------------------------------------------
with tab_compendium:
    st.header("💊 Fișe Tehnice: Tabel 1 ADA/EASD")
    st.markdown("Selectați o clasă pentru a vedea detaliile din tabel (Eficacitate, Risc CV/Renal, Costuri).")
    
    # Selector Medicament
    drug_choice = st.selectbox("Alege Clasa Terapeutică:", list(MED_DETAILS.keys()), index=1)
    
    # Extragere date
    info = MED_DETAILS[drug_choice]
    
    # Layout Card
    st.markdown(f"""
    <div class="med-card">
        <div class="med-header">{drug_choice}</div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("**Eficacitate:**")
        st.info(info['efficacy'])
    with col2:
        st.markdown("**Hipoglicemie:**")
        if info['hypo'] == "Yes": st.error("DA")
        else: st.success("NU")
    with col3:
        st.markdown("**Greutate:**")
        if "Loss" in info['weight']: st.success(info['weight'])
        elif "Gain" in info['weight']: st.error(info['weight'])
        else: st.warning(info['weight'])
    with col4:
        st.markdown("**Cost:**")
        st.write(info['cost'])

    st.divider()
    
    c_cv, c_renal = st.columns(2)
    with c_cv:
        st.subheader("🫀 Efecte Cardiovasculare")
        st.markdown(f"**MACE:** {info['cv_effect']}")
        st.markdown(f"**Heart Failure:** {info['hf_effect']}")
        
        if "Benefit" in info['cv_effect'] or "Benefit" in info['hf_effect']:
            st.caption("✅ Agent preferat în boală cardiovasculară.")
        if "Risk" in info['hf_effect']:
            st.caption("⛔ Atenție la pacienții cu HF.")

    with c_renal:
        st.subheader(" किडनी Efecte Renale")
        st.markdown(f"**Progresie DKD:** {info['renal_effect']}")
        st.markdown(f"**Considerații Dozaj:** {info['dosing']}")

    st.divider()
    
    st.subheader("⚠️ Considerații Clinice & Reacții Adverse")
    for point in info['clinical']:
        st.markdown(f"- {point}")
    
    st.markdown(f"**Administrare:** {info['route']}")
    
    # Comparator Simplu
    st.divider()
    with st.expander("🔄 Compară doi agenți (Head-to-Head)"):
        c_left, c_right = st.columns(2)
        drug_a = c_left.selectbox("Medicament A", list(MED_DETAILS.keys()), index=1)
        drug_b = c_right.selectbox("Medicament B", list(MED_DETAILS.keys()), index=2)
        
        d_a = MED_DETAILS[drug_a]
        d_b = MED_DETAILS[drug_b]
        
        c_left.write(f"**Eficacitate:** {d_a['efficacy']}")
        c_right.write(f"**Eficacitate:** {d_b['efficacy']}")
        
        c_left.write(f"**Greutate:** {d_a['weight']}")
        c_right.write(f"**Greutate:** {d_b['weight']}")
        
        c_left.write(f"**CV Benefit:** {d_a['cv_effect']}")
        c_right.write(f"**CV Benefit:** {d_b['cv_effect']}")
