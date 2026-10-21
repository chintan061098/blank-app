import os, json
from typing import Optional
import pandas as pd
import requests
import streamlit as st
import plotly.express as px

st.set_page_config(page_title='ShubhgeneAI', page_icon='🧬', layout='wide')
TIMEOUT = 25
NCBI = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils'
GDC = 'https://api.gdc.cancer.gov'
UNIPROT = 'https://rest.uniprot.org'

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

def get_json(url, params=None):
    r=requests.get(url, params=params, timeout=TIMEOUT); r.raise_for_status(); return r.json()

@st.cache_data(ttl=3600, show_spinner=False)
def ncbi_gene(symbol):
    data=get_json(f'{NCBI}/esearch.fcgi', {'db':'gene','term':f'{symbol}[Gene Name] AND Homo sapiens[Organism]','retmode':'json','retmax':5})
    ids=data.get('esearchresult',{}).get('idlist',[])
    if not ids: return {'found':False,'message':'No human NCBI Gene record found.'}
    s=get_json(f'{NCBI}/esummary.fcgi', {'db':'gene','id':ids[0],'retmode':'json'}).get('result',{}).get(ids[0],{})
    return {'found':True,'id':ids[0],'name':s.get('name',symbol),'description':s.get('description',''),'summary':s.get('summary',''),'map':s.get('maplocation',''),'url':f'https://www.ncbi.nlm.nih.gov/gene/{ids[0]}'}

@st.cache_data(ttl=3600, show_spinner=False)
def uniprot_gene(symbol):
    data=get_json(f'{UNIPROT}/uniprotkb/search', {'query':f'(gene_exact:{symbol}) AND (organism_id:9606) AND (reviewed:true)','format':'json','size':1,'fields':'accession,protein_name,gene_names,length,mass'})
    hits=data.get('results',[])
    if not hits: return {'found':False,'message':'No reviewed human UniProt record returned.'}
    x=hits[0]; pdsc=x.get('proteinDescription',{}); pname=pdsc.get('recommendedName',{}).get('fullName',{}).get('value','')
    return {'found':True,'accession':x.get('primaryAccession',''),'protein_name':pname,'length':x.get('sequence',{}).get('length'),'url':f"https://www.uniprot.org/uniprotkb/{x.get('primaryAccession','')}"}

@st.cache_data(ttl=1800, show_spinner=False)
def clinvar_search(symbol, limit=25):
    data=get_json(f'{NCBI}/esearch.fcgi', {'db':'clinvar','term':f'{symbol}[gene] AND human[orgn]','retmode':'json','retmax':limit,'sort':'relevance'})
    ids=data.get('esearchresult',{}).get('idlist',[])
    if not ids: return pd.DataFrame()
    result=get_json(f'{NCBI}/esummary.fcgi', {'db':'clinvar','id':','.join(ids),'retmode':'json'}).get('result',{})
    rows=[]
    for uid in ids:
        x=result.get(uid,{})
        if not isinstance(x,dict): continue
        gc=x.get('germline_classification') or {}
        rows.append({'ClinVar ID':uid,'Variant / condition':x.get('title',''),'Clinical significance':gc.get('description','Not stated'),'Review status':gc.get('review_status','Not stated'),'Last evaluated':gc.get('last_evaluated',''),'Source':f'https://www.ncbi.nlm.nih.gov/clinvar/variation/{uid}/'})
    return pd.DataFrame(rows)

def gdc_catalog(project, category, limit=100):
    content=[{'op':'in','content':{'field':'cases.project.project_id','value':[project]}},{'op':'in','content':{'field':'data_category','value':[category]}},{'op':'in','content':{'field':'access','value':['open']}}]
    if category=='Transcriptome Profiling':
        content += [{'op':'in','content':{'field':'data_type','value':['Gene Expression Quantification']}},{'op':'in','content':{'field':'analysis.workflow_type','value':['STAR - Counts']}}]
    filters={'op':'and','content':content}
    fields='file_id,file_name,data_type,data_format,file_size,cases.submitter_id,cases.project.project_id,cases.samples.sample_type'
    data=get_json(f'{GDC}/files', {'filters':json.dumps(filters),'fields':fields,'format':'JSON','size':limit})
    rows=[]
    for x in data.get('data',{}).get('hits',[]):
        cases=x.get('cases') or [{}]; case=cases[0]; samples=case.get('samples') or [{}]
        rows.append({'File':x.get('file_name',''),'Data type':x.get('data_type',''),'Format':x.get('data_format',''),'Sample':case.get('submitter_id',''),'Sample type':samples[0].get('sample_type','') if samples else '', 'Size (MB)':round((x.get('file_size') or 0)/1e6,2),'Source':f"https://portal.gdc.cancer.gov/files/{x.get('file_id','')}"})
    return pd.DataFrame(rows)

