# app.py
# Versão Streamlit com Desativação (Inativo) + Relatório CSV + Reativação
import streamlit as st
import pandas as pd
import io, zipfile, os
from datetime import datetime

st.set_page_config(page_title="Painel de Avaliação - Streamlit", layout="wide")

# ---------- Config ----------
SENHA_PADRAO = "1234"
VAGAS_POR_SALA = 6
SALAS_INFO = [(1, "Hidrossanitário"), (2, "Hidrossanitário"), (3, "Elétrica"), (4, "Elétrica")]
CLASSES = ["S", "A", "B", "C", "D"]

# Critérios (igual ao que você já conhece)
CRITERIOS = {
    "Qualidade Técnica": [
        (10, "Nenhum erro, projeto independente", "Acurácia 100%"),
        (9,  "Quase sem falhas, ainda não independente", "Acurácia >90%"),
        (8,  "Bom projeto, ajustes de organização", "Ajustes leves de organização"),
        (7,  "Bom projeto, alguns ajustes técnicos", "Ajustes técnicos solicitados"),
        (6,  "Projeto razoável, muitos comentários", "Razoável, precisa de revisão"),
        (5,  "Uso errado de materiais ou modelagem", "Erro de materiais/modelagem"),
        (4,  "Erro grave em 1 projeto", "Erro grave único"),
        (3,  "Dois ou mais erros graves", "Erros graves múltiplos")
    ],
    "Proatividade": [
        (10, "4 ou mais ações além do básico", "Proativo extremo"),
        (9,  "3 ações", "Muito proativo"),
        (8,  "2 ações", "Proativo"),
        (7,  "1 ação", "Alguma proatividade"),
        (6,  "Faz o básico e pede novas demandas", "Básico + iniciativa mínima"),
        (5,  "Fala que acabou, mas não quer novos projetos", "Pouca disposição"),
        (3,  "Nenhuma ação", "Inativo")
    ],
    "Colaboração em equipe": [
        (10, "Sempre ajuda primeiro, acompanha até resolver", "Sempre ajuda primeiro"),
        (9,  "Frequentemente ajuda primeiro e acompanha", "Ajuda frequente"),
        (8,  "Boa disposição, ajuda, mas não é o primeiro", "Disponível para ajudar"),
        (6,  "Oferece ajuda, mas pouco disposto", "Ajuda limitada"),
        (5,  "Só escuta, não se envolve", "Escuta passiva"),
        (3,  "Nunca ajuda, não se dispõe", "Não colaborativo")
    ],
    "Comunicação": [
        (10, "Clareza total, escuta ativa, escreve bem", "Comunicação perfeita"),
        (9,  "Clareza, escuta ativa, e-mails/WhatsApp ok", "Comunicação boa"),
        (7,  "Clareza, escuta ativa, mas escrita ruim", "Comunicação com falhas"),
        (6,  "Clareza média, escuta/ escrita irregular", "Comunicação média"),
        (5,  "Clareza limitada, escuta irregular", "Comunicação fraca"),
        (3,  "Não comunica claramente, não escuta", "Comunicação ruim")
    ],
    "Organização / Planejamento": [
        (10, "Muito organizado, ajuda o coordenador", "Organização exemplar"),
        (9,  "Organizado, segue procedimentos, sugere melhorias", "Organizado e propositivo"),
        (7,  "Respeita procedimentos, sem sugestão", "Organizado básico"),
        (6,  "Uma chamada de atenção", "Pouco organizado"),
        (5,  "Duas chamadas de atenção", "Desorganizado"),
        (3,  "Três ou mais chamadas", "Muito desorganizado")
    ],
    "Dedicação em estudos": [
        (10, "Anota sempre, faz cursos, aplica treinamentos, traz soluções", "Estudo constante e aplicado"),
        (9,  "Anota, faz cursos, aproveita treinamentos, às vezes traz soluções", "Estudo aplicado"),
        (7,  "Anota às vezes, raramente traz soluções", "Dedicação parcial"),
        (6,  "Anota pouco, não faz cursos, não traz soluções", "Pouca dedicação"),
        (5,  "Repete perguntas, não usa cursos", "Dedicação mínima"),
        (3,  "Repete muitas vezes, não aproveita cursos", "Sem dedicação")
    ],
    "Cumprimento de prazos": [
        (10, "Nenhum atraso", "Pontualidade total"),
        (9,  "1 atraso justificado", "Quase pontual"),
        (8,  "2 atrasos justificados", "Pontualidade razoável"),
        (7,  "3 atrasos justificados", "Atrasos frequentes"),
        (6,  "4 atrasos justificados", "Atrasos contínuos"),
        (5,  "1 atraso não justificado", "Atraso sem justificativa"),
        (4,  "2 atrasos não justificados", "Atrasos problemáticos"),
        (3,  "Mais de 2 atrasos não justificados", "Muito atrasado")
    ],
    "Engajamento com Odoo": [
        (10, "Usa todos apps, sugere melhorias, cobra colegas", "Engajamento total"),
        (9,  "Usa boa parte dos apps, abre todo dia, cobra colegas", "Engajamento alto"),
        (7,  "Usa parte dos apps, abre todo dia, não cobra colegas", "Engajamento moderado"),
        (6,  "Usa parte dos apps, abre todo dia, mas não durante todo o dia", "Uso limitado"),
        (5,  "Usa apenas parte dos apps, abre de forma irregular", "Uso mínimo"),
        (3,  "Não usa corretamente, resiste à ferramenta", "Resistência total")
    ]
}

