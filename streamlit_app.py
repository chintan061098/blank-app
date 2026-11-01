import os
import json
import time
import urllib.parse
from typing import Optional, Callable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st
import plotly.express as px

# --------------------------------------------------------------------------
# App configuration
# --------------------------------------------------------------------------
st.set_page_config(page_title='Gene-SphereAI', page_icon='🧬', layout='wide')

TIMEOUT = int(os.getenv('APP_TIMEOUT', '25'))
MAX_QUESTION_CHARS = 800

NCBI = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
GDC = 'https://api.gdc.cancer.gov'
UNIPROT = 'https://rest.uniprot.org'
COSMIC = 'https://pmc.ncbi.nlm.nih.gov/articles/PMC10767972/'

GENE_DB = {
 'TP53': {'full_name':'Tumor protein p53','type':'Tumor suppressor','function':'Regulates cell-cycle arrest, DNA-damage responses and apoptosis.','length':393,'mass':53,'pathway':'DNA damage response; cell-cycle checkpoints; apoptosis','disease':'Alterations are associated with several cancers; interpretation depends on variant and context.','chromosome':'17p13.1'},
 'BRCA1': {'full_name':'BRCA1 DNA repair associated','type':'Tumor suppressor','function':'Participates in DNA-damage response and homologous recombination repair.','length':1863,'mass':220,'pathway':'Homologous recombination and DNA damage response','disease':'Pathogenic variants can increase risk of breast, ovarian and other cancers.','chromosome':'17q21'},
 'EGFR': {'full_name':'Epidermal growth factor receptor','type':'Receptor tyrosine kinase / proto-oncogene','function':'Cell-surface receptor involved in growth and survival signaling.','length':1210,'mass':134,'pathway':'EGFR, MAPK and PI3K-AKT signaling','disease':'Alterations occur in several cancers; clinical relevance is disease- and variant-specific.','chromosome':'7p11.2'},
 'CFTR': {'full_name':'CF transmembrane conductance regulator','type':'Ion channel gene','function':'Encodes a chloride/bicarbonate channel important for epithelial fluid balance.','length':1480,'mass':170,'pathway':'Epithelial ion transport','disease':'Biallelic disease-causing variants can cause cystic fibrosis.','chromosome':'7q31.2'},
 'APOE': {'full_name':'Apolipoprotein E','type':'Lipid metabolism','function':'Participates in lipid transport and lipoprotein metabolism.','length':299,'mass':34,'pathway':'Lipoprotein metabolism','disease':'APOE alleles can influence risk; they are not deterministic diagnoses.','chromosome':'19q13.32'},
 'HBB': {'full_name':'Hemoglobin subunit beta','type':'Structural protein','function':'Encodes the beta-globin component of adult hemoglobin.','length':147,'mass':16,'pathway':'Oxygen transport','disease':'Some variants cause sickle cell disease or beta thalassemia.','chromosome':'11p15.4'},
 'INS': {'full_name':'Insulin','type':'Hormone','function':'Encodes insulin, a key regulator of blood glucose.','length':110,'mass':None,'pathway':'Glucose homeostasis','disease':'Insulin biology is central to diabetes; mechanisms vary.','chromosome':'11p15.5'},
 'VEGFA': {'full_name':'Vascular endothelial growth factor A','type':'Growth factor','function':'Supports blood-vessel formation and vascular permeability.','length':232,'mass':27,'pathway':'Angiogenesis','disease':'VEGF signaling is relevant to cancer and retinal vascular disease.','chromosome':'6p21.1'},
 'MYC': {'full_name':'MYC proto-oncogene','type':'Proto-oncogene','function':'Regulates transcription, growth, metabolism and cell proliferation.','length':439,'mass':49,'pathway':'Transcriptional regulation and cell growth','disease':'Dysregulated MYC activity is implicated in multiple cancers.','chromosome':'8q24.21'},
 'MTHFR': {'full_name':'Methylenetetrahydrofolate reductase','type':'Metabolic enzyme','function':'Participates in folate and one-carbon metabolism.','length':656,'mass':74,'pathway':'Folate and homocysteine metabolism','disease':'Common variants should not be interpreted as standalone diagnoses.','chromosome':'1p36.22'},
}