def gemini_explain(symbol, facts, question):
    try:
        key = st.secrets.get('GEMINI_API_KEY', '')
    except Exception:
        key = ''
    key = key or os.getenv('GEMINI_API_KEY', '')
    if not key: raise RuntimeError('Gemini key missing. Add GEMINI_API_KEY in Streamlit Secrets or environment variables.')
    prompt=f'''You are a cautious bioinformatics teaching assistant. Explain only the supplied information; do not invent variants, measurements, treatments or citations. State uncertainty. Educational use only, not diagnosis or medical advice. Gene: {symbol}. Curated facts: {facts}. Student question: {question}. Use headings: Explanation, Biological context, Limitations, Sources to verify.'''
    r=requests.post('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent',params={'key':key},json={'contents':[{'parts':[{'text':prompt}]}]},timeout=TIMEOUT)
    r.raise_for_status(); data=r.json()
    try: return data['candidates'][0]['content']['parts'][0]['text']
    except (KeyError,IndexError,TypeError): raise RuntimeError('Gemini returned an unexpected response. Check key, quota and model access.')

def references(gene):
    a,b,c=st.columns(3)
    a.link_button('NCBI Gene',f'https://www.ncbi.nlm.nih.gov/gene/?term={gene}')
    b.link_button('UniProt',f'https://www.uniprot.org/uniprotkb?query={gene}')
    c.link_button('ClinVar',f'https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene]')

st.markdown('<h1 style="text-align:center">🧬 ShubhgeneAI</h1><p style="text-align:center;color:gray">Hybrid Gene Intelligence Platform · Evidence first, AI assisted</p>',unsafe_allow_html=True)
st.caption('Student bioinformatics prototype · Public data may change · Not a diagnostic tool')
with st.sidebar:
    st.header('⚙️ Analysis settings')
    mode=st.radio('Mode',['Offline / demo','Online / live data'])
    gene=st.selectbox('Choose gene',list(GENE_DB.keys()),index=1)
    project=st.selectbox('TCGA project',['TCGA-BRCA','TCGA-LUAD','TCGA-LUSC','TCGA-COAD','TCGA-GBM','TCGA-OV','TCGA-PRAD'])
    st.caption('Online mode uses public NCBI, UniProt and GDC endpoints. Gemini explanations require GEMINI_API_KEY.')
facts=GENE_DB[gene]
tabs=st.tabs(['Overview','Mutations','Gene expression','DNA methylation','Treatments','AI explanation'])

