# Carrega a oferta das disciplinas oferecidas pelo DEES entre 2012/2 a 2025/1.
# Streamlit version of dashlit.py

import pandas as pd
import plotly.express as px
import streamlit as st
import glob

# Configuração da página
st.set_page_config(
    page_title="Dashboard DEES",
    page_icon="📊",
    layout="wide"
)

# Cache para carregar dados apenas uma vez
@st.cache_data
def load_data():
    """Carrega e processa os dados"""
    # passo 1 - importar dados
    encargos = pd.read_csv('cursosConsolidados_20251.csv', sep=';', encoding='cp1252')
    
    # inicio das "estatísticas"
    semestres = encargos['semestre'].unique()
    professores = encargos.sort_values(by='professor')['professor'].unique()
    professores.sort()
    cursos_ofertados = encargos['curso'].unique()
    cursos_ofertados.sort()

    encargos['disciplina'] = encargos.apply(lambda row: row.codigo + ": " + row.nome, axis=1)
    disciplinas = pd.DataFrame(encargos.drop(columns=['semestre', 'professor', 'codigo', 'nome', 'ch', 'ch_prof', 'turma', 'vagas', 'ocupacao']))
    disciplinas = disciplinas.query("curso != 'PROPEES'")
    disciplinas.reset_index()
    disciplinas.sort_values(by='disciplina', inplace=True)
    
    return encargos, semestres, professores, cursos_ofertados, disciplinas

@st.cache_data
def calculate_general_stats(encargos, semestres):
    """Calcula estatísticas gerais de encargos"""
    df = pd.DataFrame(columns=['semestre', 'numprf', 'numsub', 'numvol', 'numvis', 'cdsm', 'chg', 'chp', 'docente', 'docentepos'])
    
    for sem in semestres:
        cdsm = encargos[encargos['semestre'] == sem]
        somacht = cdsm['ch_prof'].sum()
        numprof = cdsm['professor'].nunique()
        numprf = cdsm.loc[cdsm['vinculo'] == 'PRF', 'professor'].nunique()
        numsub = cdsm.loc[cdsm['vinculo'] == 'SUB', 'professor'].nunique()
        numvol = cdsm.loc[cdsm['vinculo'] == 'VOL', 'professor'].nunique()
        numvis = cdsm.loc[cdsm['vinculo'] == 'VIS', 'professor'].nunique()
        
        cdsmdees = somacht / 15 / (numprf + numsub) if (numprf + numsub) > 0 else 0
        somachp = cdsm.loc[cdsm['curso'] == 'PROPEES', 'ch_prof'].sum()
        somachg = somacht - somachp
        chg = somachg / somacht if somacht > 0 else 0
        chp = somachp / somacht if somacht > 0 else 0
        df.loc[len(df.index)] = [sem, numprf, numsub, numvol, numvis, cdsmdees, chg, chp, 0.0, 0.0]
    
    return df

@st.cache_data
def calculate_occupation_stats(encargos, semestres):
    """Calcula estatísticas de ocupação das disciplinas"""
    df2 = pd.DataFrame(columns=['semestre', 'disciplina', 'curso', 'vagas', 'ocupacao'])
    
    for sem in semestres:
        disciplinas_sem = encargos[encargos['semestre'] == sem]
        cursos = disciplinas_sem[disciplinas_sem['curso'] != 'PROPEES']['curso'].unique()
        for cur in cursos:
            disciplina_curso = disciplinas_sem[disciplinas_sem['curso'] == cur]
            disciplina_codigos = disciplina_curso['codigo'].unique()
            for cod in disciplina_codigos:
                somaocupa = disciplina_curso.loc[disciplina_curso['codigo'] == cod, 'ocupacao'].sum()
                somavagas = disciplina_curso.loc[disciplina_curso['codigo'] == cod, 'vagas'].sum()
                d = disciplina_curso.loc[disciplina_curso['codigo'] == cod]['disciplina'].unique().tolist()[0]
                df2.loc[len(df2.index)] = [sem, d, cur, somavagas, somaocupa]
    
    return df2

def create_chsm_graph(encargos, df, semestres, professor):
    """Cria o gráfico de CHSM para um professor específico"""
    df_copy = df.copy()
    
    for sem in semestres:
        cdsm = encargos[encargos['semestre'] == sem]
        somadocente = float((cdsm.loc[cdsm['professor'] == professor, 'ch_prof'].sum())/15.0)
        cdsmpos = cdsm[cdsm['curso'] == 'PROPEES']
        somadocentepos = float((cdsmpos.loc[cdsmpos['professor'] == professor, 'ch_prof'].sum())/15.0)
        idx = df_copy.index.get_loc(df_copy[df_copy['semestre'] == sem].index[0])
        df_copy.loc[idx, ['docente', 'docentepos']] = [somadocente, somadocentepos]

    fig = px.line(df_copy, x='semestre', y=['cdsm', 'docente', 'docentepos'])
    fig.update_layout(legend_title_text='CHSM')
    fig.update_traces({'name': 'CH DEES'}, selector={'name': 'cdsm'})
    fig.update_traces({'name': 'CH TOTAL'}, selector={'name': 'docente'})
    fig.update_traces({'name': 'CH PROPEES'}, selector={'name': 'docentepos'})
    fig.update_xaxes(zeroline=True)
    fig.update_yaxes(zeroline=True, range=[0,20])
    
    return fig