# --------------------------------------------------------------------------
# Networking: a single session with retries/backoff for transient failures
# --------------------------------------------------------------------------
def _build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'POST'],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    s.headers.update({'User-Agent': 'Gene-SphereAI-educational-prototype/1.0'})
    return s

SESSION = _build_session()


def describe_error(e: Exception) -> str:
    """Turn raw exceptions into messages a non-technical user can act on."""
    if isinstance(e, requests.exceptions.Timeout):
        return 'The request timed out. The external database may be slow or unreachable right now. Please try again.'
    if isinstance(e, requests.exceptions.ConnectionError):
        return 'Could not connect to the external database. Please check your network connection and try again.'
    if isinstance(e, requests.exceptions.HTTPError):
        code = e.response.status_code if e.response is not None else 'unknown'
        return f'The external database returned an error (HTTP {code}). It may be temporarily unavailable.'
    if isinstance(e, (ValueError, json.JSONDecodeError)):
        return 'The external database returned a response that could not be understood (not valid JSON).'
    if isinstance(e, RuntimeError):
        return str(e)
    return f'An unexpected error occurred: {e}'


def get_json(url: str, params: Optional[dict] = None) -> dict:
    try:
        r = SESSION.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError, ValueError, json.JSONDecodeError):
        raise
    except Exception as e:  # anything unforeseen still surfaces cleanly
        raise RuntimeError(f'Unexpected failure while contacting {url}: {e}')


def quote(value) -> str:
    """URL-encode any value used inside a hand-built link."""
    return urllib.parse.quote_plus(str(value))


# --------------------------------------------------------------------------
# Fault isolation: one broken tab must never take the whole app down
# --------------------------------------------------------------------------
def safe_section(render_fn: Callable, title: str = 'This section'):
    try:
        render_fn()
    except Exception as e:
        st.error(f'{title} could not be displayed because of an unexpected error. '
                 f'Other tabs are unaffected.')
        with st.expander('Technical details (for debugging)'):
            st.exception(e)


def render_link_table(df: pd.DataFrame, link_col: str = 'Source'):
    """Render a dataframe with a clickable link column, without raw HTML (avoids injection)."""
    if link_col in df.columns:
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={link_col: st.column_config.LinkColumn(link_col, display_text='Open ↗')},
        )
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# External data sources
# --------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def ncbi_gene(symbol: str) -> dict:
    data = get_json(f'{NCBI}/esearch.fcgi', {
        'db': 'gene', 'term': f'{symbol}[Gene Name] AND Homo sapiens[Organism]',
        'retmode': 'json', 'retmax': 5,
    })
    ids = (data.get('esearchresult') or {}).get('idlist') or []
    if not ids:
        return {'found': False, 'message': 'No human NCBI Gene record found.'}

    time.sleep(0.34)  # be polite to the unauthenticated eutils rate limit (~3 req/s)
    summary = get_json(f'{NCBI}/esummary.fcgi', {'db': 'gene', 'id': ids[0], 'retmode': 'json'})
    s = (summary.get('result') or {}).get(ids[0]) or {}
    if not isinstance(s, dict):
        raise RuntimeError('NCBI returned an unexpected summary structure.')

    return {
        'found': True, 'id': ids[0], 'name': s.get('name', symbol),
        'description': s.get('description', ''), 'summary': s.get('summary', ''),
        'map': s.get('maplocation', ''), 'url': f'https://www.ncbi.nlm.nih.gov/gene/{ids[0]}',
    }


@st.cache_data(ttl=3600, show_spinner=False)
def uniprot_gene(symbol: str) -> dict:
    data = get_json(f'{UNIPROT}/uniprotkb/search', {
        'query': f'(gene_exact:{symbol}) AND (organism_id:9606) AND (reviewed:true)',
        'format': 'json', 'size': 1, 'fields': 'accession,protein_name,gene_names,length,mass',
    })
    hits = data.get('results') or []
    if not hits:
        return {'found': False, 'message': 'No reviewed human UniProt record returned.'}

    x = hits[0]
    pdsc = x.get('proteinDescription') or {}
    pname = ((pdsc.get('recommendedName') or {}).get('fullName') or {}).get('value', '')
    accession = x.get('primaryAccession', '')
    return {
        'found': True, 'accession': accession, 'protein_name': pname,
        'length': (x.get('sequence') or {}).get('length'),
        'url': f'https://www.uniprot.org/uniprotkb/{accession}',
    }

