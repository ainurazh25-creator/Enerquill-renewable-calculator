import streamlit as st

st.set_page_config(
    page_title="Renewable Energy Calculator - Enerquill Advisory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Helpers
# -----------------------------
def pv_costs_split(capex_mln_per_mw, opex_mln_per_mw_per_year, capacity_mw, r, n):
    capex_usd_per_mw = float(capex_mln_per_mw) * 1_000_000
    opex_usd_per_mw_per_year = float(opex_mln_per_mw_per_year) * 1_000_000
    pv_capex = capacity_mw * capex_usd_per_mw
    annual_opex = capacity_mw * opex_usd_per_mw_per_year
    pv_opex = sum(annual_opex / ((1 + r) ** t) for t in range(1, n + 1))
    return pv_capex, pv_opex, pv_capex + pv_opex

def pv_energy_mwh(capacity_mw, capacity_factor, r, n):
    annual_mwh = capacity_mw * 8760 * capacity_factor
    return sum(annual_mwh / ((1 + r) ** t) for t in range(1, n + 1))

def lcoe_from_costs(pv_costs_total, pv_energy):
    return float("inf") if pv_energy == 0 else pv_costs_total / pv_energy

def lcoh_from_lcoe(lcoe_chain_usd_per_mwh, electrolyzer_eff, h2_energy_content_mwh_per_kg=0.0333):
    eff = max(electrolyzer_eff, 1e-9)
    return lcoe_chain_usd_per_mwh * (h2_energy_content_mwh_per_kg / eff)

def lcoa_from_lcoh(lcoh_usd_per_kg, h2_to_nh3_eff, nh3_energy_content_mwh_per_tonne=5.17):
    eff = max(h2_to_nh3_eff, 1e-9)
    return (lcoh_usd_per_kg / 0.0333) / eff * nh3_energy_content_mwh_per_tonne

def lcom_from_lcoh(lcoh_usd_per_kg, h2_to_meoh_eff, meoh_energy_content_mwh_per_tonne=5.53):
    eff = max(h2_to_meoh_eff, 1e-9)
    return (lcoh_usd_per_kg / 0.0333) / eff * meoh_energy_content_mwh_per_tonne

def fmt1(x):
    try:
        return f"{x:,.1f}"
    except Exception:
        return str(x)

# -----------------------------
# App
# -----------------------------
def main():
    st.title("⚡ Renewable Energy Calculator")
    st.caption("Enerquill Advisory – Value-chain KPIs (tuned defaults with benchmarks)")
    st.markdown("---")

    product = st.radio(
        "Select end product/value chain",
        options=["Electricity (Electrons)", "Hydrogen", "Ammonia", "Methanol"],
        horizontal=True,
    )
    mode = st.selectbox("Cost input mode", ["Simple multipliers", "Detailed breakdown"])

    st.markdown("---")
    st.header("Input Parameters (million USD units)")

    # ---------- Generation (1.3M CAPEX, 0.025 OPEX, 45% CF)
    row1 = st.columns(3)
    with row1[0]:
        gen_mw = st.number_input("Generation Capacity (MW)", min_value=0.1, value=100.0, step=0.1)
    with row1[1]:
        capex_gen_mln = st.number_input("Gen CAPEX (USD mln/MW)", min_value=0.001, value=1.30, step=0.01)
    with row1[2]:
        opex_gen_mln = st.number_input("Gen OPEX (USD mln/MW/yr)", min_value=0.001, value=0.025, step=0.001)

    row2 = st.columns(3)
    with row2[0]:
        cf = st.number_input("Capacity Factor (%)", min_value=1.0, value=45.0, step=0.1) / 100
    with row2[1]:
        r = st.number_input("Discount Rate (%)", min_value=0.1, value=7.0, step=0.1) / 100
    with row2[2]:
        n = st.number_input("Project Lifetime (years)", min_value=1, value=25, step=1)

    # PV electricity & upstream LCOE
    pv_elec = pv_energy_mwh(gen_mw, cf, r, n)
    pv_capex_gen, pv_opex_gen, pv_cost_gen = pv_costs_split(capex_gen_mln, opex_gen_mln, gen_mw, r, n)
    lcoe_up = lcoe_from_costs(pv_cost_gen, pv_elec)

    need_h2 = product in ("Hydrogen", "Ammonia", "Methanol")
    need_syn = product in ("Ammonia", "Methanol")

    # ---------- Electrolyzer
    pv_capex_elz = pv_opex_elz = pv_cost_elz = 0.0
    elz_mw = 0.0
    capex_elz_mln = opex_elz_mln = 0.0
    electrolyzer_eff = 0.70
    if need_h2:
        st.markdown("---")
        st.subheader("Electrolyzer Block")

        if mode == "Simple multipliers":
            cols = st.columns(3)
            with cols[0]:
                elz_size_vs_gen_pct = st.number_input("Size vs Gen (%)", min_value=1.0, value=100.0, step=1.0)
            with cols[1]:
                # default ~1.00 / 1.30 ≈ 77%
                elz_capex_pct_of_gen = st.number_input("CAPEX as % of Gen CAPEX", min_value=1.0, value=77.0, step=1.0)
            with cols[2]:
                # default 0.025 / 0.025 = 100%
                elz_opex_pct_of_gen = st.number_input("OPEX as % of Gen OPEX", min_value=1.0, value=100.0, step=1.0)
            elz_mw = gen_mw * (elz_size_vs_gen_pct / 100.0)
            capex_elz_mln = capex_gen_mln * (elz_capex_pct_of_gen / 100.0)
            opex_elz_mln = opex_gen_mln * (elz_opex_pct_of_gen / 100.0)
        else:
            cols = st.columns(3)
            with cols[0]:
                elz_mw = st.number_input("Electrolyzer Capacity (MW)", min_value=0.1, value=100.0, step=0.1)
            with cols[1]:
                capex_elz_mln = st.number_input("Electrolyzer CAPEX (USD mln/MW)", min_value=0.001, value=1.00, step=0.01)
            with cols[2]:
                opex_elz_mln = st.number_input("Electrolyzer OPEX (USD mln/MW/yr)", min_value=0.001, value=0.025, step=0.001)

        electrolyzer_eff = st.number_input("Electrolyzer Efficiency (%)", min_value=10.0, value=70.0, step=0.1) / 100
        pv_capex_elz, pv_opex_elz, pv_cost_elz = pv_costs_split(capex_elz_mln, opex_elz_mln, elz_mw, r, n)

    # ---------- Synthesis (Ammonia & Methanol)
    pv_capex_syn = pv_opex_syn = pv_cost_syn = 0.0
    syn_mw = 0.0
    capex_syn_mln = opex_syn_mln = 0.0
    nh3_eff = 0.65
    meoh_eff = 0.65
    # CO2 defaults for Methanol (defined even when not used to avoid NameError)
    co2_cons_t_per_t_meoh = 0.0
    co2_price_usd_per_t = 0.0

    if need_syn:
        st.markdown("---")
        st.subheader(f"Synthesis Block ({'Ammonia' if product=='Ammonia' else 'Methanol'})")

        if mode == "Simple multipliers":
            cols = st.columns(3)
            with cols[0]:
                syn_size_vs_elz_pct = st.number_input("Size vs Electrolyzer (%)", min_value=1.0, value=100.0, step=1.0)
            with cols[1]:
                # For NH3 default ~0.65/1.30=50%, for MeOH ~0.70/1.30≈54%
                default_syn_capex_pct = 50.0 if product == "Ammonia" else 54.0
                syn_capex_pct_of_gen = st.number_input("CAPEX as % of Gen CAPEX", min_value=1.0, value=default_syn_capex_pct, step=1.0)
            with cols[2]:
                # OPEX default ~0.012/0.025 ≈ 48% (both NH3/MeOH)
                syn_opex_pct_of_gen = st.number_input("OPEX as % of Gen OPEX", min_value=1.0, value=48.0, step=1.0)

            syn_mw = (elz_mw if need_h2 else gen_mw) * (syn_size_vs_elz_pct / 100.0)
            capex_syn_mln = capex_gen_mln * (syn_capex_pct_of_gen / 100.0)
            opex_syn_mln = opex_gen_mln * (syn_opex_pct_of_gen / 100.0)
        else:
            cols = st.columns(3)
            with cols[0]:
                syn_mw = st.number_input("Synthesis Capacity (MW-eq)", min_value=0.1, value=100.0, step=0.1)
            with cols[1]:
                capex_syn_mln = st.number_input(
                    "Synthesis CAPEX (USD mln/MW-eq)",
                    min_value=0.001,
                    value=(0.65 if product == "Ammonia" else 0.70),
                    step=0.01,
                )
            with cols[2]:
                opex_syn_mln = st.number_input("Synthesis OPEX (USD mln/MW-eq/yr)", min_value=0.001, value=0.012, step=0.001)

        if product == "Ammonia":
            nh3_eff = st.number_input("H2 → NH3 Efficiency (%)", min_value=10.0, value=65.0, step=0.1) / 100
        if product == "Methanol":
            meoh_eff = st.number_input("H2 → MeOH Efficiency (%)", min_value=10.0, value=65.0, step=0.1) / 100
            co2_cons_t_per_t_meoh = st.number_input("CO₂ consumption (t CO₂ / t MeOH)", min_value=0.0, value=1.375, step=0.01)
            co2_price_usd_per_t   = st.number_input("CO₂ price (USD / t CO₂)", min_value=0.0, value=45.0, step=1.0)

        pv_capex_syn, pv_opex_syn, pv_cost_syn = pv_costs_split(capex_syn_mln, opex_syn_mln, syn_mw, r, n)

    st.markdown("---")

    if st.button("Calculate", type="primary"):
        pv_chain = pv_cost_gen + pv_cost_elz + pv_cost_syn
        lcoe_chain = lcoe_from_costs(pv_chain, pv_elec)

        final_kpi_label = "LCOE"
        final_kpi_value = lcoe_chain
        if product == "Hydrogen":
            final_kpi_label = "LCOH"
            final_kpi_value = lcoh_from_lcoe(lcoe_chain, electrolyzer_eff)
        elif product == "Ammonia":
            final_kpi_label = "LCOA"
            lcoh_tmp = lcoh_from_lcoe(lcoe_chain, electrolyzer_eff)
            final_kpi_value = lcoa_from_lcoh(lcoh_tmp, nh3_eff)
        elif product == "Methanol":
            final_kpi_label = "LCOM"
            lcoh_tmp = lcoh_from_lcoe(lcoe_chain, electrolyzer_eff)
            final_kpi_value = lcom_from_lcoh(lcoh_tmp, meoh_eff)
            final_kpi_value += co2_cons_t_per_t_meoh * co2_price_usd_per_t

        # ---- Results ----
        st.header("Results")
        c = st.columns(2)
        with c[0]:
            unit = "USD/MWh" if final_kpi_label == "LCOE" else ("USD/kg" if final_kpi_label == "LCOH" else "USD/tonne")
            st.metric(final_kpi_label, f"${fmt1(final_kpi_value)}", help=unit)
        with c[1]:
            st.metric("Upstream LCOE (Generation)", f"${fmt1(lcoe_up)}", help="USD/MWh")

        # ---- Benchmarks ----
        st.markdown("### 📊 Benchmark Ranges (for reference)")
        if final_kpi_label == "LCOE":
            st.markdown("* **Renewables LCOE:** 30–60 USD/MWh  \n  Source: Lazard, *Levelized Cost of Energy 2023*")
        elif final_kpi_label == "LCOH":
            st.markdown("* **Hydrogen (LCOH):** 3–6 USD/kg  \n  Source: IEA, *Global Hydrogen Review 2023*")
        elif final_kpi_label == "LCOA":
            st.markdown("* **Ammonia (LCOA):** 900–1300 USD/t  \n  Sources: IRENA, *Green Hydrogen Cost Outlook 2023*; EU JRC, *Ammonia Cost Modelling 2022*")
        elif final_kpi_label == "LCOM":
            st.markdown("* **Methanol (LCOM):** 1000–1300 USD/t  \n  Sources: IEA, *Renewables 2023*; Methanol Institute, *Green Methanol Report 2023*")

    # ---- Notes & References (inputs + KPIs) ----
    st.markdown("---")
    with st.expander("📖 Notes & References"):
        st.markdown(
            """
**Input Ranges (typical industry values):**
- **Generation CAPEX (MUSD/MW):** Solar PV 0.8–1.2, Onshore wind 1.1–1.6, Offshore wind 2.5–4.0  
  *Sources: Lazard LCOE 2023; IRENA Renewable Power Generation Costs 2023*  
- **Generation OPEX (MUSD/MW/yr):** 0.015–0.035  (*IRENA 2023*)  
- **Capacity Factor:** Solar 18–25%, Onshore wind 35–50%, Offshore wind 45–60%  (*IEA, Renewables 2023*)  
- **Electrolyzer CAPEX (MUSD/MW):** 0.7–1.2 today; trending lower to ~0.5 by 2030  (*IEA, Global Hydrogen Review 2023*)  
- **Electrolyzer OPEX:** ~2–3% of CAPEX/yr  (*Hydrogen Council, 2022*)  
- **Electrolyzer Efficiency (HHV):** 65–75%  (*IEA, Global Hydrogen Review 2023*)  
- **Ammonia synthesis efficiency (HHV):** 60–70%  (*EU JRC, 2022*)  
- **Methanol synthesis efficiency (HHV):** 60–68%  (*Methanol Institute, 2023*)  
- **CO₂ price (USD/t):** 20–60 depending on source/region  (*IEA CCUS 2023*)

**Benchmark KPIs (today, global averages):**
- **Renewables LCOE:** 30–60 USD/MWh  (*Lazard 2023*)  
- **Hydrogen (LCOH):** 3–6 USD/kg  (*IEA, Global Hydrogen Review 2023*)  
- **Ammonia (LCOA):** 900–1300 USD/t  (*IRENA 2023; EU JRC 2022*)  
- **Methanol (LCOM):** 1000–1300 USD/t  (*IEA 2023; Methanol Institute 2023*)
            """
        )

if __name__ == "__main__":
    main()