with tabs[0]:
    st.subheader(f'{gene} — gene and protein overview'); st.write(facts['function'])
    c1,c2,c3,c4=st.columns(4); c1.metric('Gene type',facts['type']); c2.metric('Protein length',f"{facts['length']:,} aa"); c3.metric('Approx. mass',f"{facts['mass']} kDa" if facts['mass'] else 'Not available'); c4.metric('Chromosome',facts['chromosome'])
    left,right=st.columns(2)
    with left:
        st.markdown('#### Curated educational summary'); st.write('**Full name:**',facts['full_name']); st.write('**Pathway / process:**',facts['pathway']); st.write('**Disease context:**',facts['disease'])
        st.plotly_chart(px.bar(pd.DataFrame({'Measure':['Protein length (aa)'],'Value':[facts['length']]}),x='Measure',y='Value',title='Reference protein length'),use_container_width=True)
    with right:
        st.markdown('#### Live database records')
        if mode=='Online / live data':
            if st.button('Retrieve NCBI + UniProt records'):
                try:
                    with st.spinner('Retrieving records…'):
                        st.session_state[f'ncbi_{gene}']=ncbi_gene(gene); st.session_state[f'uni_{gene}']=uniprot_gene(gene)
                except Exception as e: st.error(f'Retrieval failed: {e}')
            n=st.session_state.get(f'ncbi_{gene}'); u=st.session_state.get(f'uni_{gene}')
            if n:
                if n.get('found'): st.success(f"NCBI Gene ID: {n['id']}"); st.write(n.get('summary') or n.get('description')); st.link_button('View NCBI record',n['url'])
                else: st.info(n['message'])
            if u:
                if u.get('found'): st.write('**UniProt accession:**',u['accession']); st.write('**Protein:**',u['protein_name']); st.write('**Length:**',u['length']); st.link_button('View UniProt record',u['url'])
                else: st.info(u['message'])
            if not n and not u: st.info('Click the button to retrieve current records.')
        else: st.info('Offline mode uses curated local examples. Switch to Online mode for live public records.')
    references(gene)

with tabs[1]:
    st.subheader('Mutation and clinical-variant explorer'); st.warning('A gene symbol alone does not identify a person’s variant. Clinical classifications are evidence summaries, not personal risk predictions.')
    if mode=='Online / live data':
        limit=st.slider('Maximum ClinVar records',10,100,25,5)
        if st.button('Retrieve ClinVar variants'):
            try:
                with st.spinner('Searching ClinVar…'): st.session_state[f'clinvar_{gene}']=clinvar_search(gene,limit)
            except Exception as e: st.error(f'ClinVar query failed: {e}')
        df=st.session_state.get(f'clinvar_{gene}')
        if isinstance(df,pd.DataFrame):
            if df.empty: st.info('No records returned for this query.')
            else:
                st.dataframe(df.drop(columns=['Source']),use_container_width=True,hide_index=True)
                st.dataframe(df[['Variant / condition','Source']],use_container_width=True,hide_index=True)
    else: st.info('Offline mode does not simulate mutation effects. Switch to Online mode to query ClinVar.')
    references(gene)

def gdc_gene_exploration_url(project, symbol):
    # Generates a direct GDC portal search URL filtered by project and gene
    return f"https://portal.gdc.cancer.gov/exploration?filters=%7B%22op%22%3A%22and%22%2C%22content%22%3A%5B%7B%22op%22%3A%22in%22%2C%22content%22%3A%7B%22field%22%3A%22cases.project.project_id%22%2C%22value%22%3A%5B%22{project}%22%5D%7D%7D%2C%7B%22op%22%3A%22in%22%2C%22content%22%3A%7B%22field%22%3A%22genes.symbol%22%2C%22value%22%3A%5B%22{symbol}%22%5D%7D%7D%5D%7D"

# --- Inside Tab 2 ---
with tabs[2]:
    st.subheader(f'TCGA gene expression: {gene} in {project}')
    st.write(f'Explore open-access GDC RNA-seq files and transcriptome profiling data for **{gene}** within the **{project}** cohort.')
    
    st.markdown('#### 🔗 Direct GDC Portal Integration')
    st.link_button(f'Explore {gene} expression in {project} on GDC Portal', gdc_gene_exploration_url(project, gene))
    
    st.markdown('---')
    st.subheader('Project Transcriptome Files (STAR - Counts)')
    st.info('This version discovers STAR count files and visualizes sample type distributions for the selected project.')
    
    if mode == 'Online / live data':
        if st.button('Check GDC expression data availability'):
            try:
                with st.spinner(f'Checking {project}…'): 
                    st.session_state[f'expr_{project}'] = gdc_catalog(project, 'Transcriptome Profiling')
            except Exception as e: 
                st.error(f'GDC query failed: {e}')
                
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
                
                # Render native interactive dataframe with clickable LinkColumn
                st.dataframe(
                    df,
                    column_config={
                        "Source": st.column_config.LinkColumn(
                            "Source Link",
                            help="Click to open file in GDC portal",
                            display_text="🔗 Open File"
                        )
                    },
                    use_container_width=True,
                    hide_index=True
                )
    else: 
        st.info('Online mode is required to check GDC. Offline mode does not invent expression measurements.')
    references(gene)
