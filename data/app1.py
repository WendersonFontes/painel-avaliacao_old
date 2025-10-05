# app.py
# Painel de Avaliação de Projetistas - versão Streamlit
# Cole este arquivo como app.py e rode com `streamlit run app.py`

import streamlit as st
import pandas as pd
import io, zipfile, os
from datetime import datetime
import copy

st.set_page_config(page_title="Painel de Avaliação - Streamlit", layout="wide")

# -----------------------
# Configuração inicial
# -----------------------
SENHA_PADRAO = "1234"
VAGAS_POR_SALA = 6
SALAS_INFO = [(1, "Hidrossanitário"), (2, "Hidrossanitário"), (3, "Elétrica"), (4, "Elétrica")]
CLASSES = ["S", "A", "B", "C", "D"]

# Critérios: (nota, frase, resumo)
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

# -----------------------
# Helpers
# -----------------------
def pontos_por_nota(nota):
    if nota == 10: return 3
    if nota == 9: return 2
    if nota == 8: return 1
    return 0

def init_session_state():
    if "df" not in st.session_state:
        rows = []
        for sala, equipe in SALAS_INFO:
            for _ in range(VAGAS_POR_SALA):
                rows.append({"Sala": sala, "Equipe": equipe, "Classe": "-", "Projetista": "-", "Pontuação": 0})
        st.session_state.df = pd.DataFrame(rows)
    if "historico" not in st.session_state:
        st.session_state.historico = pd.DataFrame(columns=[
            "Timestamp", "Disciplina", "Demanda", "Projetista", "Parâmetro", "Nota", "Resumo", "PontosAtribuídos"
        ])
    if "last_df" not in st.session_state:
        st.session_state.last_df = None
    if "last_hist" not in st.session_state:
        st.session_state.last_hist = None
    if "logged" not in st.session_state:
        st.session_state.logged = False
    if "status_msg" not in st.session_state:
        st.session_state.status_msg = ""

init_session_state()

def salvar_snapshot_para_undo():
    st.session_state.last_df = st.session_state.df.copy(deep=True)
    st.session_state.last_hist = st.session_state.historico.copy(deep=True)

def desfazer_ultima_acao():
    if st.session_state.last_df is None and st.session_state.last_hist is None:
        st.warning("Não há ação anterior para desfazer.")
        return
    st.session_state.df = st.session_state.last_df.copy(deep=True) if st.session_state.last_df is not None else st.session_state.df
    st.session_state.historico = st.session_state.last_hist.copy(deep=True) if st.session_state.last_hist is not None else st.session_state.historico
    st.session_state.last_df = None
    st.session_state.last_hist = None
    st.success("Última ação desfeita com sucesso.")

def calcular_rankings():
    df = st.session_state.df
    df["RankingClasse"] = "-"
    for classe in CLASSES:
        subset = df[df["Classe"] == classe].copy()
        if subset.empty: continue
        subset_sorted = subset.sort_values("Pontuação", ascending=False)
        for rank, (idx, _) in enumerate(subset_sorted.iterrows(), start=1):
            if df.at[idx, "Pontuação"] > 0:
                df.at[idx, "RankingClasse"] = rank
            else:
                df.at[idx, "RankingClasse"] = "-"
    st.session_state.df = df

def atualizar_dropdowns():
    # in Streamlit we simply read from session_state when building selects
    pass

# -----------------------
# UI: barra lateral - Autenticação / Informações
# -----------------------
st.sidebar.title("Acesso")
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

# Show summary counts at top
def mostrar_resumo_topo():
    df = st.session_state.df
    ativos = df[df["Projetista"]!="-"]
    total_ativos = len(ativos)
    total_vagas = len(df)
    vagas_livres = total_vagas - total_ativos
    hid_ativos = len(ativos[ativos["Equipe"]=="Hidrossanitário"])
    ele_ativos = len(ativos[ativos["Equipe"]=="Elétrica"])
    st.markdown(f"**Projetistas ativos:** {total_ativos} — **Vagas livres:** {vagas_livres}  \nHidrossanitário: {hid_ativos} | Elétrica: {ele_ativos}")

mostrar_resumo_topo()