def create_occupation_graph(df2, curso, disciplina):
    """Cria o gráfico de ocupação para uma disciplina específica"""
    dfc = df2[df2['curso'] == curso]
    df3 = dfc[dfc['disciplina'] == disciplina]
    
    fig = px.line(df3, x='semestre', y=['vagas', 'ocupacao'], title=disciplina)
    fig.update_layout(legend_title_text='Ocupação')
    fig.update_traces({'name': 'vagas'}, selector={'name': 'vagas'})
    fig.update_traces({'name': 'ocupação'}, selector={'name': 'ocupacao'})
    fig.update_xaxes(zeroline=True)
    fig.update_yaxes(zeroline=True, range=[0,200])
    
    return fig

def main():
    # Título principal
    st.title("📊 Dashboard DEES - Análise de Encargos e Ocupação")
    
    # Carrega os dados
    try:
        encargos, semestres, professores, cursos_ofertados, disciplinas = load_data()
        df = calculate_general_stats(encargos, semestres)
        df2 = calculate_occupation_stats(encargos, semestres)
    except FileNotFoundError:
        st.error("❌ Arquivo 'cursosConsolidados_20251.csv' não encontrado!")
        st.stop()
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados: {str(e)}")
        st.stop()
    
    # Tabs principais
    tab1, tab2 = st.tabs(["📈 CHSM", "📊 Ocupação"])
    
    with tab1:
        st.header("Histórico da CHSM")
        
        # Seletor de professor
        professor_selected = st.selectbox(
            "Selecione um professor:",
            professores,
            index=0,
            key="professor_selector"
        )
        
        # Gráfico CHSM
        if professor_selected:
            fig_chsm = create_chsm_graph(encargos, df, semestres, professor_selected)
            st.plotly_chart(fig_chsm, use_container_width=True)
            
            # Informações adicionais
            with st.expander("ℹ️ Informações sobre CHSM"):
                st.write("""
                - **CH DEES**: Carga horária total do departamento
                - **CH TOTAL**: Carga horária total do professor selecionado
                - **CH PROPEES**: Carga horária do professor em disciplinas de pós-graduação
                """)
    
    with tab2:
        st.header("Análise de Ocupação das Disciplinas")
        
        # Layout em colunas para os seletores
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Cursos")
            curso_selected = st.selectbox(
                "Selecione um curso:",
                cursos_ofertados,
                index=0,
                key="curso_selector"
            )
        
        with col2:
            st.subheader("Disciplinas")
            # Filtra disciplinas pelo curso selecionado
            disciplinas_do_curso = disciplinas[disciplinas['curso'] == curso_selected]['disciplina'].unique()
            
            if len(disciplinas_do_curso) > 0:
                disciplina_selected = st.selectbox(
                    "Selecione uma disciplina:",
                    disciplinas_do_curso,
                    index=0,
                    key="disciplina_selector"
                )
            else:
                st.warning("Nenhuma disciplina encontrada para este curso.")
                disciplina_selected = None
        
        # Gráfico de ocupação
        if curso_selected and disciplina_selected:
            fig_ocupacao = create_occupation_graph(df2, curso_selected, disciplina_selected)
            st.plotly_chart(fig_ocupacao, use_container_width=True)
            
            # Estatísticas da disciplina
            dfc = df2[df2['curso'] == curso_selected]
            df3 = dfc[dfc['disciplina'] == disciplina_selected]
            
            if not df3.empty:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Média de Vagas", f"{df3['vagas'].mean():.1f}")
                
                with col2:
                    st.metric("Média de Ocupação", f"{df3['ocupacao'].mean():.1f}")
                
                with col3:
                    taxa_ocupacao = (df3['ocupacao'].mean() / df3['vagas'].mean() * 100) if df3['vagas'].mean() > 0 else 0
                    st.metric("Taxa de Ocupação", f"{taxa_ocupacao:.1f}%")
                
                with col4:
                    st.metric("Períodos Analisados", len(df3))
    
    # Sidebar com informações gerais
    with st.sidebar:
        st.header("📊 Estatísticas Gerais")
        
        st.metric("Total de Professores", len(professores))
        st.metric("Total de Cursos", len(cursos_ofertados))
        st.metric("Períodos Analisados", len(semestres))
        
        st.markdown("---")
        st.markdown("**Período de Análise:**")
        st.markdown(f"De {min(semestres)} a {max(semestres)}")
        
        # Informações sobre os dados
        with st.expander("ℹ️ Sobre os Dados"):
            st.write("""
            Este dashboard apresenta análises sobre:
            - Carga horária semestral média (CHSM)
            - Ocupação das disciplinas por curso
            - Distribuição de encargos docentes
            
            Os dados são baseados na oferta de disciplinas 
            do DEES entre 2012/2 e 2025/1.
            """)

if __name__ == "__main__":
    main()