# ---------- Helpers ----------
def pontos_por_nota(n):
    if n==10: return 3
    if n==9: return 2
    if n==8: return 1
    return 0

def init_state():
    if "df" not in st.session_state:
        rows=[]
        for sala,equipe in SALAS_INFO:
            for _ in range(VAGAS_POR_SALA):
                rows.append({"Sala":sala,"Equipe":equipe,"Classe":"-","Projetista":"-","Pontuação":0})
        st.session_state.df = pd.DataFrame(rows)
    if "historico" not in st.session_state:
        st.session_state.historico = pd.DataFrame(columns=["Timestamp","Disciplina","Demanda","Projetista","Parâmetro","Nota","Resumo","PontosAtribuídos"])
    if "inativos" not in st.session_state:
        # lista de dicts: {"Projetista":str,"Pontuação":int,"removetime":timestamp}
        st.session_state.inativos = []
    if "last_df" not in st.session_state:
        st.session_state.last_df = None
        st.session_state.last_hist = None
    if "logged" not in st.session_state:
        st.session_state.logged = False
    if "status_msg" not in st.session_state:
        st.session_state.status_msg = ""

init_state()

def salvar_snapshot():
    st.session_state.last_df = st.session_state.df.copy(deep=True)
    st.session_state.last_hist = st.session_state.historico.copy(deep=True)

def desfazer():
    if st.session_state.last_df is None and st.session_state.last_hist is None:
        st.warning("Nada para desfazer.")
        return
    st.session_state.df = st.session_state.last_df.copy(deep=True) if st.session_state.last_df is not None else st.session_state.df
    st.session_state.historico = st.session_state.last_hist.copy(deep=True) if st.session_state.last_hist is not None else st.session_state.historico
    st.session_state.last_df = None
    st.session_state.last_hist = None
    st.success("Última ação desfeita.")

def calcular_rankings():
    df = st.session_state.df
    df["RankingClasse"] = "-"
    for classe in CLASSES:
        subset = df[df["Classe"]==classe].copy()
        if subset.empty: continue
        subset_sorted = subset.sort_values("Pontuação", ascending=False)
        for rank, (idx, _) in enumerate(subset_sorted.iterrows(), start=1):
            if df.at[idx,"Pontuação"]>0:
                df.at[idx,"RankingClasse"]=rank
            else:
                df.at[idx,"RankingClasse"]="-"
    st.session_state.df = df

