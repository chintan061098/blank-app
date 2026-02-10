import streamlit as st
import json
import pandas as pd
import matplotlib.pyplot as plt
from openai import OpenAI

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

# ---------------- OPENAI CLIENT ----------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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

# ---------------- AI FUNCTIONS ----------------
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

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)


def explain_mutation(gene, mutation):
    prompt = f"""
    Explain the biological and clinical impact of mutation {mutation}
    in gene {gene}. Keep it short, clear, and academic.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content

# ---------------- MAIN ACTION ----------------
if st.button("🔬 Analyze Gene(s)"):

    if not genes:
        st.warning("Please select at least one gene.")
        st.stop()

    results = {}

    with st.spinner("Analyzing gene intelligence..."):
        for gene in genes:
            results[gene] = get_gene_info(gene)

    # ---------------- DISPLAY PER GENE ----------------
    for gene, data in results.items():
        st.markdown(f"## 🧬 {gene}")

        col1, col2 = st.columns([2, 1])

        with col1:
            df_info = pd.DataFrame({
                "Category": list(data.keys()),
                "Details": list(data.values())
            })
            st.table(df_info)

        with col2:
            st.image(
                f"https://string-db.org/api/image/network?identifiers={gene}&species=9606",
                caption="Protein Interaction Network (STRING DB)",
                use_container_width=True
            )

            st.image(
                f"https://alphafold.ebi.ac.uk/files/AF-{gene}-F1-model_v4.png",
                caption="Predicted Protein Structure (AlphaFold)",
                use_container_width=True
            )

        # ---------------- MUTATION ANALYSIS ----------------
        if mutation:
            st.markdown("### 🧬 Mutation Impact")
            st.info(explain_mutation(gene, mutation))

        st.markdown("---")

    # ---------------- COMPARISON CHART ----------------
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
        ax.set_ylabel("Value")
        ax.set_title("Protein Property Comparison")
        st.pyplot(fig)

# ---------------- FOOTER ----------------
st.markdown("""
<hr>
<p style="text-align:center; font-size:14px; color:gray;">
ShubhgeneAI © 2026<br>
Artificial Intelligence in Life Sciences<br>
College Science Fair Project
</p>
""", unsafe_allow_html=True)
