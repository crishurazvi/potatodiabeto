import streamlit as st
import pandas as pd

# ==========================================
# CONFIG & STYLING
# ==========================================
st.set_page_config(
    page_title="Diabetes Treatment Decision Support",
    page_icon="🩺",
    layout="wide"
)

# Custom CSS to highlight crucial alerts
st.markdown("""
    <style>
    .warning-box { border-left: 5px solid #ffa500; background-color: #f9f9f9; padding: 10px; }
    .rec-box { border-left: 5px solid #28a745; background-color: #f0fff4; padding: 10px; }
    .contra-box { border-left: 5px solid #dc3545; background-color: #fff0f0; padding: 10px; }
    </style>
""", unsafe_allow_html=True)

DISCLAIMER = "⚠️ **CLINICAL SUPPORT TOOL ONLY**: This is not a prescription. Suggestions are based on general guidelines (ADA/EASD). Verify all drug-drug interactions and specific patient history manually."

# ==========================================
# INPUT SIDEBAR (PATIENT DATA)
# ==========================================
st.sidebar.header("1. Patient Profile")

# Biometrics
weight = st.sidebar.number_input("Weight (kg)", 40, 200, 90)
height = st.sidebar.number_input("Height (cm)", 100, 240, 175)
bmi = weight / ((height/100)**2)
st.sidebar.caption(f"Calculated BMI: {bmi:.1f} kg/m²")

# Labs
st.sidebar.header("2. Laboratory Data")
hba1c = st.sidebar.number_input("Current HbA1c (%)", 4.0, 18.0, 8.2, step=0.1)
target_a1c = st.sidebar.selectbox("Target HbA1c", [6.5, 7.0, 7.5, 8.0], index=1)
egfr = st.sidebar.number_input("eGFR (mL/min/1.73m²)", 5, 140, 55)
uacr_high = st.sidebar.checkbox("Albuminuria (uACR > 30 mg/g)")

# CV / Renal Risk Profile (Crucial for Guidelines)
st.sidebar.header("3. Comorbidities (FDRCV)")
ascvd = st.sidebar.checkbox("Established ASCVD (MI, Stroke, PAD)")
hf = st.sidebar.checkbox("Heart Failure (HF)")
ckd = st.sidebar.checkbox("CKD History")

# Current Treatment
st.sidebar.header("4. Current Meds")
med_options = [
    "Metformin", 
    "SGLT2 Inhibitor (e.g., Dapa, Empa)", 
    "GLP-1 RA (e.g., Sema, Dula, Lira)", 
    "DPP-4 Inhibitor (e.g., Sita, Lina)", 
    "Sulfonylurea (e.g., Gliclazide, Glimepiride)", 
    "TZD (Pioglitazone)", 
    "Basal Insulin", 
    "Prandial Insulin"
]
current_meds = st.sidebar.multiselect("Select active medications:", med_options)

# ==========================================
# LOGIC ENGINE
# ==========================================

def get_recommendations():
    recs = []
    alerts = []
    
    # --- 1. SAFETY & CONTRAINDICATION CHECKS ---
    if egfr < 30:
        if "Metformin" in current_meds:
            alerts.append(f"🔴 **STOP Metformin**: eGFR is {egfr} (Contraindicated < 30).")
        if "SGLT2 Inhibitor (e.g., Dapa, Empa)" in current_meds:
            alerts.append(f"🔴 **Review SGLT2i**: eGFR {egfr} is low. (Usually initiation contraindicated < 20-30, check specific agent).")
            
    if egfr < 45 and "Metformin" in current_meds:
        alerts.append(f"🟠 **Dose Reduce Metformin**: eGFR 30-45. Max dose usually 1000mg/day.")

    if hf and "TZD (Pioglitazone)" in current_meds:
        alerts.append("🔴 **STOP TZD**: Contraindicated in Heart Failure.")

    # --- 2. ORGAN PROTECTION (Independent of HbA1c) ---
    # Guidelines say: If ASCVD/HF/CKD, use SGLT2i or GLP1 REGARDLESS of A1c.
    
    organ_protection_needed = False
    
    if ascvd:
        if "GLP-1 RA (e.g., Sema, Dula, Lira)" not in current_meds:
            recs.append("✅ **Add GLP-1 RA**: Proven CV benefit in ASCVD (Guideline Class 1A).")
            organ_protection_needed = True
        if "SGLT2 Inhibitor (e.g., Dapa, Empa)" not in current_meds:
            recs.append("✅ **Add SGLT2i**: Proven CV benefit (Guideline Class 1A).")
            organ_protection_needed = True
            
    if hf:
        if "SGLT2 Inhibitor (e.g., Dapa, Empa)" not in current_meds:
            recs.append("✅ **Add SGLT2i**: Strongest evidence for Heart Failure (HFrEF & HFpEF).")
            organ_protection_needed = True
            
    if ckd or (uacr_high and egfr >= 20):
        if "SGLT2 Inhibitor (e.g., Dapa, Empa)" not in current_meds:
            recs.append("✅ **Add SGLT2i**: Indicated for CKD progression delay (check eGFR thresholds).")
            organ_protection_needed = True
        if "GLP-1 RA (e.g., Sema, Dula, Lira)" not in current_meds and "SGLT2 Inhibitor (e.g., Dapa, Empa)" in current_meds:
            recs.append("🔹 **Consider GLP-1 RA**: If SGLT2i not tolerated or further protection needed.")

    # --- 3. GLYCEMIC INTENSIFICATION (If A1c > Target) ---
    glycemic_gap = hba1c - target_a1c
    
    if glycemic_gap > 0:
        if not organ_protection_needed:
            recs.append(f"📉 **Intensification Needed**: HbA1c is {hba1c}% (Target {target_a1c}%).")
        
        # Scenario: No Meds yet
        if not current_meds:
            recs.append("🔹 **Start Metformin**: First line (unless contraindicated).")
            
        # Scenario: On Metformin, need next step (and no ASCVD/HF forced choice)
        elif "Metformin" in current_meds and len(current_meds) == 1 and not (ascvd or hf or ckd):
            if bmi > 27:
                recs.append("🔹 **Add GLP-1 RA or SGLT2i**: Preferred for weight loss benefit.")
            else:
                recs.append("🔹 **Add SGLT2i, GLP-1, or DPP-4i**: Base choice on cost/side effects.")
        
        # Scenario: Very high A1c
        if glycemic_gap > 1.5 or hba1c > 10:
            if "Basal Insulin" not in current_meds and "GLP-1 RA (e.g., Sema, Dula, Lira)" in current_meds:
                recs.append("💉 **Consider Basal Insulin**: High glycemic burden. Start 10U or 0.1-0.2 U/kg.")
            elif "Basal Insulin" not in current_meds and "GLP-1 RA (e.g., Sema, Dula, Lira)" not in current_meds:
                recs.append("💉 **Consider GLP-1 RA (High Potency)**: Before insulin if possible.")
                
        # Scenario: Already on Basal Insulin but not controlled
        if "Basal Insulin" in current_meds:
             recs.append("⚖️ **Overbasalization Check**: If Basal > 0.5 U/kg and A1c high, add Prandial Insulin or switch to GLP-1/Insulin combo.")

    # --- 4. DE-ESCALATION / CONFLICTS ---
    if "GLP-1 RA (e.g., Sema, Dula, Lira)" in current_meds and "DPP-4 Inhibitor (e.g., Sita, Lina)" in current_meds:
        alerts.append("🟠 **Duplicate Mechanism**: STOP DPP-4i if starting GLP-1 RA (no added benefit, increased cost).")
        
    if "Basal Insulin" in current_meds and "Sulfonylurea (e.g., Gliclazide, Glimepiride)" in current_meds:
        alerts.append("🟠 **Hypo Risk**: Consider stopping Sulfonylurea when starting Insulin to reduce hypoglycemia risk.")

    return alerts, recs