# --------------------------------------------------
# PROTEIN STRUCTURE EXPLORER
# --------------------------------------------------

def get_uniprot_accession(symbol: str) -> Optional[str]:
    url = "https://rest.uniprot.org/uniprotkb/search"
    params = {
        "query": f"(gene_exact:{symbol}) AND (organism_id:9606) AND (reviewed:true)",
        "format": "json",
        "size": 1
    }
    data = get_json(url, params)
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("primaryAccession")


def get_protein_structure(symbol: str) -> Optional[dict]:
    accession = get_uniprot_accession(symbol)
    if not accession:
        return None
    structure_url = f"https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v4.pdb"
    return {
        "accession": accession,
        "structure_url": structure_url,
        "uniprot_url": f"https://www.uniprot.org/uniprotkb/{accession}",
        "alphafold_url": f"https://alphafold.ebi.ac.uk/entry/{accession}"
    }

def gdc_gene_exploration_url(project: str, symbol: str) -> str:
    filters = {
        'op': 'and',
        'content': [
            {'op': 'in', 'content': {'field': 'cases.project.project_id', 'value': [project]}},
            {'op': 'in', 'content': {'field': 'genes.symbol', 'value': [symbol]}},
        ],
    }
    return 'https://portal.gdc.cancer.gov/exploration?filters=' + quote(json.dumps(filters))


def render_protein_structure_1(selected_gene: str):
    st.subheader("Protein Structure Explorer")
    st.write("Explore the protein sequence, structure and functional features of the selected gene.")
    
    if st.button("Retrieve Protein Structure", key="btn_protein_struct"):
        with st.spinner("Retrieving protein information..."):
            # Pass the selected gene explicitly
            result = get_protein_structure(selected_gene)
            if result:
                st.success(f"UniProt accession: {result['accession']}")
                st.link_button("Open AlphaFold 3D Structure", result["alphafold_url"])
                st.link_button("Open UniProt Protein Record", result["uniprot_url"])
                st.markdown("### Structure file")
                st.link_button("Download / view PDB file", result["structure_url"])
            else:
                st.warning("No reviewed UniProt protein record found.")


# --------------------------------------------------
# PROTEIN STRUCTURE EXPLORER
# --------------------------------------------------

def get_uniprot_accession(symbol):

    url = (
        "https://rest.uniprot.org/uniprotkb/search"
    )

    params = {
        "query": (
            f"(gene_exact:{symbol}) "
            "AND (organism_id:9606) "
            "AND (reviewed:true)"
        ),
        "format": "json",
        "size": 1
    }

    data = get_json(url, params)

    results = data.get("results", [])

    if not results:
        return None

    return results[0].get("primaryAccession")


def get_protein_structure(symbol):

    accession = get_uniprot_accession(symbol)

    if not accession:
        return None

    # AlphaFold structure download link
    structure_url = (
        "https://alphafold.ebi.ac.uk/files/"
        f"AF-{accession}-F1-model_v4.pdb"
    )

    return {
        "accession": accession,
        "structure_url": structure_url,
        "uniprot_url": (
            f"https://www.uniprot.org/uniprotkb/{accession}"
        ),
        "alphafold_url": (
            f"https://alphafold.ebi.ac.uk/entry/{accession}"
        )
    }


def render_protein_structure():

    st.subheader("Protein Structure Explorer")

    st.write(
        "Explore the protein sequence, structure "
        "and functional features of the selected gene."
    )

    if st.button("Retrieve Protein Structure"):

        with st.spinner("Retrieving protein information..."):

            result = get_protein_structure(gene)

            if result:

                st.success(
                    f"UniProt accession: "
                    f"{result['accession']}"
                )

                st.link_button(
                    "Open AlphaFold 3D Structure",
                    result["alphafold_url"]
                )

                st.link_button(
                    "Open UniProt Protein Record",
                    result["uniprot_url"]
                )

                st.markdown(
                    "### Structure file"
                )

                st.link_button(
                    "Download / view PDB file",
                    result["structure_url"]
                )

            else:

                st.warning(
                    "No reviewed UniProt protein record found."
                )



