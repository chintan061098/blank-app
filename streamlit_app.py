import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="ShubhgeneAI (Offline Mode)",
    page_icon="🧬",
    layout="wide"
)

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align:center">
    <h1>🧬 ShubhgeneAI</h1>
    <h4>AI-Inspired Gene Intelligence Platform</h4>
    <p style="color:gray">Offline Scientific Demonstration Mode</p>
</div>
<hr>
""", unsafe_allow_html=True)

# ---------------- LOCAL GENE DATABASE ----------------
GENE_DB = {
    "TP53": {
        "gene_type": "Tumor Suppressor",
        "function": "Controls cell cycle and triggers apoptosis upon DNA damage",
        "protein_length_aa": 393,
        "molecular_weight_kDa": 53,
        "pathways": "Cell cycle regulation, DNA repair",
        "disease_association": "Multiple cancers including breast and lung"
    },
    "BRCA1": {
        "gene_type": "Tumor Suppressor",
        "function": "Repairs DNA double-strand breaks",
        "protein_length_aa": 1863,
        "molecular_weight_kDa": 220,
        "pathways": "Homologous recombination",
        "disease_association": "Breast and ovarian cancer"
    },
    "EGFR": {
        "gene_type": "Proto-oncogene",
        "function": "Regulates cell growth and proliferation",
        "protein_length_aa": 1210,
        "molecular_weight_kDa": 134,
        "pathways": "MAPK, PI3K-AKT",
        "disease_association": "Lung cancer, glioblastoma"
    }
}

# ---------------- LOGIC FUNCTIONS ----------------
def get_gene_info(gene):
    return GENE_DB.get(gene, None)


def explain_mutation(gene, mutation):
    return (
        f"The mutation {mutation} in gene {gene} may alter the protein structure, "
        f"leading to reduced biological activity or abnormal signaling. "
        f"Such mutations are often associated with disease progression "
        f"and may impact therapeutic response."
    )

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙️ Controls")

genes = st.sidebar.multiselect(
    "Select Gene(s)",
    list(GENE_DB.keys()),
    default=["TP53"]
)

mutation = st.sidebar.text_input(
    "Optional Mutation (e.g. p.R175H)"
)

# ---------------- MAIN BUTTON ----------------
if st.button("🔬 Analyze Gene(s)"):

    if not genes:
        st.warning("Please select at least one gene.")
        st.stop()

    results = {}

    for gene in genes:
        info = get_gene_info(gene)
        if info:
            results[gene] = info
        else:
            st.error(f"No data available for {gene}")

    # ---------------- DISPLAY ----------------
    for gene, data in results.items():
        st.markdown(f"## 🧬 {gene}")

        df = pd.DataFrame({
            "Category": data.keys(),
            "Details": data.values()
        })

        st.table(df)

        if mutation:
            st.markdown("### 🧬 Mutation Impact")
            st.info(explain_mutation(gene, mutation))

        st.markdown("---")

    # ---------------- COMPARISON ----------------
    if len(results) > 1:
        st.markdown("## 📊 Multi-Gene Comparison")

        compare_df = pd.DataFrame({
            gene: {
                "Protein Length (aa)": results[gene]["protein_length_aa"],
                "Molecular Weight (kDa)": results[gene]["molecular_weight_kDa"]
            }
            for gene in results
        }).T

        st.dataframe(compare_df)

        fig, ax = plt.subplots()
        compare_df.plot(kind="bar", ax=ax)
        ax.set_title("Protein Property Comparison")
        st.pyplot(fig)

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style="text-align:center; font-size:14px; color:gray;">
ShubhgeneAI © 2026<br>
Offline AI Simulation for Academic Demonstration
</p>
""", unsafe_allow_html=True)
