import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import uuid

# ==========================================
# CONFIGURATION & CONSTANTS
# ==========================================
st.set_page_config(
    page_title="Clinician Diabetes Support System",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

SAFETY_LABEL = "⚠️ Clinical suggestion for review. NOT a prescription."
GUIDELINE_VERSION = "Based on Mock ADA/EASD Consensus Logic (v2025.1)"

# Generic Dosing Reference (Static Data)
DOSING_REF = pd.DataFrame([
    {"Class": "Metformin", "Start": "500mg daily with meal", "Max": "2000-2550mg daily", "Note": "Titrate to mitigate GI SE"},
    {"Class": "SGLT2i", "Start": "10mg (Empa/Dapa) or 100mg (Cana)", "Max": "Standard dose usually max", "Note": "Monitor genital hygiene, DKA risk"},
    {"Class": "GLP-1 RA", "Start": "0.25mg (Semaglutide) / 0.75mg (Dulaglutide)", "Max": "2.0mg / 4.5mg", "Note": "Titrate q4 weeks"},
    {"Class": "DPP-4i", "Start": "100mg (Sitagliptin)", "Max": "100mg", "Note": "Adjust for renal function"},
    {"Class": "Basal Insulin", "Start": "10 units or 0.1-0.2 U/kg", "Max": "Titrate to FBG target", "Note": "Monitor Hypoglycemia"},
])

# ==========================================
# DATA MODELS & MOCK DB
# ==========================================
def init_db():
    if 'patients' not in st.session_state:
        # Mock Data Generation
        st.session_state.patients = [
            {
                "id": str(uuid.uuid4()),
                "initials": "JD",
                "dob": datetime.date(1965, 5, 20),
                "sex": "Male",
                "weight_kg": 95,
                "height_cm": 175,
                "type": "T2DM",
                "duration_years": 8,
                "hba1c": 8.2,
                "egfr": 45, # CKD Stage 3b
                "acr_cat": "A2",
                "ascvd": True,
                "hf": False,
                "ckd": True,
                "liver_disease": False,
                "meds": ["Metformin 1000mg BID", "Lisinopril 10mg"],
                "allergies": ["Sulfa"],
                "glucose_history": [
                    {"date": "2024-01-01", "val": 140, "type": "Fasting"},
                    {"date": "2024-02-01", "val": 155, "type": "Fasting"},
                    {"date": "2024-03-01", "val": 148, "type": "Fasting"},
                ],
                "hba1c_history": [
                    {"date": "2023-01", "val": 7.5},
                    {"date": "2023-06", "val": 7.8},
                    {"date": "2024-01", "val": 8.2},
                ]
            },
            {
                "id": str(uuid.uuid4()),
                "initials": "AS",
                "dob": datetime.date(1980, 8, 15),
                "sex": "Female",
                "weight_kg": 60,
                "height_cm": 165,
                "type": "T1DM",
                "duration_years": 20,
                "hba1c": 7.1,
                "egfr": 90,
                "acr_cat": "A1",
                "ascvd": False,
                "hf": False,
                "ckd": False,
                "liver_disease": False,
                "meds": ["Insulin Glargine", "Insulin Aspart"],
                "allergies": [],
                "glucose_history": [],
                "hba1c_history": [{"date": "2024-01", "val": 7.1}]
            }
        ]

def calculate_bmi(weight, height):
    if height > 0:
        return round(weight / ((height/100)**2), 1)
    return 0

# ==========================================
# CLINICAL DECISION SUPPORT ENGINE
# ==========================================
def evaluate_guidelines(patient):
    """
    Pure logic function. Returns analysis dictionaries.
    DOES NOT prescribe. Returns flags: Preferred, Neutral, Caution, Contraindicated.
    """
    analysis = []
    
    # Extract vars
    egfr = patient['egfr']
    ascvd = patient['ascvd']
    hf = patient['hf']
    ckd = patient['ckd']
    p_type = patient['type']
    bmi = calculate_bmi(patient['weight_kg'], patient['height_cm'])

    # 1. Metformin Logic
    met_status = "Consider"
    met_reason = "First-line for T2DM unless contraindicated."
    if p_type == "T1DM":
        met_status = "Not Indicated"
        met_reason = "T1DM primary treatment is Insulin."
    elif egfr < 30:
        met_status = "Contraindicated"
        met_reason = "eGFR < 30 mL/min/1.73m²."
    elif egfr < 45:
        met_status = "Caution"
        met_reason = "Max dose 1000mg if eGFR 30-45."
    
    analysis.append({"Class": "Metformin", "Status": met_status, "Reason": met_reason})

    # 2. SGLT2i Logic
    sglt2_status = "Neutral"
    sglt2_reason = "Option for glucose lowering."
    if p_type == "T1DM":
        sglt2_status = "Off-label/Caution"
        sglt2_reason = "High DKA risk in T1DM."
    else:
        if hf or ckd:
            sglt2_status = "Preferred"
            sglt2_reason = "Compelling indication for HF/CKD benefit."
        if egfr < 20: # General cutoff for initiation varies, safe threshold used
            sglt2_status = "Contraindicated (Initiation)"
            sglt2_reason = "eGFR too low for initiation (check specific agent)."
    
    analysis.append({"Class": "SGLT2 Inhibitors", "Status": sglt2_status, "Reason": sglt2_reason})

    # 3. GLP-1 RA Logic
    glp1_status = "Neutral"
    glp1_reason = "Potent glucose lowering."
    if p_type == "T1DM":
        glp1_status = "Off-label"
        glp1_reason = "Not FDA approved for T1DM."
    else:
        if ascvd:
            glp1_status = "Preferred"
            glp1_reason = "Proven CV benefit in ASCVD."
        elif bmi > 30:
            glp1_status = "Preferred"
            glp1_reason = "Benefit for weight management."
    
    analysis.append({"Class": "GLP-1 RA", "Status": glp1_status, "Reason": glp1_reason})

    # 4. Sulfonylureas
    su_status = "Neutral"
    su_reason = "Effective, low cost."
    if p_type == "T1DM":
        su_status = "Not Indicated"
        su_reason = "T1DM requires insulin."
    else:
        if egfr < 60 and "Glipizide" not in str(patient['meds']): 
             su_status = "Caution"
             su_reason = "Hypoglycemia risk increases with reduced renal function (prefer Glipizide)."
        if hf or ckd or ascvd:
            su_status = "Less Preferred"
            su_reason = "Lack of CV/Renal outcome benefits compared to SGLT2i/GLP1."

    analysis.append({"Class": "Sulfonylureas", "Status": su_status, "Reason": su_reason})

    return pd.DataFrame(analysis)

# ==========================================
# UI COMPONENTS
# ==========================================

def render_patient_profile(patient):
    # Header
    col1, col2, col3, col4 = st.columns(4)
    bmi = calculate_bmi(patient['weight_kg'], patient['height_cm'])
    
    with col1:
        st.metric("Age", (datetime.date.today() - patient['dob']).days // 365)
        st.metric("Type", patient['type'])
    with col2:
        st.metric("BMI", bmi)
        st.metric("HbA1c", f"{patient['hba1c']}%")
    with col3:
        st.metric("eGFR", f"{patient['egfr']}")
        if patient['egfr'] < 60:
            st.error("CKD Suggested")
    with col4:
        # Badges
        if patient['ascvd']: st.warning("ASCVD")
        if patient['hf']: st.warning("Heart Failure")
        if patient['ckd']: st.warning("CKD")
        if patient['liver_disease']: st.info("Liver Disease")

    st.markdown("---")
    
    # Charts
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("HbA1c Trend")
        if patient['hba1c_history']:
            df_a1c = pd.DataFrame(patient['hba1c_history'])
            fig_a1c = px.line(df_a1c, x='date', y='val', markers=True, title="HbA1c (%)")
            st.plotly_chart(fig_a1c, use_container_width=True)
        else:
            st.info("No historical A1c data.")
            
    with c2:
        st.subheader("Glucose Entries")
        if patient['glucose_history']:
            df_gluc = pd.DataFrame(patient['glucose_history'])
            fig_gluc = px.scatter(df_gluc, x='date', y='val', color='type', title="Glucose (mg/dL)")
            fig_gluc.add_hline(y=70, line_dash="dot", line_color="red", annotation_text="Hypo Threshold")
            st.plotly_chart(fig_gluc, use_container_width=True)
        else:
            st.info("No glucose logs available.")

    # Current Meds
    st.subheader("Current Medication Regime")
    if patient['meds']:
        for med in patient['meds']:
            st.text(f"• {med}")
    else:
        st.text("No active medications recorded.")

def render_cds_module(patient):
    st.markdown("## 🧠 Guideline-Informed Decision Support")
    st.info(f"Ruleset: {GUIDELINE_VERSION}")
    
    # Disclaimer Box
    st.warning(f"**IMPORTANT**: {SAFETY_LABEL}\n\nThis tool checks specific contraindications (e.g., eGFR limits) and guideline preferences (e.g., ASCVD). It does not account for temporary acute conditions, drug-drug interactions outside diabetes meds, or formulary coverage.")

    # Run Logic
    df_analysis = evaluate_guidelines(patient)
    
    # Styling the DataFrame
    def color_status(val):
        color = 'black'
        if val == 'Preferred': color = 'green'
        elif val == 'Contraindicated': color = 'red'
        elif val == 'Caution': color = 'orange'
        return f'color: {color}; font-weight: bold'

    st.subheader("Therapeutic Class Eligibility Review")
    st.caption("Review these flags against patient history.")
    
    st.dataframe(
        df_analysis.style.map(color_status, subset=['Status']),
        use_container_width=True,
        hide_index=True
    )

    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        st.subheader("Reference: Standard Starting Doses")
        st.caption("Not patient specific.")
        st.table(DOSING_REF)

    with col_b:
        st.subheader("Clinical Actions")
        st.markdown(f"**Active Patient**: {patient['initials']} (ID: {patient['id'][:8]})")
        
        notes = st.text_area("Clinical Notes / Rationale for Change", height=150)
        
        confirm_check = st.checkbox("I have reviewed the contraindications and verified eGFR/Allergies manually.")
        
        if st.button("Export Plan to PDF (Mock)", disabled=not confirm_check):
            st.success("Plan generated (Mock download).")
            st.balloons()
            st.markdown(f"> **Plan Summary for {patient['initials']}**\n> Notes: {notes}\n> *{SAFETY_LABEL}*")

# ==========================================
# MAIN APP LAYOUT
# ==========================================
def main():
    init_db()
    
    st.sidebar.title("CDSS Diabetes")
    
    menu = st.sidebar.radio("Navigation", ["Registry", "Add Patient"])
    
    if menu == "Registry":
        st.title("Patient Registry")
        
        # Patient Selector
        patient_names = {p['initials'] + f" ({p['id'][:4]})": p['id'] for p in st.session_state.patients}
        selected_label = st.selectbox("Select Patient", list(patient_names.keys()))
        selected_id = patient_names[selected_label]
        
        # Get Patient Object
        patient = next(p for p in st.session_state.patients if p['id'] == selected_id)
        
        # Tabs for Patient View
        tab1, tab2 = st.tabs(["Patient Profile", "Decision Support"])
        
        with tab1:
            render_patient_profile(patient)
            
        with tab2:
            render_cds_module(patient)

    elif menu == "Add Patient":
        st.title("Add New Patient")
        with st.form("new_patient_form"):
            c1, c2 = st.columns(2)
            initials = c1.text_input("Initials")
            dob = c2.date_input("Date of Birth", value=datetime.date(1970, 1, 1))
            sex = c1.selectbox("Sex", ["Male", "Female"])
            p_type = c2.selectbox("Diabetes Type", ["T1DM", "T2DM", "LADA", "Other"])
            
            st.markdown("---")
            w = st.number_input("Weight (kg)", 40, 200, 80)
            h = st.number_input("Height (cm)", 100, 250, 170)
            egfr = st.number_input("eGFR (mL/min)", 0, 150, 90)
            a1c = st.number_input("HbA1c (%)", 4.0, 20.0, 7.0)
            
            st.markdown("### Comorbidities")
            col_a, col_b, col_c = st.columns(3)
            ascvd = col_a.checkbox("ASCVD (MI, Stroke, PAD)")
            hf = col_b.checkbox("Heart Failure")
            ckd = col_c.checkbox("CKD (Albuminuria/History)")
            
            submit = st.form_submit_button("Create Record")
            
            if submit:
                new_p = {
                    "id": str(uuid.uuid4()),
                    "initials": initials,
                    "dob": dob,
                    "sex": sex,
                    "weight_kg": w,
                    "height_cm": h,
                    "type": p_type,
                    "duration_years": 0,
                    "hba1c": a1c,
                    "egfr": egfr,
                    "acr_cat": "Unknown",
                    "ascvd": ascvd,
                    "hf": hf,
                    "ckd": ckd,
                    "liver_disease": False,
                    "meds": [],
                    "allergies": [],
                    "glucose_history": [],
                    "hba1c_history": [{"date": str(datetime.date.today()), "val": a1c}]
                }
                st.session_state.patients.append(new_p)
                st.success("Patient Added!")
                st.rerun()

if __name__ == "__main__":
    main()