@st.cache_data(ttl=1800, show_spinner=False)
def clinvar_search(symbol: str, limit: int = 25) -> pd.DataFrame:
    limit = max(1, min(int(limit), 200))
    data = get_json(f'{NCBI}/esearch.fcgi', {
        'db': 'clinvar', 'term': f'{symbol}[gene] AND human[orgn]',
        'retmode': 'json', 'retmax': limit, 'sort': 'relevance',
    })
    ids = (data.get('esearchresult') or {}).get('idlist') or []
    if not ids:
        return pd.DataFrame()

    time.sleep(0.34)
    summary = get_json(f'{NCBI}/esummary.fcgi', {'db': 'clinvar', 'id': ','.join(ids), 'retmode': 'json'})
    result = summary.get('result') or {}

    rows = []
    for uid in ids:
        x = result.get(uid)
        if not isinstance(x, dict):
            continue
        gc = x.get('germline_classification')
        gc = gc if isinstance(gc, dict) else {}
        rows.append({
            'ClinVar ID': uid,
            'Variant / condition': x.get('title', ''),
            'Clinical significance': gc.get('description', 'Not stated'),
            'Review status': gc.get('review_status', 'Not stated'),
            'Last evaluated': gc.get('last_evaluated', ''),
            'Source': f'https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/',
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=1800, show_spinner=False)
def gdc_catalog(project: str, category: str, limit: int = 100) -> pd.DataFrame:
    limit = max(1, min(int(limit), 500))
    content = [
        {'op': 'in', 'content': {'field': 'cases.project.project_id', 'value': [project]}},
        {'op': 'in', 'content': {'field': 'data_category', 'value': [category]}},
        {'op': 'in', 'content': {'field': 'access', 'value': ['open']}},
    ]
    if category == 'Transcriptome Profiling':
        content += [
            {'op': 'in', 'content': {'field': 'data_type', 'value': ['Gene Expression Quantification']}},
            {'op': 'in', 'content': {'field': 'analysis.workflow_type', 'value': ['STAR - Counts']}},
        ]
    filters = {'op': 'and', 'content': content}
    fields = 'file_id,file_name,data_type,data_format,file_size,cases.submitter_id,cases.project.project_id,cases.samples.sample_type'
    data = get_json(f'{GDC}/files', {
        'filters': json.dumps(filters), 'fields': fields, 'format': 'JSON', 'size': limit,
    })

    hits = ((data.get('data') or {}).get('hits')) or []
    rows = []
    for x in hits:
        if not isinstance(x, dict):
            continue
        cases = x.get('cases') or [{}]
        case = cases[0] if isinstance(cases[0], dict) else {}
        samples = case.get('samples') or [{}]
        sample0 = samples[0] if samples and isinstance(samples[0], dict) else {}
        rows.append({
            'File': x.get('file_name', ''),
            'Data type': x.get('data_type', ''),
            'Format': x.get('data_format', ''),
            'Sample': case.get('submitter_id', ''),
            'Sample type': sample0.get('sample_type', ''),
            'Size (MB)': round((x.get('file_size') or 0) / 1e6, 2),
            'Source': f"https://portal.gdc.cancer.gov/files/{x.get('file_id', '')}",
        })
    return pd.DataFrame(rows)


def get_gemini_key() -> str:
    key = ''
    try:
        key = st.secrets.get('GEMINI_API_KEY', '')
    except Exception:
        key = ''
    return key or os.getenv('GEMINI_API_KEY', '')


def gemini_explain(symbol: str, facts: dict, question: str) -> str:
    key = get_gemini_key()
    if not key:
        raise RuntimeError('Gemini key missing. Add GEMINI_API_KEY in Streamlit Secrets or environment variables.')

    question = (question or '').strip()
    if not question:
        raise RuntimeError('Please enter a question before requesting an explanation.')
    if len(question) > MAX_QUESTION_CHARS:
        question = question[:MAX_QUESTION_CHARS]

    prompt = f'''You are a cautious bioinformatics teaching assistant. Explain only the supplied
information; do not invent variants, measurements, treatments or citations. State uncertainty.
If the question asks for a personal diagnosis, dosage or individualized treatment plan, decline
and recommend consulting a qualified clinician instead. Educational use only, not diagnosis or
medical advice.

Gene: {symbol}
Curated facts: {facts}
Student question: {question}

Use headings: Explanation, Biological context, Limitations, Sources to verify.'''

    try:
        r = SESSION.post(
            'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',
            headers={'Content-Type': 'application/json', 'x-goog-api-key': key},
            json={'contents': [{'parts': [{'text': prompt}]}]},
            timeout=TIMEOUT,
        )
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        raise

    if r.status_code == 429:
        raise RuntimeError('Gemini quota/rate limit exceeded. Please wait a moment and try again.')
    if r.status_code in (401, 403):
        raise RuntimeError('Gemini API key invalid or unauthorized. Check GEMINI_API_KEY.')
    r.raise_for_status()

    try:
        data = r.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError, TypeError, json.JSONDecodeError, ValueError):
        raise RuntimeError('Gemini returned an unexpected response. Check key, quota and model access.')


