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
    "SGLT2i": {"type": "Oral", "contra_egfr": 20, "benefit": ["HF", "CKD", "ASCVD"]},  # init >=20
    "GLP1_RA": {"type": "Injectable", "contra_egfr": 15, "benefit": ["ASCVD", "Weight", "CKD_Secondary"]},
    "GIP_GLP1": {"type": "Injectable", "contra_egfr": 15, "benefit": ["Weight++", "Glycemia++"]},  # Tirzepatide
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
bmi = weight / ((height / 100) ** 2)
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
if acr != "A1 Normal (<30 mg/g)":
    ckd_dx = True

st.sidebar.subheader("Severitate / Red flags")
newly_dx = st.sidebar.checkbox("Diagnostic recent (<1 an)")
catabolic = st.sidebar.checkbox("Simptome catabolice (slăbire, poliurie/polidipsie)")
ketosis = st.sidebar.checkbox("Ketonurie / ketoză (sau suspiciune)")
acute_illness = st.sidebar.checkbox("Boală acută / spitalizare (infecție, chirurgie etc.)")
suspected_t1d = st.sidebar.checkbox("Suspiciune T1D/LADA (debut rapid, IMC mic, autoimun etc.)")

st.sidebar.subheader("Schema Actuală")
current_meds = []
if st.sidebar.checkbox("Metformin"):
    current_meds.append("Metformin")
if st.sidebar.checkbox("SGLT2i (Dapa/Empa/Cana)"):
    current_meds.append("SGLT2i")
if st.sidebar.checkbox("GLP-1 RA (Sema/Dula/Lira)"):
    current_meds.append("GLP1_RA")
if st.sidebar.checkbox("GIP/GLP-1 RA (Tirzepatide)"):
    current_meds.append("GIP_GLP1")
if st.sidebar.checkbox("DPP-4i (Sita/Lina/Vilda)"):
    current_meds.append("DPP4i")
if st.sidebar.checkbox("Sulfoniluree (SU)"):
    current_meds.append("SU")
if st.sidebar.checkbox("TZD (Pioglitazona)"):
    current_meds.append("TZD")
if st.sidebar.checkbox("Insulină Bazală"):
    current_meds.append("Insulin_Basal")
if st.sidebar.checkbox("Insulină Prandială"):
    current_meds.append("Insulin_Prandial")