# ---------- UI topo ----------
st.title("Painel de Avaliação de Projetistas (Streamlit)")
st.markdown("Sistema com histórico, backup, desativação/reativação e gestão de pontuações.")

# Sidebar auth
st.sidebar.header("Acesso")
senha = st.sidebar.text_input("Senha do Coordenador", type="password")
if st.sidebar.button("Entrar"):
    if senha == SENHA_PADRAO:
        st.session_state.logged = True
        st.session_state.status_msg = ""
        st.sidebar.success("Acesso concedido")
    else:
        st.session_state.logged = False
        st.session_state.status_msg = "Senha incorreta!"
        st.sidebar.error("Senha incorreta!")

if st.session_state.status_msg:
    st.sidebar.warning(st.session_state.status_msg)

# resumo topo
def resumo_topo():
    df = st.session_state.df
    ativos = df[df["Projetista"]!="-"]
    st.markdown(f"**Projetistas ativos:** {len(ativos)} — **Vagas livres:** {len(df)-len(ativos)}  \nHidrossanitário: {len(ativos[ativos['Equipe']=='Hidrossanitário'])} | Elétrica: {len(ativos[ativos['Equipe']=='Elétrica'])}")

resumo_topo()

# ---------- Main visualizações ----------
calcular_rankings()
st.header("Visualizações")
col1,col2 = st.columns(2)
with col1:
    st.subheader("Por Sala")
    df = st.session_state.df.copy()
    for sala in sorted(df["Sala"].unique()):
        equipe = df[df["Sala"]==sala]["Equipe"].iloc[0]
        st.write(f"🏢 Sala {sala} ({equipe})")
        subset = df[df["Sala"]==sala][["Projetista","Equipe","Classe","RankingClasse","Pontuação"]].reset_index(drop=True)
        st.dataframe(subset, use_container_width=True)
with col2:
    st.subheader("Ranking por Classe (apenas Ativos)")
    df_act = st.session_state.df[st.session_state.df["Projetista"]!="-"]
    for classe in CLASSES:
        sub = df_act[df_act["Classe"]==classe].sort_values("Pontuação", ascending=False)
        if not sub.empty:
            st.write(f"**Classe {classe}**")
            st.dataframe(sub[["Projetista","Equipe","Sala","Pontuação","RankingClasse"]].reset_index(drop=True), use_container_width=True)
    st.subheader("Ranking Geral (apenas Ativos)")
    geral = df_act.sort_values("Pontuação", ascending=False).reset_index(drop=True)
    if not geral.empty:
        geral["Ranking Geral"] = geral.index + 1
        geral["Ranking Geral"] = geral.apply(lambda x: x["Ranking Geral"] if x["Pontuação"]>0 else "-", axis=1)
        st.dataframe(geral[["Ranking Geral","Projetista","Equipe","Classe","Sala","RankingClasse","Pontuação"]], use_container_width=True)
    else:
        st.info("Nenhum projetista alocado ainda.")
st.markdown("---")

# Histórico (inclui Inativos marcados)
st.subheader("Histórico de Demandas (acumulativo)")
hist = st.session_state.historico.copy()
if hist.empty:
    st.info("Nenhuma demanda registrada.")
else:
    t1,t2 = st.tabs(["Hidrossanitário","Elétrica"])
    with t1:
        hid = hist[hist["Disciplina"]=="Hidrossanitário"].sort_values("Timestamp", ascending=False).reset_index(drop=True)
        if not hid.empty:
            st.dataframe(hid, use_container_width=True)
        else:
            st.info("Nenhuma demanda Hidrossanitário.")
    with t2:
        ele = hist[hist["Disciplina"]=="Elétrica"].sort_values("Timestamp", ascending=False).reset_index(drop=True)
        if not ele.empty:
            st.dataframe(ele, use_container_width=True)
        else:
            st.info("Nenhuma demanda Elétrica.")

st.markdown("---")