# with tabs[2]:
#     st.subheader('TCGA gene expression'); st.write('Discover open-access GDC RNA-seq files for the selected project.')
#     st.info('This version discovers STAR count files; it does not yet download, aggregate and statistically compare gene-level expression measurements.')
#     if mode=='Online / live data':
#         if st.button('Check GDC expression data availability'):
#             try:
#                 with st.spinner(f'Checking {project}…'): st.session_state[f'expr_{project}']=gdc_catalog(project,'Transcriptome Profiling')
#             except Exception as e: st.error(f'GDC query failed: {e}')
#         df=st.session_state.get(f'expr_{project}')
#         if isinstance(df,pd.DataFrame):
#             st.metric('Files returned',len(df))
#             if df.empty: st.info('No matching files returned. Try another project.')
#             else: st.dataframe(df.drop(columns=['Source']),use_container_width=True,hide_index=True); st.dataframe(df[['File','Source']],use_container_width=True,hide_index=True)
#     else: st.info('Online mode is required to check GDC. Offline mode does not invent expression measurements.')

with tabs[3]:
    st.subheader('TCGA DNA methylation'); st.write('First discover public methylation files for a cancer project.')
    st.warning('This version does not yet calculate CpG beta values, annotate probes, match methylation to expression samples, or compute correlations.')
    if mode=='Online / live data':
        if st.button('Check GDC methylation data availability'):
            try:
                with st.spinner(f'Checking methylation files for {project}…'): st.session_state[f'meth_{project}']=gdc_catalog(project,'DNA Methylation')
            except Exception as e: st.error(f'GDC query failed: {e}')
        df=st.session_state.get(f'meth_{project}')
        if isinstance(df,pd.DataFrame):
            st.metric('Files returned',len(df))
            if df.empty: st.info('No matching open-access files returned.')
            else: st.dataframe(df.drop(columns=['Source']),use_container_width=True,hide_index=True); st.dataframe(df[['File','Source']],use_container_width=True,hide_index=True)
    else: st.info('Online mode is required to check GDC. No methylation values are fabricated in offline mode.')

with tabs[4]:
    st.subheader('Disease treatment and application information')
    st.warning('Educational research only. Treatment depends on diagnosis, disease stage, exact variant, current guidelines and clinical judgement.')
    st.write('This version supplies reliable starting points rather than inferring a treatment from a gene alone.')
    st.markdown(f'- [NCI cancer information search for {gene}](https://www.cancer.gov/search/results?swKeyword={gene})')
    st.markdown(f'- [ClinicalTrials.gov studies involving {gene}](https://clinicaltrials.gov/search?term={gene})')
    st.markdown(f'- [ClinVar variant interpretations for {gene}](https://www.ncbi.nlm.nih.gov/clinvar/?term={gene}[gene])')
    st.markdown(f'- [NCBI Gene background for {gene}](https://www.ncbi.nlm.nih.gov/gene/?term={gene})')
    st.caption('Structured treatment evidence, approval status and guideline dates are a future implementation step. These links are not treatment recommendations.')

with tabs[5]:
    st.subheader('Gemini-assisted explanation'); st.write('Gemini explains supplied information; it is not the source of scientific facts or clinical classifications.')
    question=st.text_area('What would you like explained?',f'Explain the biological role of {gene} for a microbiology student.')
    if st.button('Generate explanation with Gemini'):
        try:
            with st.spinner('Preparing explanation…'): answer=gemini_explain(gene,facts,question)
            st.markdown(answer); st.caption('AI-generated explanation. Verify scientific details against linked source records.')
        except requests.HTTPError as e: st.error(f'Gemini request failed. Check API key, quota and model access. Details: {e}')
        except Exception as e: st.error(str(e))
    references(gene)

st.markdown('---')
st.markdown('<div style="text-align:center;color:gray;font-size:.85rem">ShubhgeneAI · Evidence first, AI assisted · Not for diagnosis or treatment decisions</div>',unsafe_allow_html=True)