def references(gene: str):
    a, b, c = st.columns(3)
    a.link_button('NCBI Gene', f'https://www.ncbi.nlm.nih.gov/gene/?term={quote(gene)}')
    b.link_button('UniProt', f'https://www.uniprot.org/uniprotkb?query={quote(gene)}')
    c.link_button('ClinVar', f'https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(gene)}[gene]')


def gdc_gene_exploration_url(project: str, symbol: str) -> str:
    filters = {
        'op': 'and',
        'content': [
            {'op': 'in', 'content': {'field': 'cases.project.project_id', 'value': [project]}},
            {'op': 'in', 'content': {'field': 'genes.symbol', 'value': [symbol]}},
        ],
    }
    return 'https://portal.gdc.cancer.gov/exploration?filters=' + quote(json.dumps(filters))


# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------
st.markdown(
    '<h1 style="text-align:center">🧬 Gene-SphereAI</h1>'
    '<p style="text-align:center;color:gray">Hybrid Gene Intelligence Platform · Evidence first, AI assisted</p>',
    unsafe_allow_html=True,
)
st.caption('Student bioinformatics prototype · Public data may change · Not a diagnostic tool')

with st.sidebar:
    st.header('⚙️ Analysis settings')
    mode = st.radio('Mode', ['Offline / demo', 'Online / live data'])
    gene = st.selectbox('Choose gene', list(GENE_DB.keys()), index=1)
    project = st.selectbox('TCGA project', ['TCGA-BRCA', 'TCGA-LUAD', 'TCGA-LUSC', 'TCGA-COAD', 'TCGA-GBM', 'TCGA-OV', 'TCGA-PRAD'])
    st.caption('Online mode uses public NCBI, UniProt and GDC endpoints. Gemini explanations require GEMINI_API_KEY.')

facts = GENE_DB[gene]
tabs = st.tabs(['Overview', 'Mutations', 'Gene expression', 'DNA methylation', 'Protein structure', 'Treatments', 'AI explanation'])


