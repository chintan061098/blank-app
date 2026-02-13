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

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align:center">
    <h1>🧬 ShubhgeneAI</h1>
    <h3 style="color:gray">Hybrid Gene Intelligence Platform</h3>
</div>
<hr>
""", unsafe_allow_html=True)

# ---------------- MODE SELECTION ----------------
st.sidebar.header("⚙ System Mode")

mode = st.sidebar.radio(
    "Select Analysis Mode",
    ["Offline Mode (Recommended)", "Online Mode (Experimental)"]
)

# ---------------- LOCAL DATABASE ----------------
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
        "Function": "DNA repair",
        "Protein Length (aa)": 1863,
        "Molecular Weight (kDa)": 220,
        "Pathway": "Homologous recombination",
        "Disease": "Breast & ovarian cancer"
    },
    "EGFR": {
        "Gene Type": "Oncogene",
        "Function": "Growth signaling",
        "Protein Length (aa)": 1210,
        "Molecular Weight (kDa)": 134,
        "Pathway": "MAPK / PI3K-AKT",
        "Disease": "Lung cancer"
    }
}

# ---------------- AI FUNCTIONS ----------------
def offline_ai_reasoning(gene, mutation=None):
    steps = [
        f"Loaded curated gene data for {gene}",
        "Analyzed protein structure",
        "Mapped biological pathway",
        "Linked to disease relevance"
    ]
    if mutation:
        steps.append(f"Simulated mutation effect: {mutation}")
    return steps

def online_ai_enhancement_stub(gene):
    # Placeholder – NO exception raised
    return "Online AI enhancement unavailable (demo mode)"

# ---------------- SIDEBAR CONTROLS ----------------
st.sidebar.header("🔬 Analysis Controls")

genes = st.sidebar.multiselect(
    "Select Gene(s)",
    list(GENE_DB.keys()),
    default=["TP53"]
)

mutation = st.sidebar.text_input("Mutation (optional)", "p.R175H")
run = st.sidebar.button("Run Analysis")

# ---------------- MAIN EXECUTION ----------------
if run:

    if not genes:
        st.warning("Select at least one gene")
        st.stop()

    with st.spinner("Analyzing gene data..."):
        time.sleep(1)

    for gene in genes:
        data = GENE_DB[gene]

        st.markdown(f"## 🧬 {gene}")

        # -------- DATA TABLE --------
        df = pd.DataFrame({
            "Property": data.keys(),
            "Description": data.values()
        })
        st.table(df)

        # -------- VISUALS --------
        col1, col2 = st.columns(2)

        with col1:
            fig1, ax1 = plt.subplots()
            ax1.bar(["Protein Length"], [data["Protein Length (aa)"]])
            ax1.set_ylabel("Amino Acids")
            ax1.set_title("Protein Size")
            st.pyplot(fig1)

        with col2:
            fig2, ax2 = plt.subplots()
            ax2.bar(["Molecular Weight"], [data["Molecular Weight (kDa)"]])
            ax2.set_ylabel("kDa")
            ax2.set_title("Protein Mass")
            st.pyplot(fig2)

        # -------- PATHWAY DIAGRAM --------
        fig3, ax3 = plt.subplots(figsize=(6, 2))
        ax3.text(0.1, 0.5, gene, fontsize=12, weight="bold")
        ax3.arrow(0.3, 0.5, 0.3, 0, head_width=0.05)
        ax3.text(0.7, 0.5, data["Pathway"], fontsize=11)
        ax3.axis("off")
        st.pyplot(fig3)

        # -------- MUTATION --------
        if mutation:
            fig4, ax4 = plt.subplots()
            ax4.bar(["Normal Protein", "Mutated Protein"], [100, 60])
            ax4.set_ylabel("Functional Efficiency (%)")
            ax4.set_title(f"Mutation Impact: {mutation}")
            st.pyplot(fig4)

        # -------- AI REASONING --------
        with st.expander("🧠 AI Reasoning"):
            for step in offline_ai_reasoning(gene, mutation):
                st.markdown(f"- {step}")

            if mode.startswith("Online"):
                st.caption("🔍 Online enhancement attempted")
                st.caption(online_ai_enhancement_stub(gene))

        # -------- REFERENCES (ALWAYS VISIBLE) --------
        st.markdown("### 📚 External Scientific References")
        st.link_button(
            "NCBI Gene",
            f"https://www.ncbi.nlm.nih.gov/gene/?term={gene}"
        )
        st.link_button(
            "UniProt",
            f"https://www.uniprot.org/uniprotkb?query={gene}"
        )

        st.markdown("---")

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style="text-align:center;color:gray;font-size:14px">
ShubhgeneAI © 2026<br>
Resilient Hybrid AI Architecture for Academic Demonstration
</p>
""", unsafe_allow_html=True)
