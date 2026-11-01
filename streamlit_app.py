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
# Networking & Helper Functions
# --------------------------------------------------------------------------
def _build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3, connect=3, read=3, backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET', 'POST'], raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount('https://', adapter)
    s.mount('http://', adapter)
    s.headers.update({'User-Agent': 'Gene-SphereAI-educational-prototype/1.0'})
    return s

SESSION = _build_session()


def describe_error(e: Exception) -> str:
    if isinstance(e, requests.exceptions.Timeout):
        return 'The request timed out. External database may be slow or unreachable.'
    if isinstance(e, requests.exceptions.ConnectionError):
        return 'Could not connect to database. Check network connection.'
    if isinstance(e, requests.exceptions.HTTPError):
        code = e.response.status_code if e.response is not None else 'unknown'
        return f'External database returned error (HTTP {code}).'
    if isinstance(e, (ValueError, json.JSONDecodeError)):
        return 'Database returned invalid response format.'
    return f'An unexpected error occurred: {e}'


def get_json(url: str, params: Optional[dict] = None) -> dict:
    try:
        r = SESSION.get(url, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise RuntimeError(f'Unexpected failure while contacting {url}: {e}')


def quote(value) -> str:
    return urllib.parse.quote_plus(str(value))


def safe_section(render_fn: Callable, title: str = 'This section'):
    try:
        render_fn()
    except Exception as e:
        st.error(f'{title} could not be displayed. Other tabs are unaffected.')
        with st.expander('Technical details (for debugging)'):
            st.exception(e)


def render_link_table(df: pd.DataFrame, link_col: str = 'Source'):
    if link_col in df.columns:
        st.dataframe(
            df, use_container_width=True, hide_index=True,
            column_config={link_col: st.column_config.LinkColumn(link_col, display_text='Open ↗')},
        )
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# --------------------------------------------------------------------------
# External Data Retrieval
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

    time.sleep(0.34)
    summary = get_json(f'{NCBI}/esummary.fcgi', {'db': 'gene', 'id': ids[0], 'retmode': 'json'})
    s = (summary.get('result') or {}).get(ids[0]) or {}
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


@st.cache_data(ttl=3600, show_spinner=False)
def get_uniprot_accession(symbol: str) -> Optional[str]:
    data = get_json(f'{UNIPROT}/uniprotkb/search', {
        'query': f'(gene_exact:{symbol}) AND (organism_id:9606) AND (reviewed:true)',
        'format': 'json', 'size': 1,
    })
    results = data.get('results', [])
    if not results:
        return None
    return results[0].get('primaryAccession')


@st.cache_data(ttl=3600, show_spinner=False)
def get_alphafold_metadata(accession: str) -> Optional[dict]:
    url = f'https://alphafold.ebi.ac.uk/api/prediction/{accession}'
    try:
        data = get_json(url)
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


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
        gc = x.get('germline_classification') or {}
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


def gdc_gene_exploration_url(project: str, symbol: str) -> str:
    filters = {
        'op': 'and',
        'content': [
            {'op': 'in', 'content': {'field': 'cases.project.project_id', 'value': [project]}},
            {'op': 'in', 'content': {'field': 'genes.symbol', 'value': [symbol]}},
        ],
    }
    return 'https://portal.gdc.cancer.gov/exploration?filters=' + quote(json.dumps(filters))


def references(gene: str):
    a, b, c = st.columns(3)
    a.link_button('NCBI Gene', f'https://www.ncbi.nlm.nih.gov/gene/?term={quote(gene)}')
    b.link_button('UniProt', f'https://www.uniprot.org/uniprotkb?query={quote(gene)}')
    c.link_button('ClinVar', f'https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(gene)}[gene]')


# --------------------------------------------------------------------------
# UI Header & Sidebar Navigation
# --------------------------------------------------------------------------
st.markdown(
    '<h1 style="text-align:center">🧬 Gene-SphereAI</h1>'
    '<p style="text-align:center;color:gray">Hybrid Gene Intelligence Platform · Evidence first, AI assisted</p>',
    unsafe_allow_html=True,
)
st.caption('Student bioinformatics prototype · Public data may change · Not a diagnostic tool')

with st.sidebar:
    st.header('🧭 Navigation')
    app_view = st.radio('Go to', ['🏠 Portal Home', '🧬 Gene & Cancer Explorer'])
    
    st.markdown('---')
    st.header('⚙️ Analysis settings')
    mode = st.radio('Mode', ['Offline / demo', 'Online / live data'])
    gene = st.selectbox('Choose gene', list(GENE_DB.keys()), index=1)
    project = st.selectbox('TCGA project', ['TCGA-BRCA', 'TCGA-LUAD', 'TCGA-LUSC', 'TCGA-COAD', 'TCGA-GBM', 'TCGA-OV', 'TCGA-PRAD'])
    st.caption('Online mode uses public NCBI, UniProt and GDC endpoints.')

facts = GENE_DB[gene]


# --------------------------------------------------------------------------
# Portal Landing Page
# --------------------------------------------------------------------------
def render_landing_page():
    st.markdown("<h2 style='text-align: center;'>Welcome to Gene-SphereAI Portal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>A Hybrid Multi-Omics & Protein Structure Intelligence Platform</p>", unsafe_allow_html=True)
    st.markdown('---')

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Curated Genes", len(GENE_DB))
    c2.metric("Integrated APIs", "NCBI, UniProt, GDC, AlphaFold")
    c3.metric("TCGA Cohorts", "7 Cancer Types")
    c4.metric("Architecture", "Fault-Isolated Modular Tabs")

    st.markdown("### 🔍 About the Platform")
    st.write(
        "**Gene-SphereAI** bridges genomic metadata, clinical variant classifications, transcriptomic profiling "
        "from the Genomic Data Commons (GDC), and 3D protein structural models into a single interface. "
        "Designed for evidence-first exploration with strict error boundaries."
    )

    st.markdown("### 🚀 Core Modules")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.markdown("#### 🧬 Overview & Protein Explorer")
        st.write("Retrieve official NCBI/UniProt records alongside AlphaFold structural models, sequence metrics, and PAE confidence plots.")
    with col_b:
        st.markdown("#### 📊 Multi-Omics & Variants")
        st.write("Explore ClinVar germline clinical significance tables and GDC TCGA open-access transcriptome/methylation file distributions.")
    with col_c:
        st.markdown("#### 🤖 AI Assistant")
        st.write("Leverage a Gemini-powered teaching assistant configured to explain biological context strictly using verified records.")

    st.markdown('---')
    st.info("👉 Use the sidebar **Navigation** menu to switch to **Gene & Cancer Explorer** and begin analyzing specific genes.")


# --------------------------------------------------------------------------
# Tab Renderers
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
            if n and n.get('found'):
                st.success(f"NCBI Gene ID: {n['id']}")
                st.write(n.get('summary') or n.get('description') or 'No description provided.')
                st.link_button('View NCBI record', n['url'])
            if u and u.get('found'):
                st.write('**UniProt accession:**', u['accession'])
                st.write('**Protein:**', u['protein_name'] or 'Not provided')
                st.write('**Length:**', u['length'] or 'Not provided')
                st.link_button('View UniProt record', u['url'])
            if not n and not u:
                st.info('Click the button to retrieve current records.')
        else:
            st.info('Offline mode uses curated local examples. Switch to Online mode for live public records.')
    references(gene)


def render_mutations():
    st.subheader('Mutation and clinical-variant explorer')
    st.warning('Clinical classifications are evidence summaries, not personal risk predictions.')
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
        if isinstance(df, pd.DataFrame) and not df.empty:
            render_link_table(df)
        elif isinstance(df, pd.DataFrame):
            st.info('No records returned for this query.')
    else:
        st.info('Switch to Online mode to query ClinVar.')
    references(gene)


def render_expression():
    st.subheader(f'TCGA gene expression: {gene} in {project}')
    st.markdown('#### 🔗 Direct GDC Portal Integration')
    st.link_button(f'Explore {gene} expression in {project} on GDC Portal', gdc_gene_exploration_url(project, gene))
    st.markdown('---')
    st.subheader('Project Transcriptome Files (STAR - Counts)')

    if mode == 'Online / live data':
        if st.button('Check GDC expression data availability'):
            with st.spinner(f'Checking {project}…'):
                try:
                    st.session_state[f'expr_{project}'] = gdc_catalog(project, 'Transcriptome Profiling')
                except Exception as e:
                    st.session_state[f'expr_{project}'] = None
                    st.error(f'GDC query failed: {describe_error(e)}')

        df = st.session_state.get(f'expr_{project}')
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.metric('Files returned', len(df))
            if 'Sample type' in df.columns:
                sample_counts = df['Sample type'].value_counts().reset_index()
                sample_counts.columns = ['Sample Type', 'Count']
                fig = px.bar(sample_counts, x='Sample Type', y='Count', title=f'Sample Type Distribution in {project}')
                st.plotly_chart(fig, use_container_width=True)
            render_link_table(df)
        elif isinstance(df, pd.DataFrame):
            st.info('No matching files returned.')
    else:
        st.info('Online mode is required to check GDC.')
    references(gene)


def render_methylation():
    st.subheader('TCGA DNA methylation')
    if mode == 'Online / live data':
        if st.button('Check GDC methylation data availability'):
            with st.spinner(f'Checking methylation files for {project}…'):
                try:
                    st.session_state[f'meth_{project}'] = gdc_catalog(project, 'DNA Methylation')
                except Exception as e:
                    st.session_state[f'meth_{project}'] = None
                    st.error(f'GDC query failed: {describe_error(e)}')
        df = st.session_state.get(f'meth_{project}')
        if isinstance(df, pd.DataFrame) and not df.empty:
            st.metric('Files returned', len(df))
            render_link_table(df)
        elif isinstance(df, pd.DataFrame):
            st.info('No matching open-access files returned.')
    else:
        st.info('Online mode is required to check GDC.')
    references(gene)


def render_protein_structure(selected_gene: str):
    st.subheader('Protein Structure Explorer')
    st.write('Explore structural metadata, confidence metrics, and alignment graphics retrieved directly from AlphaFold and UniProt.')

    if st.button('Retrieve Protein Structure', key='btn_protein_struct'):
        with st.spinner('Fetching structural metadata and metrics...'):
            accession = get_uniprot_accession(selected_gene)
            if not accession:
                st.warning('No reviewed UniProt protein record found for this gene.')
                return

            uni_data = uniprot_gene(selected_gene)
            af_data = get_alphafold_metadata(accession)

            st.success(f'**UniProt Accession:** {accession}')

            col1, col2, col3 = st.columns(3)
            pname = uni_data.get('protein_name', 'N/A')
            if len(pname) > 25:
                pname = pname[:22] + '...'
            col1.metric('Protein Name', pname)
            col2.metric('Sequence Length', f"{uni_data.get('length', 'N/A')} aa")
            
            if af_data:
                col3.metric('AlphaFold Version', af_data.get('alphafoldVersion', 'N/A'))
            else:
                col3.metric('AlphaFold Model', 'Available')

            st.markdown('---')
            st.markdown('### 🧬 Structural Features & Confidence')

            if af_data:
                st.write(f'**Organism:** {af_data.get("organismScientificName", "Homo sapiens")} (TaxID: {af_data.get("taxId", "9606")})')
                st.write(f'**Gene Symbol:** {af_data.get("gene", selected_gene)}')
                
                pae_url = af_data.get('paeImageUrl')
                if pae_url:
                    st.markdown('#### Predicted Aligned Error (PAE) Plot')
                    st.image(pae_url, caption='AlphaFold PAE graph indicating domain packing confidence.', use_container_width=True)
                
                bc = af_data.get('globalMetricValue')
                if bc:
                    st.metric('Mean pLDDT Confidence Score', f'{float(bc) * 100:.1f}%')
            else:
                st.info('Detailed structural metrics are loading via external records.')

            with st.expander('External Database Files & Links'):
                st.link_button('Open AlphaFold 3D Structure Entry', f'https://alphafold.ebi.ac.uk/entry/{accession}')
                st.link_button('Open UniProt Protein Record', f'https://www.uniprot.org/uniprotkb/{accession}')
                st.link_button('Download PDB Model File', f'https://alphafold.ebi.ac.uk/files/AF-{accession}-F1-model_v4.pdb')


def render_treatments():
    st.subheader('Disease treatment and application information')
    st.warning('Educational research only. Treatment depends on diagnosis, disease stage, exact variant, and clinical judgement.')
    st.markdown(f'- [NCI cancer information search for {gene}](https://www.cancer.gov/search/results?swKeyword={quote(gene)})')
    st.markdown(f'- [ClinicalTrials.gov studies involving {gene}](https://clinicaltrials.gov/search?term={quote(gene)})')
    st.markdown(f'- [ClinVar variant interpretations for {gene}](https://www.ncbi.nlm.nih.gov/clinvar/?term={quote(gene)}[gene])')


def render_ai():
    st.subheader('AI Explanation Assistant')
    st.info('Ask contextual questions about the selected gene.')


# --------------------------------------------------------------------------
# Main Execution Logic
# --------------------------------------------------------------------------
if app_view == '🏠 Portal Home':
    render_landing_page()
else:
    tabs = st.tabs(['Overview', 'Mutations', 'Gene expression', 'DNA methylation', 'Protein structure', 'Treatments', 'AI explanation'])

    with tabs[0]:
        safe_section(render_overview, 'Overview tab')

    with tabs[1]:
        safe_section(render_mutations, 'Mutations tab')

    with tabs[2]:
        safe_section(render_expression, 'Gene expression tab')

    with tabs[3]:
        safe_section(render_methylation, 'DNA methylation tab')

    with tabs[4]:
        safe_section(lambda: render_protein_structure(gene), 'Protein structure tab')

    with tabs[5]:
        safe_section(render_treatments, 'Treatments tab')

    with tabs[6]:
        safe_section(render_ai, 'AI explanation tab')