# --------------------------------------------------------------------------
# Tab 1: Overview
# --------------------------------------------------------------------------
def render_overview():
    st.subheader(f'{gene} — gene and protein overview')
    st.write(facts['function'])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Gene type', facts['type'])
    c2.metric('Protein length', f"{facts['length']:,} aa")
    c3.metric('Approx. mass', f"{facts['mass']} kDa" if facts['mass'] else 'Not available')
    c4.metric('Chromosome', facts['chromosome'])

    left, right = st.columns(2)
    with left:
        st.markdown('#### Curated educational summary')
        st.write('**Full name:**', facts['full_name'])
        st.write('**Pathway / process:**', facts['pathway'])
        st.write('**Disease context:**', facts['disease'])
        st.plotly_chart(
            px.bar(pd.DataFrame({'Measure': ['Protein length (aa)'], 'Value': [facts['length']]}),
                   x='Measure', y='Value', title='Reference protein length'),
            use_container_width=True,
        )
    with right:
        st.markdown('#### Live database records')
        if mode == 'Online / live data':
            if st.button('Retrieve NCBI + UniProt records'):
                with st.spinner('Retrieving NCBI record…'):
                    try:
                        st.session_state[f'ncbi_{gene}'] = ncbi_gene(gene)
                    except Exception as e:
                        st.session_state[f'ncbi_{gene}'] = None
                        st.error(f'NCBI lookup failed: {describe_error(e)}')
                with st.spinner('Retrieving UniProt record…'):
                    try:
                        st.session_state[f'uni_{gene}'] = uniprot_gene(gene)
                    except Exception as e:
                        st.session_state[f'uni_{gene}'] = None
                        st.error(f'UniProt lookup failed: {describe_error(e)}')

            n = st.session_state.get(f'ncbi_{gene}')
            u = st.session_state.get(f'uni_{gene}')
            if n:
                if n.get('found'):
                    st.success(f"NCBI Gene ID: {n['id']}")
                    st.write(n.get('summary') or n.get('description') or 'No description provided.')
                    st.link_button('View NCBI record', n['url'])
                else:
                    st.info(n['message'])
            if u:
                if u.get('found'):
                    st.write('**UniProt accession:**', u['accession'])
                    st.write('**Protein:**', u['protein_name'] or 'Not provided')
                    st.write('**Length:**', u['length'] or 'Not provided')
                    st.link_button('View UniProt record', u['url'])
                else:
                    st.info(u['message'])
            if not n and not u:
                st.info('Click the button to retrieve current records.')
        else:
            st.info('Offline mode uses curated local examples. Switch to Online mode for live public records.')
    references(gene)


with tabs[0]:
    safe_section(render_overview, 'Overview tab')


# --------------------------------------------------------------------------
# Tab 2: Mutations
# --------------------------------------------------------------------------
def render_mutations():
    st.subheader('Mutation and clinical-variant explorer')
    st.warning('A gene symbol alone does not identify a person’s variant. Clinical classifications are '
               'evidence summaries, not personal risk predictions.')
    if mode == 'Online / live data':
        limit = st.slider('Maximum ClinVar records', 10, 100, 25, 5)
        if st.button('Retrieve ClinVar variants'):
            with st.spinner('Searching ClinVar…'):
                try:
                    st.session_state[f'clinvar_{gene}'] = clinvar_search(gene, limit)
                except Exception as e:
                    st.session_state[f'clinvar_{gene}'] = None
                    st.error(f'ClinVar query failed: {describe_error(e)}')
        df = st.session_state.get(f'clinvar_{gene}')
        if isinstance(df, pd.DataFrame):
            if df.empty:
                st.info('No records returned for this query.')
            else:
                render_link_table(df)
    else:
        st.info('Offline mode does not simulate mutation effects. Switch to Online mode to query ClinVar.')
    references(gene)


with tabs[1]:
    safe_section(render_mutations, 'Mutations tab')


# --------------------------------------------------------------------------
# Tab 3: Gene expression
# --------------------------------------------------------------------------
def render_expression():
    st.subheader(f'TCGA gene expression: {gene} in {project}')
    st.write(f'Explore open-access GDC RNA-seq files and transcriptome profiling data for **{gene}** '
             f'within the **{project}** cohort.')

    st.markdown('#### 🔗 Direct GDC Portal Integration')
    st.link_button(f'Explore {gene} expression in {project} on GDC Portal', gdc_gene_exploration_url(project, gene))

    st.markdown('---')
    st.subheader('Project Transcriptome Files (STAR - Counts)')
    st.info('This version discovers STAR count files and visualizes sample type distributions for the selected project. '
            'It does not yet download, aggregate and statistically compare gene-level expression measurements.')

    if mode == 'Online / live data':
        if st.button('Check GDC expression data availability'):
            with st.spinner(f'Checking {project}…'):
                try:
                    st.session_state[f'expr_{project}'] = gdc_catalog(project, 'Transcriptome Profiling')
                except Exception as e:
                    st.session_state[f'expr_{project}'] = None
                    st.error(f'GDC query failed: {describe_error(e)}')

        df = st.session_state.get(f'expr_{project}')
        if isinstance(df, pd.DataFrame):
            st.metric('Files returned', len(df))
            if df.empty:
                st.info('No matching files returned. Try another project.')
            else:
                if 'Sample type' in df.columns:
                    sample_counts = df['Sample type'].value_counts().reset_index()
                    sample_counts.columns = ['Sample Type', 'Count']
                    fig = px.bar(sample_counts, x='Sample Type', y='Count', title=f'Sample Type Distribution in {project}')
                    st.plotly_chart(fig, use_container_width=True)
                render_link_table(df)
    else:
        st.info('Online mode is required to check GDC. Offline mode does not invent expression measurements.')
    references(gene)