# ==========================================
# 3. MOTORUL DE DECIZIE (CORECTAT)
# ==========================================
def generate_plan(meds, hba1c, target, egfr, bmi, ascvd, hf, ckd, age, newly_dx, catabolic, ketosis, acute_illness, suspected_t1d):
    plan = []
    simulated_meds = meds.copy()

    def stop_su_if_present(reason, ref):
        if "SU" in simulated_meds:
            plan.append({
                "type": "STOP",
                "text": "OPRIȚI Sulfonilureea (SU)",
                "reason": reason,
                "ref": ref
            })
            simulated_meds.remove("SU")

    def stop_dpp4_if_incretin_present():
        has_incretin = ("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds)
        if "DPP4i" in simulated_meds and has_incretin:
            plan.append({
                "type": "STOP",
                "text": "OPRIȚI DPP-4i",
                "reason": "Nu combinați DPP-4i cu GLP-1 RA sau GIP/GLP-1 RA (mecanisme similare, beneficiu mic).",
                "ref": "Consensus Report: Principles of Care"
            })
            simulated_meds.remove("DPP4i")

    # -----------------------------------------------------
    # PASUL 1: SIGURANȚĂ & SANITIZARE
    # -----------------------------------------------------
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

    # SGLT2i: NU inițiați sub 20, dar NU opriți automat dacă deja e inițiat și tolerat
    if "SGLT2i" in simulated_meds and egfr < 20:
        plan.append({
            "type": "ALERT",
            "text": "NU inițiați SGLT2i la eGFR < 20; dacă este deja în curs, continuați dacă este tolerat",
            "reason": "La eGFR < 20 inițierea nu e recomandată. Dacă deja este inițiat, poate fi continuat pentru beneficiu cardiorenal, dacă este tolerat.",
            "ref": "ADA-KDIGO 2022 / Consensus"
        })
        # nu îl scoatem din listă

    if "TZD" in simulated_meds and hf:
        plan.append({
            "type": "STOP",
            "text": "OPRIȚI TZD (Pioglitazona)",
            "reason": "Risc de retenție lichidiană și agravare HF.",
            "ref": "Consensus Report: Thiazolidinediones"
        })
        simulated_meds.remove("TZD")

    # Redundanță incretinică
    stop_dpp4_if_incretin_present()

    # Situații de siguranță unde SGLT2i se evită temporar (ketoză/boală acută)
    if "SGLT2i" in simulated_meds and (ketosis or acute_illness):
        plan.append({
            "type": "ALERT",
            "text": "Luați în calcul PAUZĂ temporară SGLT2i",
            "reason": "În boală acută sau suspiciune de ketoză, riscul de DKA e mai mare; reevaluați la stabilizare.",
            "ref": "Consensus Report: Safety considerations"
        })

    # -----------------------------------------------------
    # PASUL 2: RED FLAGS -> INSULINĂ (nu doar HbA1c)
    # -----------------------------------------------------
    red_flags = suspected_t1d or ketosis or catabolic or acute_illness
    if red_flags:
        if "Insulin_Basal" not in simulated_meds:
            plan.append({
                "type": "START",
                "text": "INIȚIAȚI Insulină Bazală (prioritar)",
                "reason": "Red flags (catabolism/ketoză/boală acută/suspiciune T1D) -> control rapid și sigur; nu așteptați escaladări lente.",
                "ref": "Consensus Report: Place of Insulin"
            })
            simulated_meds.append("Insulin_Basal")

        stop_su_if_present(
            reason="La inițierea insulinei, SU crește mult riscul de hipoglicemie.",
            ref="Consensus Report: Hypoglycemia risk / Place of Insulin"
        )

        if hba1c >= 10 and "Insulin_Prandial" not in simulated_meds:
            plan.append({
                "type": "START",
                "text": "Considerați intensificare rapidă (± insulină prandială)",
                "reason": "Hiperglicemie severă + red flags: poate necesita regim mai intensiv inițial.",
                "ref": "Consensus Report: Severe hyperglycemia"
            })

    # -----------------------------------------------------
    # PASUL 3: PROTECȚIE DE ORGAN (independent de A1c/metformin)
    # -----------------------------------------------------
    if hf and "SGLT2i" not in simulated_meds and egfr >= 20 and (not ketosis) and (not acute_illness):
        plan.append({
            "type": "START",
            "text": "INIȚIAȚI SGLT2i (Dapa/Empa)",
            "reason": "Beneficiu dovedit în reducerea HHF și mortalității CV în HF.",
            "ref": "Consensus Rec: People with HF"
        })
        simulated_meds.append("SGLT2i")

    if ckd and "SGLT2i" not in simulated_meds and egfr >= 20 and (not ketosis) and (not acute_illness):
        plan.append({
            "type": "START",
            "text": "INIȚIAȚI SGLT2i",
            "reason": "Preferat pentru încetinirea progresiei CKD și reducerea HHF.",
            "ref": "Consensus Rec: People with CKD"
        })
        simulated_meds.append("SGLT2i")

    if ckd and "SGLT2i" not in simulated_meds and egfr < 20:
        if "GLP1_RA" not in simulated_meds and "GIP_GLP1" not in simulated_meds:
            plan.append({
                "type": "START",
                "text": "INIȚIAȚI GLP-1 RA",
                "reason": "Alternativă când SGLT2i nu poate fi inițiat (eGFR < 20).",
                "ref": "Consensus Rec: CKD alternative"
            })
            simulated_meds.append("GLP1_RA")
            stop_dpp4_if_incretin_present()

    # ASCVD: strict 2022 -> consideră “proven CV benefit” doar SGLT2i sau GLP-1 RA (nu GIP/GLP1 automat)
    if ascvd:
        has_protection_strict = ("SGLT2i" in simulated_meds) or ("GLP1_RA" in simulated_meds)

        # Dacă e pe GIP/GLP1 dar nu pe SGLT2i sau GLP1_RA, preferă SGLT2i (dacă eligibil) în loc să adaugi GLP1 peste el
        if (not has_protection_strict) and ("GIP_GLP1" in simulated_meds):
            if ("SGLT2i" not in simulated_meds) and egfr >= 20 and (not ketosis) and (not acute_illness):
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI SGLT2i (pentru protecție CV la ASCVD)",
                    "reason": "În algoritmul strict 2022, beneficiul CV dovedit este pentru SGLT2i/GLP-1 RA. Evitați dublarea incretinică.",
                    "ref": "Consensus Rec: People with established CVD"
                })
                simulated_meds.append("SGLT2i")
            elif "GLP1_RA" not in simulated_meds:
                plan.append({
                    "type": "ALERT",
                    "text": "Luați în calcul trecerea la un GLP-1 RA cu beneficiu CV dovedit",
                    "reason": "Dacă SGLT2i nu poate fi inițiat, pentru ASCVD algoritmul 2022 favorizează GLP-1 RA cu beneficii CV dovedite.",
                    "ref": "Consensus Rec: People with established CVD"
                })

        if not has_protection_strict and ("GIP_GLP1" not in simulated_meds):
            plan.append({
                "type": "START",
                "text": "INIȚIAȚI GLP-1 RA sau SGLT2i",
                "reason": "ASCVD -> agent cu beneficiu CV dovedit, independent de HbA1c.",
                "ref": "Consensus Rec: People with established CVD"
            })
            if (egfr >= 20) and (bmi <= 27) and (not ketosis) and (not acute_illness):
                simulated_meds.append("SGLT2i")
            else:
                simulated_meds.append("GLP1_RA")
                stop_dpp4_if_incretin_present()

    # -----------------------------------------------------
    # PASUL 4: INTENSIFICARE GLICEMICĂ & PONDERALĂ
    # -----------------------------------------------------
    gap = hba1c - target

    if gap > 0:
        # Early combo: legat de gap mare și diagnostic recent
        if newly_dx and gap >= 1.5:
            plan.append({
                "type": "START",
                "text": "Considerați Terapie Combinată Precoce",
                "reason": "La diagnostic recent și HbA1c mult peste țintă (≥1.5%), combinația inițială poate fi superioară.",
                "ref": "Consensus Report: Early combination / VERIFY"
            })

        # Metformin ca bază dacă eligibil
        if "Metformin" not in simulated_meds and egfr >= 30:
            plan.append({
                "type": "START",
                "text": "ADĂUGAȚI Metformin",
                "reason": "Eficacitate bună, cost redus, experiență vastă.",
                "ref": "Consensus Report: Other medications"
            })
            simulated_meds.append("Metformin")

        # Greutate ca țintă primară
        has_weight_drug = ("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds) or ("SGLT2i" in simulated_meds)
        if bmi >= 30 and not has_weight_drug:
            plan.append({
                "type": "START",
                "text": "ADĂUGAȚI GLP-1 RA sau GIP/GLP-1 RA",
                "reason": "Obezitatea este țintă primară; agenții incretinici au eficacitate mare pe greutate și HbA1c.",
                "ref": "Consensus Report: Weight management"
            })
            simulated_meds.append("GIP_GLP1")
            stop_dpp4_if_incretin_present()

        # Switch DPP-4i -> GLP-1 dacă încă există și e de intensificat
        if "DPP4i" in simulated_meds and gap > 0.5:
            plan.append({
                "type": "SWITCH",
                "text": "ÎNLOCUIȚI DPP-4i cu GLP-1 RA",
                "reason": "DPP-4i are eficacitate modestă; GLP-1 RA are eficacitate mai mare și beneficii suplimentare.",
                "ref": "Consensus Report: Comparative efficacy"
            })
            simulated_meds.remove("DPP4i")
            if "GLP1_RA" not in simulated_meds and "GIP_GLP1" not in simulated_meds:
                simulated_meds.append("GLP1_RA")

        # GLP-1 înainte de insulină (dacă nu există red flags și HbA1c nu e extremă)
        has_incretin = ("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds)
        if (not red_flags) and ("Insulin_Basal" not in simulated_meds) and (not has_incretin):
            if hba1c < 10:
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI GLP-1 RA (înainte de Insulină)",
                    "reason": "Înaintea insulinei bazale: eficacitate bună, fără hipoglicemie, scădere ponderală.",
                    "ref": "Consensus Report: Place of Insulin"
                })
                simulated_meds.append("GLP1_RA")
                stop_dpp4_if_incretin_present()
            else:
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI Insulină Bazală (+ considerați GLP-1 RA)",
                    "reason": "Hiperglicemie severă (HbA1c ≥10%) poate necesita insulină.",
                    "ref": "Consensus Report: Severe hyperglycemia / Place of Insulin"
                })
                simulated_meds.append("Insulin_Basal")
                stop_su_if_present(
                    reason="La inițierea insulinei, SU crește mult riscul de hipoglicemie.",
                    ref="Consensus Report: Hypoglycemia risk / Place of Insulin"
                )

        # Dacă deja are incretin și e încă peste țintă -> adaugă insulină bazală
        if (("GLP1_RA" in simulated_meds) or ("GIP_GLP1" in simulated_meds)) and (gap > 0):
            if "Insulin_Basal" not in simulated_meds:
                plan.append({
                    "type": "START",
                    "text": "INIȚIAȚI Insulină Bazală",
                    "reason": "Persistă peste țintă pe terapie non-insulinică optimizată.",
                    "ref": "Consensus Report: Fig 5"
                })
                simulated_meds.append("Insulin_Basal")
                stop_su_if_present(
                    reason="La inițierea insulinei, SU crește mult riscul de hipoglicemie.",
                    ref="Consensus Report: Hypoglycemia risk / Place of Insulin"
                )

        # Dacă deja are bazală și încă e peste țintă -> prandial
        if ("Insulin_Basal" in simulated_meds) and (gap > 0) and ("Insulin_Prandial" not in simulated_meds):
            plan.append({
                "type": "START",
                "text": "ADĂUGAȚI Insulină Prandială",
                "reason": "Eșec pe insulină bazală (nevoie de intensificare).",
                "ref": "Consensus Report: Insulin intensification"
            })
            simulated_meds.append("Insulin_Prandial")
            stop_su_if_present(
                reason="SU + insulină prandială crește mult riscul de hipoglicemie.",
                ref="Consensus Report: Hypoglycemia risk"
            )

    return plan

