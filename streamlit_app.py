import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="ShubhgeneAI",
    page_icon="🧬",
    layout="wide"
)

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align:center">
    <h1>🧬 ShubhgeneAI</h1>
    <h4>AI-Powered Gene Intelligence Platform</h4>
    <p style="color:gray">College Science Fair – Academic Demonstration</p>
</div>
<hr>
""", unsafe_allow_html=True)

# ---------------- GEMINI CONFIG ----------------
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------- OFFLINE FALLBACK DATA ----------------
OFFLINE_DATA = {
    "TP53": {
        "gene_name": "TP53",
        "gene_type": "Tumor Suppressor",
        "function": "Regulates cell cycle and apoptosis",
        "protein_length_aa": 393,
        "molecular_weight_kDa": 53,
        "pathways": "Cell cycle, DNA repair",
        "disease_association": "Multiple cancers"
    },
    "BRCA1": {
        "gene_name": "BRCA1",
        "gene_type": "Tumor Suppressor",
        "function": "DNA double strand break repair",
        "protein_length_aa": 1863,
        "molecular_weight_kDa": 220,
        "pathways": "Homologous recombination",
        "disease_association": "Breast and ovarian cancer"
    }
}

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙️ Controls")

genes = st.sidebar.multiselect(
    "Select Gene(s)",
    ["TP53", "BRCA1", "EGFR", "INS", "CFTR"],
    default=["TP53"]
)

mutation = st.sidebar.text_input(
    "Optional Mutation (e.g. p.R175H)"
)

offline_mode = st.sidebar.checkbox(
    "Offline Demo Mode (Recommended for Fair)"
)

# ---------------- AI FUNCTIONS ----------------
@st.cache_data(show_spinner=False)
def get_gene_info(gene):
    prompt = f"""
    Provide concise academic information about the human gene {gene}.
    Respond ONLY in valid JSON with keys:
    gene_name,
    gene_type,
    function,
    protein_length_aa,
    molecular_weight_kDa,
    pathways,
    disease_association
    """

    response = model.generate_content(prompt)
    return json.loads(response.text)


@st.cache_data(show_spinner=False)
def explain_mutation(gene, mutation):
    prompt = f"""
    Explain the biological and clinical impact of mutation {mutation}
    in gene {gene}. Keep it simple and academic.
    """

    response = model.generate_content(prompt)
    return response.text

# ---------------- MAIN ACTION ----------------
if st.button("🔬 Analyze Gene(s)"):

    if not genes:
        st.warning("Please select at least one gene.")
        st.stop()

    results = {}

    with st.spinner("Analyzing gene intelligence..."):
        for gene in genes:
            try:
                if offline_mode and gene in OFFLINE_DATA:
                    results[gene] = OFFLINE_DATA[gene]
                else:
                    results[gene] = get_gene_info(gene)

            except Exception:
                st.warning(f"⚠️ Gemini unavailable. Using offline data for {gene}.")
                results[gene] = OFFLINE_DATA.get(
                    gene, {"error": "No offline data available"}
                )

    # ---------------- DISPLAY ----------------
    for gene, data in results.items():
        st.markdown(f"## 🧬 {gene}")

        col1, col2 = st.columns([2, 1])

        with col1:
            df_info = pd.DataFrame({
                "Category": data.keys(),
                "Details": data.values()
            })
            st.table(df_info)

        with col2:
            st.image(
                f"https://string-db.org/api/image/network?identifiers={gene}&species=9606",
                caption="Protein Interaction Network (STRING DB)",
                use_container_width=True
            )

        if mutation:
            st.markdown("### 🧬 Mutation Impact")
            try:
                st.info(explain_mutation(gene, mutation))
            except Exception:
                st.info("Mutation explanation unavailable in offline mode.")

        st.markdown("---")

    # ---------------- COMPARISON ----------------
    if len(results) > 1:
        st.markdown("## 📊 Multi-Gene Comparison")

        compare_df = pd.DataFrame({
            gene: {
                "Protein Length (aa)": results[gene].get("protein_length_aa"),
                "Molecular Weight (kDa)": results[gene].get("molecular_weight_kDa")
            }
            for gene in results
        }).T

        st.dataframe(compare_df)

        fig, ax = plt.subplots()
        compare_df.plot(kind="bar", ax=ax)
        ax.set_ylabel("Value")
        ax.set_title("Protein Property Comparison")
        st.pyplot(fig)

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style="text-align:center; font-size:14px; color:gray;">
ShubhgeneAI © 2026<br>
AI in Life Sciences | College Science Fair Project
</p>
""", unsafe_allow_html=True)
