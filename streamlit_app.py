import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="ShubhgeneAI",
    page_icon="🧬",
    layout="wide"
)

# ---------------- SESSION STATE ----------------
if "poster_mode" not in st.session_state:
    st.session_state.poster_mode = False

# ---------------- HEADER ----------------
title_size = "2.8rem" if st.session_state.poster_mode else "2.2rem"
subtitle_size = "1.6rem" if st.session_state.poster_mode else "1.2rem"

st.markdown(f"""
<div style="text-align:center">
    <h1 style="font-size:{title_size}">🧬 ShubhgeneAI</h1>
    <h3 style="font-size:{subtitle_size}">AI-Inspired Gene Intelligence Platform</h3>
    <p style="color:gray">Offline Scientific Demonstration System</p>
</div>
<hr>
""", unsafe_allow_html=True)

# ---------------- LOCAL GENE DATABASE ----------------
GENE_DB = {
    "TP53": {
        "gene_type": "Tumor Suppressor",
        "function": "Controls cell cycle and induces apoptosis in response to DNA damage",
        "protein_length_aa": 393,
        "molecular_weight_kDa": 53,
        "pathways": "Cell cycle regulation, DNA repair",
        "disease_association": "Breast cancer, lung cancer, leukemia"
    },
    "BRCA1": {
        "gene_type": "Tumor Suppressor",
        "function": "Repairs DNA double-strand breaks via homologous recombination",
        "protein_length_aa": 1863,
        "molecular_weight_kDa": 220,
        "pathways": "DNA damage response",
        "disease_association": "Breast and ovarian cancer"
    },
    "EGFR": {
        "gene_type": "Proto-oncogene",
        "function": "Regulates cell growth and proliferation via signal transduction",
        "protein_length_aa": 1210,
        "molecular_weight_kDa": 134,
        "pathways": "MAPK, PI3K-AKT",
        "disease_association": "Lung cancer, glioblastoma"
    }
}

# ---------------- CORE FUNCTIONS ----------------
def get_gene_info(gene):
    return GENE_DB.get(gene)

def explain_mutation(gene, mutation):
    return (
        f"Mutation {mutation} in {gene} may alter amino-acid structure, "
        f"impacting protein stability or signaling efficiency. "
        f"Such mutations are frequently linked to pathological phenotypes "
        f"and altered therapeutic response."
    )

def ai_reasoning_steps(gene):
    return [
        f"Identified {gene} as a known human gene",
        "Analyzed gene classification and molecular role",
        "Evaluated protein structure properties",
        "Linked biological pathways to disease relevance",
        "Generated mutation impact hypothesis"
    ]

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙️ Controls")

genes = st.sidebar.multiselect(
    "Select Gene(s)",
    list(GENE_DB.keys()),
    default=["TP53"]
)

mutation = st.sidebar.text_input("Optional Mutation (e.g. p.R175H)")

st.sidebar.checkbox(
    "Poster / Presentation Mode",
    value=st.session_state.poster_mode,
    on_change=lambda: st.session_state.update(
        {"poster_mode": not st.session_state.poster_mode}
    )
)

# ---------------- ANALYSIS BUTTON ----------------
if st.button("🔬 Run Analysis"):

    if not genes:
        st.warning("Please select at least one gene.")
        st.stop()

    # -------- FAKE AI THINKING --------
    with st.spinner("AI model analyzing genomic data..."):
        time.sleep(1.5)

    for gene in genes:
        data = get_gene_info(gene)

        if not data:
            st.error(f"No data available for {gene}")
            continue

        st.markdown(f"## 🧬 {gene}")

        # -------- TABLE --------
        df = pd.DataFrame({
            "Category": data.keys(),
            "Details": data.values()
        })
        st.table(df)

        # -------- MUTATION --------
        if mutation:
            st.markdown("### 🧬 Mutation Impact")
            st.info(explain_mutation(gene, mutation))

        # -------- AI REASONING --------
        with st.expander("🧠 AI Reasoning Steps"):
            for step in ai_reasoning_steps(gene):
                st.markdown(f"- {step}")

        # -------- CITATIONS --------
        st.markdown("### 📚 Scientific References")
        col1, col2 = st.columns(2)
        with col1:
            st.link_button(
                "🔗 NCBI Gene",
                f"https://www.ncbi.nlm.nih.gov/gene/?term={gene}"
            )
        with col2:
            st.link_button(
                "🔗 UniProt",
                f"https://www.uniprot.org/uniprotkb?query={gene}"
            )

        st.markdown("---")

    # -------- COMPARISON --------
    if len(genes) > 1:
        st.markdown("## 📊 Comparative Analysis")

        compare_df = pd.DataFrame({
            gene: {
                "Protein Length (aa)": GENE_DB[gene]["protein_length_aa"],
                "Molecular Weight (kDa)": GENE_DB[gene]["molecular_weight_kDa"]
            }
            for gene in genes
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
Offline AI Simulation for Academic Demonstration
</p>
""", unsafe_allow_html=True)
