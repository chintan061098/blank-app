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

# ---------------- OFFLINE MODE FLAG ----------------
OFFLINE_MODE = True  # 🔒 Hard enforced for science fair reliability

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align:center">
    <h1>🧬 ShubhgeneAI</h1>
    <h3 style="color:gray">Hybrid Gene Intelligence Platform</h3>
</div>
""", unsafe_allow_html=True)

if OFFLINE_MODE:
    st.success("🟢 Offline Mode Active — No Internet or API Required")
else:
    st.info("🌐 Online Mode Active")

st.markdown("---")

# ---------------- LOCAL OFFLINE DATABASE ----------------
GENE_DB = {
    "TP53": {
        "Gene Type": "Tumor Suppressor",
        "Function": "Cell cycle arrest and apoptosis",
        "Protein Length (aa)": 393,
        "Molecular Weight (kDa)": 53,
        "Pathway": "DNA damage checkpoint",
        "Disease": "Multiple cancers"
    },
    "BRCA1": {
        "Gene Type": "Tumor Suppressor",
        "Function": "DNA double strand break repair",
        "Protein Length (aa)": 1863,
        "Molecular Weight (kDa)": 220,
        "Pathway": "Homologous recombination",
        "Disease": "Breast & ovarian cancer"
    },
    "EGFR": {
        "Gene Type": "Oncogene",
        "Function": "Growth factor receptor signaling",
        "Protein Length (aa)": 1210,
        "Molecular Weight (kDa)": 134,
        "Pathway": "MAPK / PI3K-AKT",
        "Disease": "Lung cancer"
    }
}

# ---------------- OFFLINE AI SIMULATION ----------------
def offline_ai_analysis(gene, mutation=None):
    steps = [
        f"Loaded offline genomic profile for {gene}",
        "Analyzed protein structural attributes",
        "Mapped biological pathway involvement",
        "Estimated disease relevance using known biology"
    ]
    if mutation:
        steps.append(f"Simulated functional impact of mutation {mutation}")
    return steps

# ---------------- SIDEBAR ----------------
st.sidebar.header("⚙ Controls")

selected_genes = st.sidebar.multiselect(
    "Select Gene(s)",
    list(GENE_DB.keys()),
    default=["TP53"]
)

mutation = st.sidebar.text_input("Mutation (optional)", "p.R175H")

run = st.sidebar.button("🔬 Run Analysis")

# ---------------- MAIN ANALYSIS ----------------
if run:

    with st.spinner("Running offline AI simulation..."):
        time.sleep(1.2)

    for gene in selected_genes:
        data = GENE_DB[gene]

        st.markdown(f"## 🧬 {gene}")

        # -------- DATA TABLE --------
        df = pd.DataFrame({
            "Property": data.keys(),
            "Description": data.values()
        })
        st.table(df)

        # -------- PROTEIN LENGTH --------
        fig1, ax1 = plt.subplots()
        ax1.bar(["Protein Length"], [data["Protein Length (aa)"]])
        ax1.set_ylabel("Amino Acids")
        ax1.set_title("Protein Size")
        st.pyplot(fig1)

        # -------- MOLECULAR WEIGHT --------
        fig2, ax2 = plt.subplots()
        ax2.bar(["Molecular Weight"], [data["Molecular Weight (kDa)"]])
        ax2.set_ylabel("kDa")
        ax2.set_title("Protein Mass")
        st.pyplot(fig2)

        # -------- PATHWAY DIAGRAM --------
        fig3, ax3 = plt.subplots(figsize=(6, 2))
        ax3.text(0.1, 0.5, gene, fontsize=12, weight="bold")
        ax3.arrow(0.25, 0.5, 0.3, 0, head_width=0.05)
        ax3.text(0.6, 0.5, data["Pathway"], fontsize=11)
        ax3.axis("off")
        st.pyplot(fig3)

        # -------- MUTATION EFFECT --------
        if mutation:
            fig4, ax4 = plt.subplots()
            ax4.bar(
                ["Normal Protein", "Mutated Protein"],
                [100, 60],
            )
            ax4.set_ylabel("Functional Efficiency (%)")
            ax4.set_title(f"Simulated Effect of {mutation}")
            st.pyplot(fig4)

        # -------- AI REASONING --------
        with st.expander("🧠 Offline AI Reasoning"):
            for step in offline_ai_analysis(gene, mutation):
                st.markdown(f"- {step}")

        # -------- REFERENCES (OPTIONAL INTERNET) --------
        st.markdown("### 📚 External References (Optional)")
        st.caption("Links open only if internet is available")
        st.link_button("NCBI Gene", f"https://www.ncbi.nlm.nih.gov/gene/?term={gene}")
        st.link_button("UniProt", f"https://www.uniprot.org/uniprotkb?query={gene}")

        st.markdown("---")

    # -------- COMPARISON --------
    if len(selected_genes) > 1:
        st.markdown("## 📊 Gene Comparison")

        comp = pd.DataFrame({
            gene: {
                "Protein Length": GENE_DB[gene]["Protein Length (aa)"],
                "Molecular Weight": GENE_DB[gene]["Molecular Weight (kDa)"]
            }
            for gene in selected_genes
        }).T

        st.dataframe(comp)

        fig, ax = plt.subplots()
        comp.plot(kind="bar", ax=ax)
        ax.set_title("Protein Property Comparison")
        st.pyplot(fig)

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style="text-align:center;color:gray;font-size:14px">
ShubhgeneAI © 2026<br>
Offline-First AI Genomics Demonstration System
</p>
""", unsafe_allow_html=True)