# -----------------------
# Função para exibir visualizações principais
# -----------------------
def exibir_painel_principal():
    st.header("Painel de Gestão - Visualizações")
    calcular_rankings()
    df = st.session_state.df.copy()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Por Sala")
        for sala in sorted(df["Sala"].unique()):
            equipe = df[df["Sala"]==sala]["Equipe"].iloc[0]
            st.write(f"🏢 **Sala {sala}** ({equipe})")
            subset = df[df["Sala"]==sala][["Projetista","Equipe","Classe","RankingClasse","Pontuação"]].reset_index(drop=True)
            st.dataframe(subset, use_container_width=True)
    with col2:
        st.subheader("Ranking por Classes (unificado entre disciplinas)")
        for classe in CLASSES:
            sub = df[df["Classe"]==classe].sort_values("Pontuação", ascending=False)
            if not sub.empty:
                st.write(f"**Classe {classe}**")
                st.dataframe(sub[["Projetista","Equipe","Sala","Pontuação","RankingClasse"]].reset_index(drop=True), use_container_width=True)
        st.subheader("Ranking Geral")
        geral = df[df["Projetista"]!="-"].sort_values("Pontuação", ascending=False).reset_index(drop=True)
        if not geral.empty:
            geral_display = geral.copy()
            geral_display["Ranking Geral"] = geral_display.index + 1
            geral_display["Ranking Geral"] = geral_display.apply(lambda x: x["Ranking Geral"] if x["Pontuação"]>0 else "-", axis=1)
            st.dataframe(geral_display[["Ranking Geral","Projetista","Equipe","Classe","Sala","RankingClasse","Pontuação"]], use_container_width=True)
        else:
            st.info("Nenhum projetista alocado ainda.")
    st.markdown("---")
    st.subheader("Histórico de Demandas (acumulativo)")
    hist = st.session_state.historico.copy()
    if hist.empty:
        st.info("Nenhuma demanda registrada ainda.")
    else:
        # show two tabs: Hidro / Eletrica
        t1, t2 = st.tabs(["Hidrossanitário","Elétrica"])
        with t1:
            hid = hist[hist["Disciplina"]=="Hidrossanitário"].sort_values("Timestamp", ascending=False).reset_index(drop=True)
            if not hid.empty:
                st.dataframe(hid, use_container_width=True)
            else:
                st.info("Nenhuma demanda para Hidrossanitário.")
        with t2:
            ele = hist[hist["Disciplina"]=="Elétrica"].sort_values("Timestamp", ascending=False).reset_index(drop=True)
            if not ele.empty:
                st.dataframe(ele, use_container_width=True)
            else:
                st.info("Nenhuma demanda para Elétrica.")

# -----------------------
# Show main view (always visible)
# -----------------------
exibir_painel_principal()

# -----------------------
# Coordinator panel (only if logged)
# -----------------------
st.sidebar.markdown("---")
st.sidebar.header("Painel do Coordenador")
if not st.session_state.logged:
    st.sidebar.info("Faça login com a senha para ver o painel do coordenador.")
