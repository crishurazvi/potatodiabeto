import streamlit as st
import pandas as pd

# ==========================================
# CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Diabetes Clinical Decision Support",
    page_icon="🩺",
    layout="wide"
)

# Stiluri CSS pentru a evidenția recomandările
st.markdown("""
    <style>
    .safety-box { border-left: 5px solid #d9534f; background-color: #fdf7f7; padding: 15px; border-radius: 5px; }
    .mandate-box { border-left: 5px solid #f0ad4e; background-color: #fcf8e3; padding: 15px; border-radius: 5px; }
    .action-box { border-left: 5px solid #5cb85c; background-color: #f0f9eb; padding: 15px; border-radius: 5px; }
    .deescalate-box { border-left: 5px solid #5bc0de; background-color: #f0f8ff; padding: 15px; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

DISCLAIMER = "⚠️ **INSTRUMENT SUPORT CLINIC**: Recomandările sunt bazate pe ghiduri (ADA/EASD). Decizia finală și verificarea interacțiunilor medicamentoase aparțin medicului curant."

# ==========================================
# SIDEBAR - DATE PACIENT
# ==========================================
st.sidebar.header("1. Profil Pacient")

# Biometrie
c1, c2 = st.sidebar.columns(2)
weight = c1.number_input("Greutate (kg)", 40, 200, 90)
height = c2.number_input("Înălțime (cm)", 100, 240, 175)
bmi = weight / ((height/100)**2)
st.sidebar.caption(f"BMI Calculat: {bmi:.1f} kg/m²")

# Laborator
st.sidebar.header("2. Date Laborator")
hba1c = st.sidebar.number_input("HbA1c Actual (%)", 4.0, 18.0, 8.5, step=0.1)
target_a1c = st.sidebar.selectbox("Țintă HbA1c", [6.5, 7.0, 7.5, 8.0], index=1)
egfr = st.sidebar.number_input("eGFR (mL/min)", 5, 140, 60)
uacr_high = st.sidebar.checkbox("Albuminurie (uACR > 30 mg/g)")

# Comorbidități (Foarte important pentru algoritm)
st.sidebar.header("3. Comorbidități (FDRCV)")
ascvd = st.sidebar.checkbox("ASCVD (Infarct, AVC, Arteriopatie)")
hf = st.sidebar.checkbox("Insuficiență Cardiacă (HF)")
ckd = st.sidebar.checkbox("Boală Cronică de Rinichi (CKD)")

# Tratament Actual
st.sidebar.header("4. Tratament Actual")
st.sidebar.caption("Selectează clasele pe care pacientul le ia DEJA:")

med_metformin = st.sidebar.checkbox("Metformin")
med_sglt2 = st.sidebar.checkbox("SGLT2i (Dapa/Empa/Cana)")
med_glp1 = st.sidebar.checkbox("GLP-1 RA (Sema/Dula/Lira)")
med_dpp4 = st.sidebar.checkbox("DPP-4i (Sita/Lina/Vilda)")
med_su = st.sidebar.checkbox("Sulfoniluree (Gliclazid/Glimepirid)")
med_insulin_basal = st.sidebar.checkbox("Insulină Bazală")
med_insulin_prandial = st.sidebar.checkbox("Insulină Prandială")

# Status doze
st.sidebar.markdown("---")
max_tolerated = st.sidebar.checkbox("Tratamentul actual e la doze maxime tolerate?")

# ==========================================
# LOGIC ENGINE (MOTORUL DE DECIZIE)
# ==========================================

def run_logic_engine():
    safety_alerts = []
    organ_mandates = []
    glycemic_actions = []
    deescalation_tips = []

    # ----------------------------------------
    # 1. SAFETY & CONTRAINDICATIONS
    # ----------------------------------------
    if egfr < 30 and med_metformin:
        safety_alerts.append("⛔ **STOP Metformin**: eGFR < 30 este contraindicație absolută.")
    elif egfr < 45 and med_metformin and not max_tolerated:
        safety_alerts.append("⚠️ **Ajustare Metformin**: eGFR 30-45. Reduceți doza la 500-1000mg/zi.")

    if egfr < 20 and med_sglt2:
        safety_alerts.append("⛔ **STOP/Reevaluare SGLT2i**: eGFR < 20 (date limitate, risc eficacitate scăzută).")

    if med_glp1 and med_dpp4:
        safety_alerts.append("⛔ **Duplicitate Mecanism**: STOP DPP-4i. Nu se asociază cu GLP-1 RA (cost inutil, fără beneficiu).")

    if med_insulin_prandial and med_su:
        safety_alerts.append("⚠️ **Risc Hipoglicemie**: Luați în considerare oprirea Sulfonilureei la inițierea insulinei prandiale.")

    # ----------------------------------------
    # 2. ORGAN PROTECTION (Independent de A1c)
    # ----------------------------------------
    # Regula: Dacă are ASCVD/HF/CKD, trebuie SGLT2i sau GLP1 INDIFERENT de glicemie.
    
    organ_gap = False # Flag dacă lipsește protecția de organ

    if hf:
        if not med_sglt2:
            organ_mandates.append("🫀 **Adaugă SGLT2i**: Obligatoriu pentru Insuficiență Cardiacă (Clasa I, Nivel A).")
            organ_gap = True
    
    if ckd or (uacr_high and egfr >= 20):
        if not med_sglt2:
            organ_mandates.append("kidney **Adaugă SGLT2i**: Preferat pentru protecție renală și reducerea progresiei CKD.")
            organ_gap = True
        elif not med_glp1 and med_sglt2:
            organ_mandates.append("ℹ️ **Consideră GLP-1 RA**: Dacă eGFR scade în continuare sau ACR mare, adăugați GLP-1 pentru protecție suplimentară.")

    if ascvd:
        if not med_glp1 and not med_sglt2:
            organ_mandates.append("🫀 **Adaugă GLP-1 RA sau SGLT2i**: Beneficiu CV dovedit. GLP-1 RA preferat dacă predomină ateroscleroza.")
            organ_gap = True
        elif med_sglt2 and not med_glp1 and hba1c > target_a1c:
            organ_mandates.append("➕ **Adaugă GLP-1 RA**: Pentru beneficiu CV cumulativ și control glicemic.")

    # ----------------------------------------
    # 3. GLYCEMIC CONTROL (Escaladare)
    # ----------------------------------------
    a1c_gap = hba1c - target_a1c
    
    # Doar dacă siguranța o permite
    if a1c_gap > 0:
        glycemic_actions.append(f"📈 **Necesită Intensificare**: HbA1c {hba1c}% vs Țintă {target_a1c}%.")
        
        # Pasul 1: Metformin (Fundație)
        if not med_metformin and egfr >= 30:
            glycemic_actions.append("🔹 **Inițiază Metformin**: Prima linie de tratament (dacă nu e contraindicat).")
        
        # Pasul 2: Dacă Metformin există (sau e contraindicat), ce urmează?
        else:
            # Dacă lipsește o clasă de organ protection, a fost deja sugerată mai sus.
            # Aici tratăm cazul în care organele sunt protejate sau nu au probleme, dar glicemia e mare.
            
            # Alegerea agentului potent
            if not med_glp1 and not med_insulin_basal:
                if bmi > 27:
                    glycemic_actions.append("🔹 **Adaugă GLP-1 RA**: Eficacitate mare + Scădere ponderală.")
                elif not med_sglt2:
                    glycemic_actions.append("🔹 **Adaugă SGLT2i sau GLP-1 RA**: Agenți cu risc mic de hipoglicemie.")
            
            # Pasul 3: Dacă are deja GLP-1 sau SGLT2 și tot e mare
            elif med_glp1 and not med_insulin_basal:
                if not med_sglt2 and egfr > 20:
                    glycemic_actions.append("🔹 **Asociere Triplă**: Adaugă SGLT2i la Metformin + GLP-1.")
                else:
                    glycemic_actions.append("💉 **Inițiere Insulină Bazală**: GLP-1 maximizat. Începeți cu 10 U/zi sau 0.1-0.2 U/kg.")

            # Pasul 4: Are Insulina Bazală
            elif med_insulin_basal:
                if med_glp1:
                    glycemic_actions.append("⚖️ **Titrare Insulină**: Verificați glicemia a jeun. Dacă e normală dar A1c mare -> adăugați Insulina Prandială.")
                else:
                    glycemic_actions.append("➕ **Adaugă GLP-1 RA**: Înainte de a trece la regim Bolus-Bazal complet (injectabil combinat).")

    # ----------------------------------------
    # 4. DE-ESCALATION (Glicemie prea mică sau regim complex inutil)
    # ----------------------------------------
    if hba1c < 6.5 and (med_su or med_insulin_basal or med_insulin_prandial):
        deescalation_tips.append("📉 **Consideră De-escaladarea**: HbA1c este strâns (<6.5%).")
        if med_su:
            deescalation_tips.append("🔻 **STOP/Reduce Sulfoniluree**: Risc de hipoglicemie. Agenții moderni (SGLT2/GLP1) sunt preferați.")
        if med_insulin_basal and hba1c < 6.0:
            deescalation_tips.append("🔻 **Titrare în jos Insulină**: Reduceți doza cu 10-20% pentru a evita hipoglicemia.")

    return safety_alerts, organ_mandates, glycemic_actions, deescalation_tips

# ==========================================
# UI & DISPLAY
# ==========================================

st.title("Ghid Ajustare Tratament Diabet (ADA/EASD)")
st.markdown(f"> {DISCLAIMER}")

# Dashboard rapid
col1, col2, col3, col4 = st.columns(4)
diff = hba1c - target_a1c
col1.metric("HbA1c Gap", f"{diff:+.1f}%", delta_color="inverse")
col2.metric("eGFR Status", f"{egfr} mL/min", delta_color="normal" if egfr > 60 else "inverse")
risk_label = "Foarte Înalt" if (ascvd or hf or ckd) else "Standard"
col3.metric("Risc Cardio-Renal", risk_label)
col4.metric("BMI", f"{bmi:.1f}")

st.divider()

# Rulare Algoritm
safety, organ, glycemic, deescalation = run_logic_engine()

# Layout pe coloane
left_col, right_col = st.columns([1, 1])

with left_col:
    st.subheader("1. Siguranță & Conflicte")
    if safety:
        for s in safety:
            st.markdown(f"<div class='safety-box'>{s}</div><br>", unsafe_allow_html=True)
    else:
        st.success("✅ Fără contraindicații majore pe datele introduse.")

    st.subheader("2. Protecție de Organ (Obligatoriu)")
    if organ:
        st.info("Pacientul are comorbidități (HF, CKD sau ASCVD) care necesită clase specifice INDIFERENT de HbA1c.")
        for o in organ:
            st.markdown(f"<div class='mandate-box'>{o}</div><br>", unsafe_allow_html=True)
    elif (ascvd or hf or ckd):
        st.success("✅ Terapia actuală acoperă protecția de organ necesară.")
    else:
        st.write("Nu există indicații specifice de organ (HF/CKD/ASCVD). Focus pe control glicemic.")

with right_col:
    st.subheader("3. Control Glicemic (HbA1c)")
    if hba1c <= target_a1c:
        st.success(f"✅ Pacientul este în țintă (HbA1c {hba1c}% <= {target_a1c}%).")
        if deescalation:
            st.subheader("4. Oportunități De-escaladare")
            for d in deescalation:
                st.markdown(f"<div class='deescalate-box'>{d}</div><br>", unsafe_allow_html=True)
    else:
        # Afișare acțiuni escaladare
        for g in glycemic:
            st.markdown(f"<div class='action-box'>{g}</div><br>", unsafe_allow_html=True)
            
    # Tabel mic de referință
    with st.expander("Referință Rapidă Inițiere"):
        ref_data = {
            "Clasa": ["Metformin", "SGLT2i", "GLP-1 RA", "Insulină Bazală"],
            "Doza Start": ["500mg la masă", "10mg (Dapa/Empa)", "0.25mg (Sema) / 0.75mg (Dula)", "10 U sau 0.1-0.2 U/kg"],
            "Titrare": ["Crește săpt. la 2000mg", "Nu necesită titrare", "Crește la 4 săpt.", "Ajustare la 3 zile după glicemia a jeun"]
        }
        st.table(pd.DataFrame(ref_data))

# Secțiunea Finală
st.divider()
st.caption("Algoritm bazat pe Consensus Report ADA/EASD 2024. Această aplicație nu stochează date.")