with tabs[2]:
    safe_section(render_expression, 'Gene expression tab')


# --------------------------------------------------------------------------
# Tab 4: DNA methylation
# --------------------------------------------------------------------------
def render_methylation():
    st.subheader('TCGA DNA methylation')
    st.write('First discover public methylation files for a cancer project.')
    st.warning('This version does not yet calculate CpG beta values, annotate probes, match methylation to '
               'expression samples, or compute correlations.')
    if mode == 'Online / live data':
        if st.button('Check GDC methylation data availability'):
            with st.spinner(f'Checking methylation files for {project}…'):
                try:
                    st.session_state[f'meth_{project}'] = gdc_catalog(project, 'DNA Methylation')
                except Exception as e:
                    st.session_state[f'meth_{project}'] = None
                    st.error(f'GDC query failed: {describe_error(e)}')
        df = st.session_state.get(f'meth_{project}')
        if isinstance(df, pd.DataFrame):
            st.metric('Files returned', len(df))
            if df.empty:
                st.info('No matching open-access files returned.')
            else:
                render_link_table(df)
    else:
        st.info('Online mode is required to check GDC. No methylation values are fabricated in offline mode.')
    references(gene)


with tabs[3]:
    safe_section(render_methylation, 'DNA methylation tab')


with tabs[4]:
    safe_section(render_protein_structure_1, 'Protein structure tab')


# --------------------------------------------------------------------------
# Tab 5: Treatments
# --------------------------------------------------------------------------
def render_treatments():
    st.subheader('Disease treatment and application information')
    st.warning('Educational research only. Treatment depends on diagnosis, disease stage, exact variant, '
               'current guidelines and clinical judgement.')
    st.write('This version supplies reliable starting points rather than inferring a treatment from a gene alone.')
    st.markdown(f'- [NCI cancer information search for {gene}](https://www.cancer.gov/search/results?swKeyword={quote(gene)})')
    st.markdown(f'- [ClinicalTrials.gov studies involving {gene}](https://clinicaltrials.gov/search?term={quote(gene)})')
    st.markdown(f'- [ClinVar variant interpretations for {gene}](https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(gene)}[gene])')
    st.markdown(f'- [NCBI Gene background for {gene}](https://www.ncbi.nlm.nih.gov/gene/?term={quote(gene)})')
    st.caption('Structured treatment evidence, approval status and guideline dates are a future implementation step. '
               'These links are not treatment recommendations.')


with tabs[5]:
    safe_section(render_treatments, 'Treatments tab')


# --------------------------------------------------------------------------
# Tab 6: AI explanation
# --------------------------------------------------------------------------
def render_ai():
    st.subheader('Gemini-assisted explanation')
    st.write('Gemini explains supplied information; it is not the source of scientific facts or clinical classifications.')
    question = st.text_area(
        'What would you like explained?',
        f'Explain the biological role of {gene} for a microbiology student.',
        max_chars=MAX_QUESTION_CHARS,
    )
    if st.button('Generate explanation with Gemini'):
        with st.spinner('Preparing explanation…'):
            try:
                answer = gemini_explain(gene, facts, question)
                st.markdown(answer)
                st.caption('AI-generated explanation. Verify scientific details against linked source records.')
            except requests.HTTPError as e:
                st.error(f'Gemini request failed. {describe_error(e)}')
            except Exception as e:
                st.error(describe_error(e))
    references(gene)


with tabs[6]:
    safe_section(render_ai, 'AI explanation tab')


st.markdown('---')
st.markdown(
    '<div style="text-align:center;color:gray;font-size:.85rem">'
    'Gene-SphereAI · Evidence first, AI assisted · Not for diagnosis or treatment decisions</div>',
    unsafe_allow_html=True,
)