# ---------- Sidebar: painel do coordenador (aparece apenas se logged) ----------
st.sidebar.header("Painel do Coordenador")
if not st.session_state.logged:
    st.sidebar.info("Faça login para gerenciar o painel.")
else:
    # Projetistas: adicionar
    st.sidebar.subheader("Projetistas")
    with st.sidebar.expander("➕ Adicionar Projetista", expanded=False):
        novo_nome = st.text_input("Nome do projetista", key="add_name")
        disciplina = st.selectbox("Disciplina", options=["Hidrossanitário","Elétrica"], key="add_disc")
        salas_op = [s for s,e in SALAS_INFO if e==disciplina]
        sala_choice = st.selectbox("Sala", options=salas_op, key="add_sala")
        classe_choice = st.selectbox("Classe", options=CLASSES, key="add_classe")
        if st.button("Adicionar"):
            if not novo_nome.strip():
                st.sidebar.warning("Informe nome válido.")
            else:
                vagas = st.session_state.df[(st.session_state.df["Sala"]==sala_choice) & (st.session_state.df["Projetista"]=="-")]
                if vagas.empty:
                    st.sidebar.error("Sala cheia.")
                else:
                    salvar_snapshot()
                    idx = vagas.index[0]
                    st.session_state.df.at[idx,"Projetista"] = novo_nome.strip()
                    st.session_state.df.at[idx,"Equipe"] = disciplina
                    st.session_state.df.at[idx,"Classe"] = classe_choice
                    st.session_state.df.at[idx,"Pontuação"] = 0
                    st.sidebar.success(f"Projetista '{novo_nome}' adicionado.")

    # Renomear
    with st.sidebar.expander("✏️ Renomear Projetista", expanded=False):
        ativos = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        sel_ren = st.selectbox("Projetista", options=ativos, key="rn_sel") if ativos else None
        novo_rn = st.text_input("Novo nome", key="rn_new")
        if st.button("Atualizar nome"):
            if not sel_ren or not novo_rn.strip():
                st.sidebar.warning("Escolha e informe novo nome.")
            else:
                salvar_snapshot()
                st.session_state.df.loc[st.session_state.df["Projetista"]==sel_ren,"Projetista"] = novo_rn.strip()
                # também atualizar histórico? mantemos histórico com nome antigo para rastreio
                st.sidebar.success("Nome atualizado no quadro (histórico preserva o registro).")

    # Alterar classe
    with st.sidebar.expander("🏷️ Alterar Classe", expanded=False):
        ativos2 = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        sel_cl = st.selectbox("Projetista", options=ativos2, key="cl_sel") if ativos2 else None
        nova_cl = st.selectbox("Nova Classe", options=CLASSES, key="cl_new")
        if st.button("Alterar classe"):
            if not sel_cl:
                st.sidebar.warning("Selecione um projetista.")
            else:
                salvar_snapshot()
                st.session_state.df.loc[st.session_state.df["Projetista"]==sel_cl,"Classe"] = nova_cl
                st.sidebar.success("Classe alterada.")

    # Remover / Inativar com relatório
    with st.sidebar.expander("🗑️ Desativar (Inativar) Projetista", expanded=False):
        ativos3 = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        sel_rem = st.selectbox("Projetista a desativar", options=ativos3, key="rem_sel") if ativos3 else None
        if sel_rem:
            st.markdown("Ao desativar, será gerado um CSV com o histórico do projetista para download. Em seguida a vaga será liberada.")
            if st.button("Gerar relatório e preparar desativação"):
                # gerar CSV do histórico do projetista
                hist_proj = st.session_state.historico[st.session_state.historico["Projetista"]==sel_rem].copy()
                # também incluir demandas onde já está marcado como Inativo (por segurança)
                hist_proj = pd.concat([hist_proj, st.session_state.historico[st.session_state.historico["Projetista"]==f"{sel_rem} (Inativo)"]]).drop_duplicates().sort_values("Timestamp", ascending=False)
                if hist_proj.empty:
                    st.sidebar.info("Sem histórico para este projetista. Ainda será possível desativar.")
                csv_bytes = hist_proj.to_csv(index=False).encode("utf-8")
                nomefile = f"historico_{sel_rem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                st.sidebar.download_button("⬇️ Baixar relatório CSV antes da desativação", data=csv_bytes, file_name=nomefile, mime="text/csv")
                st.session_state.pending_desativacao = sel_rem
                st.sidebar.info("Relatório gerado — agora confirme a desativação.")
            if st.session_state.get("pending_desativacao") == sel_rem:
                if st.button("Confirmar desativação e liberar vaga"):
                    salvar_snapshot()
                    name = st.session_state.pending_desativacao
                    # salvar info em inativos
                    idx_row = st.session_state.df[st.session_state.df["Projetista"]==name].index[0]
                    pontos = int(st.session_state.df.at[idx_row,"Pontuação"])
                    st.session_state.inativos.append({"Projetista":name,"Pontuação":pontos,"removetime":pd.Timestamp.now()})
                    # marcar historico entradas com "(Inativo)"
                    mask = st.session_state.historico["Projetista"]==name
                    st.session_state.historico.loc[mask,"Projetista"] = st.session_state.historico.loc[mask,"Projetista"].apply(lambda x: f"{x} (Inativo)")
                    # liberar vaga (apaga nome no df)
                    st.session_state.df.loc[idx_row, ["Projetista","Classe","Pontuação"]] = ["-","-",0]
                    st.session_state.pending_desativacao = None
                    st.sidebar.success(f"Projetista '{name}' desativado e vaga liberada. Histórico marcado como Inativo.")
        else:
            st.sidebar.info("Nenhum projetista ativo para desativar.")

    # Reativar
    with st.sidebar.expander("♻️ Reativar Projetista", expanded=False):
        inativos = st.session_state.inativos
        if not inativos:
            st.sidebar.info("Nenhum projetista inativo.")
        else:
            nomes_inativos = [i["Projetista"] for i in inativos]
            sel_re = st.selectbox("Selecionar inativo", options=nomes_inativos, key="react_sel")
            # choose disciplina and sala to place them
            disc_re = st.selectbox("Disciplina ao reativar", options=["Hidrossanitário","Elétrica"], key="react_disc")
            salas_op_re = [s for s,e in SALAS_INFO if e==disc_re]
            sala_re = st.selectbox("Sala", options=salas_op_re, key="react_sala")
            classe_re = st.selectbox("Classe", options=CLASSES, key="react_classe")
            if st.button("Reativar projetista"):
                # find vaga
                vagas = st.session_state.df[(st.session_state.df["Sala"]==sala_re) & (st.session_state.df["Projetista"]=="-")]
                if vagas.empty:
                    st.sidebar.error("Sala escolhida não tem vaga livre. Escolha outra sala.")
                else:
                    salvar_snapshot()
                    vaga_idx = vagas.index[0]
                    # restore pontuação from inativos list
                    entry = next((x for x in st.session_state.inativos if x["Projetista"]==sel_re), None)
                    pontos_restore = entry["Pontuação"] if entry else 0
                    st.session_state.df.at[vaga_idx,"Projetista"] = sel_re
                    st.session_state.df.at[vaga_idx,"Equipe"] = disc_re
                    st.session_state.df.at[vaga_idx,"Classe"] = classe_re
                    st.session_state.df.at[vaga_idx,"Pontuação"] = pontos_restore
                    # remove "(Inativo)" suffix from historico
                    st.session_state.historico["Projetista"] = st.session_state.historico["Projetista"].apply(lambda x: x.replace(f"{sel_re} (Inativo)", sel_re) if isinstance(x,str) else x)
                    # remove from inativos list
                    st.session_state.inativos = [x for x in st.session_state.inativos if x["Projetista"]!=sel_re]
                    st.sidebar.success(f"Projetista {sel_re} reativado na sala {sala_re} (classe {classe_re}).")

    # Gerenciar demandas (criar/validar) - mantém lógica anterior
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 Demandas (Criar / Validar)")
    with st.sidebar.form("form_dem"):
        nome_demanda = st.text_input("Nome da demanda", key="dem_name")
        disc_dem = st.selectbox("Disciplina", options=["Hidrossanitário","Elétrica"], key="dem_disc")
        ativos_para_dem = st.session_state.df[(st.session_state.df["Equipe"]==disc_dem) & (st.session_state.df["Projetista"]!="-")]["Projetista"].tolist()
        selec_proj = st.selectbox("Projetista", options=ativos_para_dem) if ativos_para_dem else None
        param = st.selectbox("Parâmetro", options=list(CRITERIOS.keys()), key="dem_param")
        crit_ops = [f"{n} - {f} -> {r}" for (n,f,r) in CRITERIOS[param]]
        crit_sel = st.selectbox("Critério", options=crit_ops, key="dem_crit")
        sub = st.form_submit_button("Validar definição de ponto")
        if sub:
            if not nome_demanda.strip() or not selec_proj or not crit_sel:
                st.sidebar.warning("Preencha tudo corretamente.")
            else:
                try:
                    nota = int(crit_sel.split(" - ")[0])
                    resumo = crit_sel.split("->")[-1].strip()
                except:
                    st.sidebar.error("Erro ao interpretar critério.")
                    st.stop()
                salvar_snapshot()
                pts = pontos_por_nota(nota)
                if pts==0:
                    st.sidebar.info("Nota <=7: registrado no histórico, sem atribuição de pontos.")
                else:
                    st.session_state.df.loc[st.session_state.df["Projetista"]==selec_proj,"Pontuação"] += pts
                    st.sidebar.success(f"{pts} ponto(s) adicionados ao {selec_proj}.")
                nova = {"Timestamp":pd.Timestamp.now(),"Disciplina":disc_dem,"Demanda":nome_demanda.strip(),"Projetista":selec_proj,"Parâmetro":param,"Nota":nota,"Resumo":resumo,"PontosAtribuídos":pts}
                st.session_state.historico = pd.concat([pd.DataFrame([nova]), st.session_state.historico], ignore_index=True)

    # Gerenciar histórico: editar/excluir (mantém lógica anterior simplificada)
    st.sidebar.markdown("---")
    st.sidebar.subheader("✏️ Gerenciar Histórico (Editar / Excluir)")
    if st.session_state.historico.empty:
        st.sidebar.info("Sem histórico.")
    else:
        max_idx = max(0,len(st.session_state.historico)-1)
        idx = st.sidebar.number_input("Índice (0 = mais recente)", min_value=0, max_value=max_idx, value=0, key="hist_idx")
        action = st.sidebar.selectbox("Ação", options=["Alterar","Excluir"], key="hist_action")
        new_param = st.sidebar.selectbox("Novo Parâmetro", options=list(CRITERIOS.keys()), key="hist_new_param")
        new_crit_ops = [f"{n} - {f} -> {r}" for (n,f,r) in CRITERIOS[new_param]]
        new_crit = st.sidebar.selectbox("Novo Critério", options=new_crit_ops, key="hist_new_crit")
        if st.sidebar.button("Confirmar ação no histórico"):
            sorted_hist = st.session_state.historico.sort_values("Timestamp", ascending=False).reset_index()
            if idx < 0 or idx >= len(sorted_hist):
                st.sidebar.error("Índice inválido.")
            else:
                actual_idx = int(sorted_hist.loc[idx,"index"])
                linha = st.session_state.historico.loc[actual_idx].to_dict()
                proj = linha["Projetista"]
                pts_old = int(linha["PontosAtribuídos"]) if pd.notna(linha["PontosAtribuídos"]) else 0
                if action == "Excluir":
                    salvar_snapshot()
                    # se pontuou, subtrai do projetista ativo (se exist)
                    if pts_old>0 and isinstance(proj,str) and not proj.endswith("(Inativo)"):
                        if proj in st.session_state.df["Projetista"].values:
                            st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] -= pts_old
                            st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] = st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"].clip(lower=0)
                    st.session_state.historico = st.session_state.historico.drop(index=actual_idx).reset_index(drop=True)
                    st.sidebar.success("Entrada do histórico excluída e pontuação ajustada.")
                else:
                    salvar_snapshot()
                    # subtrai antigos
                    if pts_old>0 and isinstance(proj,str) and not proj.endswith("(Inativo)"):
                        if proj in st.session_state.df["Projetista"].values:
                            st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] -= pts_old
                            st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] = st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"].clip(lower=0)
                    # aplica novos
                    try:
                        new_nota = int(new_crit.split(" - ")[0])
                        new_res = new_crit.split("->")[-1].strip()
                    except:
                        st.sidebar.error("Erro ao interpretar novo critério.")
                        new_nota = None
                    novos_pts = pontos_por_nota(new_nota) if new_nota is not None else 0
                    st.session_state.historico.at[actual_idx,"Parâmetro"] = new_param
                    st.session_state.historico.at[actual_idx,"Nota"] = new_nota
                    st.session_state.historico.at[actual_idx,"Resumo"] = new_res
                    st.session_state.historico.at[actual_idx,"PontosAtribuídos"] = novos_pts
                    # aplica novos pontos
                    if novos_pts>0 and isinstance(proj,str) and not proj.endswith("(Inativo)"):
                        if proj in st.session_state.df["Projetista"].values:
                            st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] += novos_pts
                    st.sidebar.success("Entrada do histórico alterada e pontuação ajustada.")

    # Undo
    st.sidebar.markdown("---")
    if st.sidebar.button("↩️ Desfazer última ação"):
        desfazer()

    # Backup / Import
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 Backup / Import")
    if st.sidebar.button("📦 Criar Backup (ZIP)"):
        calcular_rankings()
        buf = io.BytesIO()
        with zipfile.ZipFile(buf,"w",zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("projetistas.csv", st.session_state.df.to_csv(index=False))
            zf.writestr("historico_demandas.csv", st.session_state.historico.to_csv(index=False))
        buf.seek(0)
        fn = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        st.sidebar.download_button("⬇️ Baixar Backup", data=buf.getvalue(), file_name=fn, mime="application/zip")
        st.sidebar.success("Backup pronto para download.")
    uploaded = st.sidebar.file_uploader("📂 Importar Backup (ZIP)", type=["zip"])
    if uploaded is not None:
        try:
            z = zipfile.ZipFile(io.BytesIO(uploaded.read()))
            names = z.namelist()
            if "projetistas.csv" not in names or "historico_demandas.csv" not in names:
                st.sidebar.error("ZIP inválido.")
            else:
                df_new = pd.read_csv(z.open("projetistas.csv"))
                hist_new = pd.read_csv(z.open("historico_demandas.csv"), parse_dates=["Timestamp"])
                # minimal validation
                req_df = {"Sala","Equipe","Classe","Projetista","Pontuação"}
                req_hist = {"Timestamp","Disciplina","Demanda","Projetista","Parâmetro","Nota","Resumo","PontosAtribuídos"}
                if not req_df.issubset(set(df_new.columns)) or not req_hist.issubset(set(hist_new.columns)):
                    st.sidebar.error("Estrutura inválida nos CSVs.")
                else:
                    st.session_state.df = df_new.copy()
                    st.session_state.historico = hist_new.copy()
                    st.sidebar.success("Dados importados com sucesso.")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler ZIP: {e}")

    st.sidebar.caption("Sistema com histórico e reativação. Use o backup para preservar cenários de teste.")

# Footer note
st.markdown("---")
st.caption("Observação: histórico conserva entradas marcadas como (Inativo). Use a seção Reativar para trazer alguém de volta com sua pontuação original (se disponível).")
