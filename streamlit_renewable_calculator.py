import streamlit as st
import numpy as np
import pandas as pd

st.set_page_config(
    page_title="Renewable Energy Calculator - Enerquill Advisory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    html, body, [class*="css"]  { font-family: 'Inter', system-ui, sans-serif !important; }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #0d6efd, #0a58ca);
        color: white; font-weight: 600; border-radius: 10px; border: none;
        height: 3em; width: 100%; box-shadow: 0 6px 14px rgba(0,0,0,.15);
        transition: all .18s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(90deg, #0a58ca, #0d6efd); transform: translateY(-2px);
        box-shadow: 0 10px 20px rgba(0,0,0,.20);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def pv_costs(capex_mln_per_mw, opex_mln_per_mw_per_year, capacity_mw, r, n):
    capex_usd_per_mw = capex_mln_per_mw * 1_000_000
    opex_usd_per_mw_per_year = opex_mln_per_mw_per_year * 1_000_000
    total_capex = capacity_mw * capex_usd_per_mw
    annual_opex = capacity_mw * opex_usd_per_mw_per_year
    pv_opex = sum(annual_opex / ((1 + r) ** t) for t in range(1, n + 1))
    return total_capex + pv_opex

def pv_energy_mwh(capacity_mw, capacity_factor, r, n):
    annual_mwh = capacity_mw * 8760 * capacity_factor
    return sum(annual_mwh / ((1 + r) ** t) for t in range(1, n + 1))

def calculate_lcoe_from_costs(pv_costs_total, pv_energy):
    if pv_energy == 0:
        return float("inf")
    return pv_costs_total / pv_energy

def calculate_lcoh(lcoe_chain_usd_per_mwh, electrolyzer_efficiency, h2_energy_content_mwh_per_kg=0.0333):
    eff = max(electrolyzer_efficiency, 1e-9)
    return lcoe_chain_usd_per_mwh * (h2_energy_content_mwh_per_kg / eff)

def calculate_lcoa(lcoh_usd_per_kg, h2_to_nh3_efficiency, nh3_energy_content_mwh_per_tonne=5.17):
    eff = max(h2_to_nh3_efficiency, 1e-9)
    return (lcoh_usd_per_kg / 0.0333) / eff * nh3_energy_content_mwh_per_tonne

def calculate_lcom(lcoh_usd_per_kg, h2_to_methanol_efficiency, methanol_energy_content_mwh_per_tonne=5.53):
    eff = max(h2_to_methanol_efficiency, 1e-9)
    return (lcoh_usd_per_kg / 0.0333) / eff * methanol_energy_content_mwh_per_tonne

def format_number(x):
    try:
        return f"{x:,.2f}"
    except Exception:
        return str(x)

def main():
    st.title("⚡ Renewable Energy Calculator")
    st.caption("Enerquill Advisory – Value-chain specific KPIs & cost blocks")
    st.markdown("---")

    product = st.radio(
        "Select end product/value chain",
        options=["Electricity (Electrons)", "Hydrogen", "Ammonia", "Methanol"],
        horizontal=True,
    )

    mode = st.selectbox(
        "Cost input mode",
        ["Simple multipliers", "Detailed breakdown"],
        help="Choose whether to enter costs as multipliers of generation, or detailed absolute values in million USD units.",
    )

    st.markdown("---")
    st.header("Input Parameters")

    g1, g2, g3 = st.columns(3)
    with g1:
        st.subheader("Generation (Renewables)")
        gen_mw = st.number_input("Generation Capacity (MW)", min_value=0.1, value=100.0, step=0.1)
        capex_gen = st.number_input("Gen CAPEX (USD mln/MW)", min_value=0.001, value=1.50, step=0.01)
    with g2:
        opex_gen = st.number_input("Gen OPEX (USD mln/MW/yr)", min_value=0.001, value=0.03, step=0.001)
        cf = st.number_input("Capacity Factor (%)", min_value=1.0, value=40.0, step=0.1) / 100
    with g3:
        r = st.number_input("Discount Rate (%)", min_value=0.1, value=7.0, step=0.1) / 100
        n = st.number_input("Project Lifetime (years)", min_value=1, value=25, step=1)

    pv_elec = pv_energy_mwh(gen_mw, cf, r, n)
    pv_cost_gen = pv_costs(capex_gen, opex_gen, gen_mw, r, n)
    lcoe_upstream = calculate_lcoe_from_costs(pv_cost_gen, pv_elec)

    need_h2 = product in ("Hydrogen", "Ammonia", "Methanol")
    need_syn = product in ("Ammonia", "Methanol")

    electrolyzer_eff = 0.75
    nh3_eff = 0.525
    meoh_eff = 0.495

    pv_cost_elz = 0.0
    elz_mw = 0.0
    if need_h2:
        st.markdown("---")
        st.subheader("Electrolyzer Block")
        if mode == "Simple multipliers":
            c1, c2, c3 = st.columns(3)
            with c1:
                elz_size_ratio = st.number_input("Electrolyzer size vs Gen (%)", min_value=1.0, value=100.0, step=1.0) / 100
            with c2:
                elz_capex_mult = st.number_input("Electrolyzer CAPEX as % of Gen CAPEX", min_value=0.0, value=80.0, step=1.0) / 100
            with c3:
                elz_opex_mult = st.number_input("Electrolyzer OPEX as % of Gen OPEX", min_value=0.0, value=80.0, step=1.0) / 100

            elz_mw = gen_mw * elz_size_ratio
            capex_elz = capex_gen * elz_capex_mult
            opex_elz = opex_gen * elz_opex_mult
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                elz_mw = st.number_input("Electrolyzer Capacity (MW)", min_value=0.1, value=float(100.0), step=0.1)
            with c2:
                capex_elz = st.number_input("Electrolyzer CAPEX (USD mln/MW)", min_value=0.001, value=1.20, step=0.01)
            with c3:
                opex_elz = st.number_input("Electrolyzer OPEX (USD mln/MW/yr)", min_value=0.001, value=0.024, step=0.001)

        electrolyzer_eff = st.number_input("Electrolyzer Efficiency (%)", min_value=10.0, value=75.0, step=0.1) / 100
        pv_cost_elz = pv_costs(capex_elz, opex_elz, elz_mw, r, n)

    pv_cost_syn = 0.0
    syn_mw = 0.0
    if need_syn:
        st.markdown("---")
        st.subheader(f"Synthesis Block ({'Ammonia' if product=='Ammonia' else 'Methanol'})")
        if mode == "Simple multipliers":
            d1, d2, d3 = st.columns(3)
            with d1:
                syn_size_ratio = st.number_input("Synthesis size vs Electrolyzer (%)", min_value=1.0, value=100.0, step=1.0) / 100
            with d2:
                syn_capex_mult = st.number_input("Synthesis CAPEX as % of Gen CAPEX", min_value=0.0, value=60.0, step=1.0) / 100
            with d3:
                syn_opex_mult = st.number_input("Synthesis OPEX as % of Gen OPEX", min_value=0.0, value=60.0, step=1.0) / 100

            syn_mw = (elz_mw if need_h2 else gen_mw) * syn_size_ratio
            capex_syn = capex_gen * syn_capex_mult
            opex_syn = opex_gen * syn_opex_mult
        else:
            d1, d2, d3 = st.columns(3)
            with d1:
                syn_mw = st.number_input("Synthesis Capacity (MW-eq)", min_value=0.1, value=float(100.0), step=0.1)
            with d2:
                capex_syn = st.number_input("Synthesis CAPEX (USD mln/MW-eq)", min_value=0.001, value=0.90, step=0.01)
            with d3:
                opex_syn = st.number_input("Synthesis OPEX (USD mln/MW-eq/yr)", min_value=0.001, value=0.018, step=0.001)

        if product == "Ammonia":
            nh3_eff = st.number_input("H2 → NH3 Efficiency (%)", min_value=10.0, value=52.5, step=0.1) / 100
        if product == "Methanol":
            meoh_eff = st.number_input("H2 → Methanol Efficiency (%)", min_value=10.0, value=49.5, step=0.1) / 100

        pv_cost_syn = pv_costs(capex_syn, opex_syn, syn_mw, r, n)

    st.markdown("---")

    if st.button("Calculate", type="primary"):
        lcoe_up = calculate_lcoe_from_costs(pv_cost_gen, pv_elec)
        pv_chain = pv_cost_gen + pv_cost_elz + pv_cost_syn
        lcoe_chain = calculate_lcoe_from_costs(pv_chain, pv_elec)

        lcoh = lcoa = lcom = None
        if need_h2:
            lcoh = calculate_lcoh(lcoe_chain, electrolyzer_eff)
        if product == "Ammonia" and lcoh is not None:
            lcoa = calculate_lcoa(lcoh, nh3_eff)
        if product == "Methanol" and lcoh is not None:
            lcom = calculate_lcom(lcoh, meoh_eff)

        st.header("Results")
        cols = st.columns(3)

        if product == "Electricity (Electrons)":
            with cols[0]:
                st.metric("LCOE", f"${format_number(lcoe_up)}", help="USD/MWh")
        elif product == "Hydrogen":
            with cols[0]:
                st.metric("LCOH", f"${format_number(lcoh)}", help="USD/kg")
            with cols[1]:
                st.metric("Upstream LCOE (Generation)", f"${format_number(lcoe_up)}", help="USD/MWh")
        elif product == "Ammonia":
            with cols[0]:
                st.metric("LCOA", f"${format_number(lcoa)}", help="USD/tonne")
            with cols[1]:
                st.metric("LCOH (Feedstock)", f"${format_number(lcoh)}", help="USD/kg")
            with cols[2]:
                st.metric("Upstream LCOE (Generation)", f"${format_number(lcoe_up)}", help="USD/MWh")
        elif product == "Methanol":
            with cols[0]:
                st.metric("LCOM", f"${format_number(lcom)}", help="USD/tonne")
            with cols[1]:
                st.metric("LCOH (Feedstock)", f"${format_number(lcoh)}", help="USD/kg")
            with cols[2]:
                st.metric("Upstream LCOE (Generation)", f"${format_number(lcoe_up)}", help="USD/MWh")

        st.markdown("---")

        rows = []
        if product == "Electricity (Electrons)":
            rows.append(["LCOE", f"${format_number(lcoe_up)}", "USD/MWh", "Levelized Cost of Energy (generation only)"])
        elif product == "Hydrogen":
            rows.append(["LCOH", f"${format_number(lcoh)}", "USD/kg", "Levelized Cost of Hydrogen (gen + electrolyzer)"])
            rows.append(["Upstream LCOE", f"${format_number(lcoe_up)}", "USD/MWh", "Generation-only electricity cost"])
        elif product == "Ammonia":
            rows.append(["LCOA", f"${format_number(lcoa)}", "USD/tonne", "Levelized Cost of Ammonia (gen + electrolyzer + synthesis)"])
            rows.append(["LCOH (feedstock)", f"${format_number(lcoh)}", "USD/kg", "Hydrogen cost (gen + electrolyzer)"])
            rows.append(["Upstream LCOE", f"${format_number(lcoe_up)}", "USD/MWh", "Generation-only electricity cost"])
        elif product == "Methanol":
            rows.append(["LCOM", f"${format_number(lcom)}", "USD/tonne", "Levelized Cost of Methanol (gen + electrolyzer + synthesis)"])
            rows.append(["LCOH (feedstock)", f"${format_number(lcoh)}", "USD/kg", "Hydrogen cost (gen + electrolyzer)"])
            rows.append(["Upstream LCOE", f"${format_number(lcoe_up)}", "USD/MWh", "Generation-only electricity cost"])

        df = pd.DataFrame(rows, columns=["Metric", "Value", "Unit", "Description"])
        st.subheader("Results Summary")
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.header("About This Calculator")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**LCOE** – generation-only electricity cost (USD/MWh).  ")
        st.markdown("**LCOH** – hydrogen cost from full chain (gen + electrolyzer).  ")
    with c2:
        st.markdown("**LCOA/LCOM** – ammonia/methanol cost from full chain (gen + electrolyzer + synthesis).  ")
        st.markdown("All CAPEX/OPEX inputs are in **million USD units** per MW or MW/yr. Defaults adjusted accordingly.")

if __name__ == "__main__":
    main()
