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

# ---------------- TITLE ----------------
st.markdown("""
<h1 style='text-align:center'>🧬 ShubhgeneAI</h1>
<h3 style='text-align:center;color:gray'>AI-Inspired Gene Visualization Platform</h3>
<hr>
""", unsafe_allow_html=True)

# ---------------- LOCAL DATABASE ----------------
GENE_DB = {
    "TP53": {
        "type": "Tumor Suppressor",
        "function": "Cell cycle arrest & apoptosis",
        "protein_length": 393,
        "molecular_weight": 53,
        "pathway": "Cell cycle checkpoint",
        "disease": "Multiple cancers"
    },
    "BRCA1": {
        "type": "Tumor Suppressor",
        "function": "DNA repair",
        "protein_length": 1863,
        "molecular_weight": 220,
        "pathway": "Homologous recombination",
        "disease": "Breast & ovarian cancer"
    },
    "EGFR": {
        "type": "Oncogene",
        "function": "Growth signaling",
        "protein_length": 1210,
        "molecular_weight": 134,
        "pathway": "MAPK / PI3K",
        "disease": "Lung cancer"
    }
}

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙ Controls")

genes = st.sidebar.multiselect(
    "Select Gene(s)",
    list(GENE_DB.keys()),
    default=["TP53"]
)

mutation = st.sidebar.text_input("Mutation (optional)", "p.R175H")

# ---------------- RUN ----------------
if st.sidebar.button("🔬 Analyze Gene"):

    with st.spinner("Analyzing genomic data..."):
        time.sleep(1.5)

    for gene in genes:
        g = GENE_DB[gene]

        st.markdown(f"## 🧬 {gene}")

        # -------- INFO TABLE --------
        df = pd.DataFrame({
            "Property": g.keys(),
            "Description": g.values()
        })
        st.table(df)

        # -------- PROTEIN LENGTH VISUAL --------
        st.markdown("### 📏 Protein Length Visualization")

        fig1, ax1 = plt.subplots()
        ax1.bar(["Protein Length"], [g["protein_length"]])
        ax1.set_ylabel("Amino Acids")
        ax1.set_title("Protein Size")
        st.pyplot(fig1)

        # -------- MOLECULAR WEIGHT --------
        st.markdown("### ⚖️ Molecular Weight")

        fig2, ax2 = plt.subplots()
        ax2.bar(["Molecular Weight"], [g["molecular_weight"]])
        ax2.set_ylabel("kDa")
        ax2.set_title("Protein Mass")
        st.pyplot(fig2)

        # -------- FUNCTIONAL PATHWAY DIAGRAM --------
        st.markdown("### 🧠 Functional Pathway")

        fig3, ax3 = plt.subplots(figsize=(6, 2))
        ax3.text(0.1, 0.5, gene, fontsize=12, weight="bold")
        ax3.arrow(0.25, 0.5, 0.3, 0, head_width=0.05)
        ax3.text(0.6, 0.5, g["pathway"], fontsize=11)
        ax3.axis("off")
        st.pyplot(fig3)

        # -------- MUTATION EFFECT --------
        st.markdown("### 🧪 Mutation Impact Simulation")

        fig4, ax4 = plt.subplots()
        ax4.bar(["Normal Protein", "Mutated Protein"], [100, 60])
        ax4.set_ylabel("Functional Efficiency (%)")
        ax4.set_title(f"Effect of {mutation}")
        st.pyplot(fig4)

        # -------- REFERENCES --------
        st.markdown("### 📚 References")
        st.link_button("NCBI Gene", f"https://www.ncbi.nlm.nih.gov/gene/?term={gene}")
        st.link_button("UniProt", f"https://www.uniprot.org/uniprotkb?query={gene}")

        st.markdown("---")

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style='text-align:center;color:gray'>
ShubhgeneAI – Offline AI Genomics Simulator<br>
Designed for College Science Fair Demonstration
</p>
""", unsafe_allow_html=True)