# ==========================================
# 4. AFIȘARE REZULTATE
# ==========================================
plan_actions = generate_plan(
    current_meds, hba1c, target_a1c, egfr, bmi, ascvd, hf, ckd_dx, age,
    newly_dx, catabolic, ketosis, acute_illness, suspected_t1d
)

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
        if item["type"] == "STOP":
            icon = "⛔"
            css_class = "action-stop"
        elif item["type"] == "START":
            icon = "✅"
            css_class = "action-start"
        elif item["type"] == "SWITCH":
            icon = "🔄"
            css_class = "action-switch"
        else:
            icon = "⚠️"
            css_class = "action-alert"

        st.markdown(f"""
        <div class="{css_class}">
            <strong>{icon} {item["type"]}: {item["text"]}</strong><br>
            <span style="font-size:0.95em">{item["reason"]}</span><br>
            <div class="citation">Sursă: {item["ref"]}</div>
        </div>
        """, unsafe_allow_html=True)

with col_detail:
    st.subheader("Sumar Clinic & Fenotip")
    st.metric("Glicemie (HbA1c)", f"{hba1c}%", delta=f"{hba1c-target_a1c:.1f}% vs Țintă", delta_color="inverse")

    st.markdown("**Status Organ:**")
    if hf:
        st.warning("Insuficiență Cardiacă (Prioritate SGLT2i)")
    elif ckd_dx:
        st.warning("Boală Renală (Prioritate SGLT2i)")
    elif ascvd:
        st.warning("ASCVD (Prioritate GLP-1/SGLT2i)")
    else:
        st.success("Fără boală cardiorenală stabilită")

    if age < 40:
        st.info("ℹ️ Pacient Tânăr (<40 ani): Risc crescut de complicații pe termen lung. Agresivitate terapeutică necesară.")

    if bmi > 30:
        st.info("ℹ️ Obezitate: Managementul greutății este țintă primară (Tirzepatide/Semaglutide).")

    if suspected_t1d or ketosis or catabolic or acute_illness:
        st.warning("⚠️ Red flags prezente: poate fi necesară insulină precoce și evaluare rapidă.")