else:
    # Controls
    st.sidebar.subheader("Gerenciamento de Projetistas")
    # Add new projetista
    with st.sidebar.expander("➕ Adicionar Projetista", expanded=False):
        novo_nome = st.text_input("Nome do Projetista", key="input_novo_nome")
        disciplina = st.selectbox("Disciplina", options=["Hidrossanitário","Elétrica"], key="input_disciplina")
        # determine salas available for discipline
        salas_op = [s for s,e in SALAS_INFO if e==disciplina]
        seleciona_sala = st.selectbox("Sala", options=salas_op, key="input_sala")
        classe_nova = st.selectbox("Classe", options=CLASSES, key="input_classe")
        if st.button("Adicionar Projetista"):
            if not novo_nome.strip():
                st.warning("Digite um nome válido.")
            else:
                vagas = st.session_state.df[(st.session_state.df["Sala"]==seleciona_sala) & (st.session_state.df["Projetista"]=="-")]
                if vagas.empty:
                    st.error("Sala cheia! Remova alguém primeiro.")
                else:
                    salvar_snapshot_para_undo()
                    idx = vagas.index[0]
                    st.session_state.df.at[idx,"Projetista"] = novo_nome.strip()
                    st.session_state.df.at[idx,"Equipe"] = disciplina
                    st.session_state.df.at[idx,"Classe"] = classe_nova
                    st.session_state.df.at[idx,"Pontuação"] = 0
                    st.success(f"Projetista '{novo_nome}' adicionado à sala {seleciona_sala} ({disciplina}) na classe {classe_nova}.")

    # Rename
    with st.sidebar.expander("✏️ Renomear Projetista", expanded=False):
        ativos = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        selecionado_rename = st.selectbox("Projetista", options=ativos, key="rename_select") if ativos else None
        novo_nome_rename = st.text_input("Novo nome", key="rename_input")
        if st.button("Atualizar nome"):
            if not selecionado_rename or not novo_nome_rename.strip():
                st.warning("Escolha projetista e digite novo nome.")
            else:
                salvar_snapshot_para_undo()
                st.session_state.df.loc[st.session_state.df["Projetista"]==selecionado_rename,"Projetista"] = novo_nome_rename.strip()
                st.success("Nome atualizado.")

    # Alterar classe
    with st.sidebar.expander("🏷️ Alterar Classe", expanded=False):
        ativos2 = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        selecionado_classe = st.selectbox("Projetista", options=ativos2, key="classe_select") if ativos2 else None
        nova_classe = st.selectbox("Nova Classe", options=CLASSES, key="classe_nova_select")
        if st.button("Alterar Classe"):
            if not selecionado_classe:
                st.warning("Selecione um projetista.")
            else:
                salvar_snapshot_para_undo()
                st.session_state.df.loc[st.session_state.df["Projetista"]==selecionado_classe,"Classe"] = nova_classe
                st.success("Classe alterada.")

    # Remover
    with st.sidebar.expander("🗑️ Remover Projetista", expanded=False):
        ativos3 = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        selecionado_remover = st.selectbox("Projetista", options=ativos3, key="remover_select") if ativos3 else None
        if st.button("Remover Projetista"):
            if not selecionado_remover:
                st.warning("Selecione um projetista para remover.")
            else:
                salvar_snapshot_para_undo()
                st.session_state.df.loc[st.session_state.df["Projetista"]==selecionado_remover, ["Projetista","Classe","Pontuação","RankingClasse"]] = ["-","-",0,"-"]
                st.success("Projetista removido e vaga liberada.")

    # Quick add points
    with st.sidebar.expander("➕ Adicionar Pontos (rápido)", expanded=False):
        ativos4 = st.session_state.df[st.session_state.df["Projetista"]!="-"]["Projetista"].tolist()
        escolha_add = st.selectbox("Projetista", options=ativos4, key="addpts_select") if ativos4 else None
        qtd_pts = st.number_input("Pontos", min_value=1, max_value=100, value=1, step=1, key="addpts_qtd")
        if st.button("Adicionar Pontos (rápido)"):
            if not escolha_add:
                st.warning("Selecione um projetista.")
            else:
                salvar_snapshot_para_undo()
                st.session_state.df.loc[st.session_state.df["Projetista"]==escolha_add,"Pontuação"] += int(qtd_pts)
                st.success("Pontos adicionados.")

    st.sidebar.markdown("---")
    # Demandas
    st.sidebar.subheader("📋 Demandas (Criar / Validar)")
    with st.sidebar.form("form_demanda"):
        demanda_nome = st.text_input("Nome da Demanda")
        demanda_disciplina = st.selectbox("Disciplina", options=["Hidrossanitário","Elétrica"])
        # projetistas filtrados
        ativos5 = st.session_state.df[(st.session_state.df["Equipe"]==demanda_disciplina) & (st.session_state.df["Projetista"]!="-")]["Projetista"].tolist()
        demanda_projetista = st.selectbox("Projetista", options=ativos5) if ativos5 else None
        parametro = st.selectbox("Parâmetro", options=list(CRITERIOS.keys()))
        # monta critérios
        criterios_op = [f"{nota} - {frase} -> {resumo}" for (nota,frase,resumo) in CRITERIOS[parametro]]
        criterio = st.selectbox("Critério", options=criterios_op)
        submit_demanda = st.form_submit_button("Validar definição de ponto")
        if submit_demanda:
            if not demanda_nome.strip() or not demanda_projetista or not criterio:
                st.warning("Preencha demanda, disciplina, projetista e critério.")
            else:
                try:
                    nota = int(criterio.split(" - ")[0])
                    resumo = criterio.split("->")[-1].strip()
                except Exception:
                    st.error("Não foi possível interpretar o critério. Tente novamente.")
                    st.stop()
                salvar_snapshot_para_undo()
                pontos = pontos_por_nota(nota)
                if pontos == 0:
                    st.warning("Nota <= 7: não é possível pontuar. A entrada será registrada no histórico sem pontos.")
                else:
                    st.session_state.df.loc[st.session_state.df["Projetista"]==demanda_projetista,"Pontuação"] += pontos
                    st.success(f"{pontos} ponto(s) adicionados ao {demanda_projetista}.")
                nova = {
                    "Timestamp": pd.Timestamp.now(),
                    "Disciplina": demanda_disciplina,
                    "Demanda": demanda_nome.strip(),
                    "Projetista": demanda_projetista,
                    "Parâmetro": parametro,
                    "Nota": nota,
                    "Resumo": resumo,
                    "PontosAtribuídos": pontos
                }
                st.session_state.historico = pd.concat([pd.DataFrame([nova]), st.session_state.historico], ignore_index=True)
    st.sidebar.markdown("---")

    # Gerenciar demandas: editar / excluir (index corresponde à exibição ordenada por Timestamp desc)
    st.sidebar.subheader("✏️ Gerenciar Demandas (Editar / Excluir)")
    if st.session_state.historico.empty:
        st.sidebar.info("Nenhuma demanda no histórico.")
    else:
        max_idx = max(0, len(st.session_state.historico)-1)
        idx_manage = st.sidebar.number_input("Índice (0 = mais recente)", min_value=0, max_value=max_idx, value=0, step=1, key="manage_idx")
        action = st.sidebar.selectbox("Ação", options=["Alterar","Excluir"], key="manage_action")
        new_param = st.sidebar.selectbox("Novo Parâmetro (para Alterar)", options=list(CRITERIOS.keys()), key="manage_new_param")
        new_crit_ops = [f"{nota} - {frase} -> {resumo}" for (nota,frase,resumo) in CRITERIOS[new_param]]
        new_crit = st.sidebar.selectbox("Novo Critério (para Alterar)", options=new_crit_ops, key="manage_new_crit")
        if st.sidebar.button("Confirmar Ação"):
            # map display index to actual index in historico
            sorted_hist = st.session_state.historico.sort_values("Timestamp", ascending=False).reset_index()
            if idx_manage < 0 or idx_manage >= len(sorted_hist):
                st.sidebar.error("Índice inválido.")
            else:
                actual_idx = int(sorted_hist.loc[idx_manage,"index"])
                # show confirmation area
                if action == "Excluir":
                    # confirm deletion
                    if st.sidebar.button("Confirmar exclusão — Sim, excluir agora"):
                        salvar_snapshot_para_undo()
                        linha = st.session_state.historico.loc[actual_idx].to_dict()
                        proj = linha["Projetista"]
                        pts_ant = int(linha["PontosAtribuídos"]) if pd.notna(linha["PontosAtribuídos"]) else 0
                        if pts_ant > 0 and proj and proj!="-":
                            if proj in st.session_state.df["Projetista"].values:
                                st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] -= pts_ant
                                st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] = st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"].clip(lower=0)
                        st.session_state.historico = st.session_state.historico.drop(index=actual_idx).reset_index(drop=True)
                        st.success("Demanda excluída e pontuação (se aplicável) ajustada.")
                else:
                    # Alterar
                    if st.sidebar.button("Confirmar alteração — Sim, aplicar"):
                        salvar_snapshot_para_undo()
                        linha = st.session_state.historico.loc[actual_idx].to_dict()
                        proj = linha["Projetista"]
                        pts_ant = int(linha["PontosAtribuídos"]) if pd.notna(linha["PontosAtribuídos"]) else 0
                        # subtrai pontos antigos
                        if pts_ant > 0 and proj and proj!="-":
                            if proj in st.session_state.df["Projetista"].values:
                                st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] -= pts_ant
                                st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] = st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"].clip(lower=0)
                        # parse new
                        try:
                            nova_nota = int(new_crit.split(" - ")[0])
                            novo_resumo = new_crit.split("->")[-1].strip()
                        except Exception:
                            st.sidebar.error("Erro ao interpretar o critério novo.")
                            nova_nota = None
                        novos_pts = pontos_por_nota(nova_nota) if nova_nota is not None else 0
                        # update historico
                        st.session_state.historico.at[actual_idx,"Parâmetro"] = new_param
                        st.session_state.historico.at[actual_idx,"Nota"] = nova_nota
                        st.session_state.historico.at[actual_idx,"Resumo"] = novo_resumo
                        st.session_state.historico.at[actual_idx,"PontosAtribuídos"] = novos_pts
                        # aplicar novos pontos
                        if novos_pts > 0 and proj and proj!="-":
                            if proj in st.session_state.df["Projetista"].values:
                                st.session_state.df.loc[st.session_state.df["Projetista"]==proj,"Pontuação"] += novos_pts
                        st.success("Demanda alterada e pontuação ajustada.")

    st.sidebar.markdown("---")
    # Undo
    if st.sidebar.button("↩️ Desfazer Última Ação"):
        desfazer_ultima_acao()

    st.sidebar.markdown("---")
    # Backup & Import
    st.sidebar.subheader("💾 Backup / Import")
    # Backup: create zip in memory and provide download
    if st.sidebar.button("📦 Criar Backup (ZIP)"):
        calcular_rankings()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("projetistas.csv", st.session_state.df.to_csv(index=False))
            zf.writestr("historico_demandas.csv", st.session_state.historico.to_csv(index=False))
        buffer.seek(0)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"backup_{ts}.zip"
        st.sidebar.download_button("⬇️ Baixar Backup (ZIP)", data=buffer.getvalue(), file_name=filename, mime="application/zip")
        st.sidebar.success("Backup pronto. Use o botão para baixar o arquivo ZIP.")

    uploaded = st.sidebar.file_uploader("📂 Importar Backup (ZIP)", type=["zip"])
    if uploaded is not None:
        # read zip and validate
        try:
            z = zipfile.ZipFile(io.BytesIO(uploaded.read()))
            names = z.namelist()
            if "projetistas.csv" not in names or "historico_demandas.csv" not in names:
                st.sidebar.error("ZIP inválido: faltam 'projetistas.csv' ou 'historico_demandas.csv'.")
            else:
                with z.open("projetistas.csv") as f:
                    df_new = pd.read_csv(f)
                with z.open("historico_demandas.csv") as f:
                    hist_new = pd.read_csv(f, parse_dates=["Timestamp"])
                # minimal validation
                req_df_cols = {"Sala","Equipe","Classe","Projetista","Pontuação"}
                req_hist_cols = {"Timestamp","Disciplina","Demanda","Projetista","Parâmetro","Nota","Resumo","PontosAtribuídos"}
                if not req_df_cols.issubset(set(df_new.columns)) or not req_hist_cols.issubset(set(hist_new.columns)):
                    st.sidebar.error("Estrutura dos CSVs não corresponde ao esperado.")
                else:
                    st.session_state.df = df_new.copy()
                    st.session_state.historico = hist_new.copy()
                    st.success("Dados importados com sucesso! Painel atualizado.")
        except Exception as e:
            st.sidebar.error(f"Erro ao ler ZIP: {e}")

    st.sidebar.markdown("---")
    st.sidebar.caption("Versão Streamlit do Painel de Avaliação. Use o backup para preservar cenários de teste.")

# -----------------------
# Footer / extras
# -----------------------
st.markdown("---")
st.caption("Observação: índices mostrados no histórico (no app) estão ordenados por Timestamp decrescente — índice 0 corresponde à demanda mais recente. Use o painel do coordenador (barra lateral) para gerenciar e testar.")

