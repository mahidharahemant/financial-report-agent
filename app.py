import json
import streamlit as st

from src.agents.agent import analyze_company

st.set_page_config(page_title="Financial Report Intelligence Agent", page_icon="📊", layout="wide")
st.title("📊 Financial Report Intelligence Agent")
st.caption("LangChain agent · SEC EDGAR · XBRL facts · Evidence-backed narrative analysis")

with st.sidebar:
    st.header("Analysis settings")
    ticker = st.text_input("Ticker symbol", value="MSFT", max_chars=12).strip().upper()
    fiscal_year = st.number_input("Fiscal year", min_value=2000, max_value=2100, value=2025, step=1)
    run = st.button("Analyze annual report", type="primary", use_container_width=True)
    st.caption("Public SEC filings and an LLM API. Educational use only; not investment advice.")

if run:
    if not ticker:
        st.error("Enter a ticker symbol.")
    else:
        try:
            with st.spinner(f"Finding and analyzing {ticker} FY{fiscal_year}..."):
                st.session_state["analysis_result"] = analyze_company(ticker, int(fiscal_year))
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")
            st.info("Check API key, SEC_USER_AGENT, ticker, fiscal year, and network access.")

result = st.session_state.get("analysis_result")
if result:
    st.subheader(f"{result.get('company_name', result.get('ticker', ticker))} — FY{result.get('fiscal_year', fiscal_year)}")
    if result.get("filing_url"):
        st.markdown(f"[Open original SEC filing]({result['filing_url']})")

    metrics = result.get("financial_metrics", [])
    if isinstance(metrics, dict):
        metrics = [{"name": name, **(value if isinstance(value, dict) else {"value": value})} for name, value in metrics.items()]
    if metrics:
        st.subheader("Financial metrics")
        st.dataframe(metrics, use_container_width=True, hide_index=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Risk factors")
        risks = result.get("risk_factors", [])
        if risks:
            for risk in risks:
                if isinstance(risk, dict):
                    with st.expander(risk.get("category", "Risk")):
                        st.write(risk.get("description", ""))
                        st.caption(risk.get("supporting_evidence", ""))
                        if risk.get("source_url"):
                            st.markdown(f"[Source]({risk['source_url']})")
                else:
                    st.write(risk)
        else:
            st.write("No structured risk factors returned.")
    with right:
        st.subheader("Management outlook")
        for item in result.get("management_outlook", []):
            st.markdown(f"- {item}")
        st.subheader("Key observations")
        for item in result.get("key_observations", []):
            st.markdown(f"- {item}")

    for limitation in result.get("limitations", []):
        st.warning(limitation)
    st.download_button(
        "Download JSON",
        data=json.dumps(result, indent=2),
        file_name=f"analysis_{result.get('ticker', ticker)}_{result.get('fiscal_year', fiscal_year)}.json",
        mime="application/json",
    )
    with st.expander("Raw JSON output"):
        st.json(result)
else:
    st.info("Try ticker MSFT and fiscal year 2025.")
    st.markdown("**The agent can:** find a 10-K, retrieve structured financial facts, search narrative risk/outlook sections, calculate metrics in Python, and return source-linked JSON.")