st.divider()
st.markdown("### 📚 Logică Extrasă din ADA/EASD Consensus 2022")
with st.expander("Vezi detaliile algoritmului"):
    st.markdown("""
    1.  **Safety First:** Metformin stop la eGFR < 30; reduceți doza la eGFR < 45. La SGLT2i nu inițiați sub eGFR 20, dar nu opriți automat dacă e deja inițiat și tolerat.
    2.  **Organ Protection:** Adăugarea agenților dovediți (SGLT2i, GLP-1 RA) independent de HbA1c sau utilizarea Metforminului, dacă există HF, CKD sau ASCVD.
    3.  **Tirzepatide (Nou):** Textul evidențiază Tirzepatide (GIP/GLP-1) ca având eficacitate superioară pe glicemie și greutate față de GLP-1 RA clasic.
    4.  **Insulin Positioning:** Algoritmul forțează evaluarea GLP-1 RA înainte de a trece la insulină, cu excepția situațiilor cu red flags (ketoză, catabolism, boală acută, suspiciune T1D).
    5.  **De-Prescribing:** Identificarea redundanțelor (DPP-4i + GLP-1/GIP-GLP-1) și oprirea lor. Când se inițiază insulina, se recomandă oprirea SU pentru a reduce hipoglicemia.
    """)