# ==========================================
# MAIN UI
# ==========================================

st.title("Guideline-Based Clinical Support")
st.markdown(f"> {DISCLAIMER}")

# Dashboard Top Row
c1, c2, c3, c4 = st.columns(4)
c1.metric("HbA1c Gap", f"{hba1c - target_a1c:.1f}%", delta_color="inverse" if hba1c > target_a1c else "normal")
c2.metric("eGFR", f"{egfr}", delta_color="inverse" if egfr < 60 else "normal")
c3.metric("BMI", f"{bmi:.1f}")
c4.metric("CV Risk Status", "High" if (ascvd or hf or ckd) else "Standard")

st.divider()

alerts, recs = get_recommendations()

# LAYOUT: Two columns (Alerts/Safety vs Recommendations)
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("⚠️ Safety & Contraindications")
    if alerts:
        for alert in alerts:
            st.markdown(f"<div class='contra-box'>{alert}</div><br>", unsafe_allow_html=True)
    else:
        st.success("No major medication contraindications detected based on inputs.")

    st.markdown("### Clinical Context")
    st.write(f"**Patient**: {int(weight)}kg, {int(height)}cm")
    st.write(f"**Target**: HbA1c < {target_a1c}%")
    st.write("**Comorbidities**:")
    if ascvd: st.badge("ASCVD")
    if hf: st.badge("Heart Failure")
    if ckd: st.badge("CKD")
    if not (ascvd or hf or ckd): st.write("No major Cardiorenal flags selected.")

with col_right:
    st.subheader("📋 Guideline Suggestions (ADA/EASD)")
    
    if hba1c <= target_a1c and not (ascvd or hf or ckd):
        st.info("Patient is at target. Maintain current therapy and monitor every 3-6 months.")
    
    if recs:
        st.markdown("Based on **Organ Protection** needs and **Glycemic Gap**:")
        for rec in recs:
             st.markdown(f"<div class='rec-box'>{rec}</div><br>", unsafe_allow_html=True)
    
    # Reference Table (Dynamic based on missing classes)
    st.markdown("#### Quick Ref: Missing Agents")
    dosing_data = []
    if "SGLT2 Inhibitor (e.g., Dapa, Empa)" not in current_meds:
        dosing_data.append({"Class": "SGLT2i", "Start": "Dapa 10mg / Empa 10mg", "Renal": "See eGFR limits"})
    if "GLP-1 RA (e.g., Sema, Dula, Lira)" not in current_meds:
        dosing_data.append({"Class": "GLP-1 RA", "Start": "Sema 0.25mg / Dula 0.75mg", "Renal": "Safe in CKD"})
    
    if dosing_data:
        st.table(pd.DataFrame(dosing_data))

st.divider()

# Footer / Confirmation
with st.expander("Clinician Action & Export"):
    st.write("Review the suggestions above against the patient's full history (allergies, cost, preference).")
    notes = st.text_area(" Consultation Notes")
    if st.button("Confirm Review & Generate Summary"):
        st.success("Review Recorded.")
        st.markdown("**Summary to Copy/Paste:**")
        st.code(f"""
Subject: Diabetes Review
Current A1c: {hba1c}% (Target {target_a1c}%)
eGFR: {egfr}
Comorbidities: {'ASCVD ' if ascvd else ''}{'HF ' if hf else ''}{'CKD ' if ckd else ''}
Current Meds: {', '.join(current_meds)}

Plan/Considerations:
{chr(10).join(['- ' + r.replace('✅','').replace('🔹','').replace('**','') for r in recs])}

Notes: {notes}
        """)
