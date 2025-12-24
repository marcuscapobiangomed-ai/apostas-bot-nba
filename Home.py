import streamlit as st

st.set_page_config(
    page_title="Central de Inteligência Esportiva",
    page_icon="🧠",
    layout="centered"
)

st.title("🧠 Central Quantitativa")
st.markdown("---")

st.markdown("""
### 👋 Bem-vindo ao seu QG de Apostas

Você está rodando um sistema profissional de análise de dados. Selecione um módulo no menu lateral para começar:

#### 🏀 Módulo NBA (Automático)
* **Power Ratings:** Atualizados via API oficial.
* **Steam Chaser:** Detector de valor em lesões.
* **Kelly Criterion:** Gestão de banca integrada.

#### ⚽ Módulo Futebol (Poisson)
* **Análise Matemática:** Distribuição de Poisson.
* **Valor Esperado:** Calculadora de +EV para Premier League.

---
### 🛡️ Regras de Ouro
1.  **Não force aposta:** Se o modelo não vê valor, não aposte.
2.  **Respeite a Stake:** Use o Critério de Kelly sugerido.
3.  **Longo Prazo:** A matemática vence a sorte no volume.
""")

st.info("👈 Selecione o esporte na barra lateral para começar.")
