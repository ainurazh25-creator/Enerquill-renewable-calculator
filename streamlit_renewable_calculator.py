
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
    [data-testid="collapsedControl"] svg { display: inline !important; }
    [data-testid="collapsedControl"]::before { content: '>>'; font-family: 'Inter', system-ui, sans-serif; }
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

def calculate_lcoe(power_capacity_mw, capex_usd_per_mw, opex_usd_per_mw_per_year, discount_rate, project_lifetime_years, capacity_factor):
    total_capex = power_capacity_mw * capex_usd_per_mw
    annual_opex = power_capacity_mw * opex_usd_per_mw_per_year
    pv_capex = total_capex
    pv_opex = 0
    for year in range(1, project_lifetime_years + 1):
        pv_opex += annual_opex / ((1 + discount_rate) ** year)
    total_pv_costs = pv_capex + pv_opex
    annual_energy_mwh = power_capacity_mw * 8760 * capacity_factor
    pv_energy_produced = 0
    for year in range(1, project_lifetime_years + 1):
        pv_energy_produced += annual_energy_mwh / ((1 + discount_rate) ** year)
    if pv_energy_produced == 0:
        return float("inf")
    return total_pv_costs / pv_energy_produced

def calculate_lcoh(lcoe_usd_per_mwh, electrolyzer_efficiency, h2_energy_content_mwh_per_kg=0.0333):
    return lcoe_usd_per_mwh * (h2_energy_content_mwh_per_kg / max(electrolyzer_efficiency, 1e-9))

def calculate_lcoa(lcoh_usd_per_kg, h2_to_nh3_efficiency, nh3_energy_content_mwh_per_tonne=5.17):
    return (lcoh_usd_per_kg / 0.0333) / max(h2_to_nh3_efficiency, 1e-9) * nh3_energy_content_mwh_per_tonne

def calculate_lcom(lcoh_usd_per_kg, h2_to_methanol_efficiency, methanol_energy_content_mwh_per_tonne=5.53):
    return (lcoh_usd_per_kg / 0.0333) / max(h2_to_methanol_efficiency, 1e-9) * methanol_energy_content_mwh_per_tonne

def format_number(num):
    try:
        return f"{num:,.2f}"
    except Exception:
        return str(num)

def main():
    st.title("⚡ Renewable Energy Calculator")
    st.caption("Enerquill Advisory – Value-chain specific KPIs")
    st.markdown("---")

    product = st.radio(
        "Select end product/value chain",
        options=["Electricity (Electrons)", "Hydrogen", "Ammonia", "Methanol"],
        horizontal=True,
        help="Choose the final product to calculate the most relevant KPI (LCOE, LCOH, LCOA, LCOM).",
    )
    st.markdown("---")

    st.header("Input Parameters")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Project Parameters")
        power_capacity = st.number_input("Power Capacity (MW)", 0.1, value=100.0, step=0.1)
        capex = st.number_input("CAPEX (USD/MW)", 1000, value=1_500_000, step=1_000)
        opex = st.number_input("OPEX (USD/MW/year)", 1000, value=30_000, step=1_000)

    with col2:
        st.subheader("Financial Parameters")
        discount_rate = st.number_input("Discount Rate (%)", 0.1, value=7.0, step=0.1) / 100
        project_lifetime = st.number_input("Project Lifetime (years)", 1, value=25, step=1)
        capacity_factor = st.number_input("Capacity Factor (%)", 1.0, value=40.0, step=0.1) / 100

    with col3:
        st.subheader("Conversion Efficiencies")
        show_h2 = product in ("Hydrogen", "Ammonia", "Methanol")
        show_nh3 = product == "Ammonia"
        show_meoh = product == "Methanol"

        if show_h2:
            electrolyzer_efficiency = st.number_input("Electrolyzer Efficiency (%)", 10.0, value=75.0, step=0.1) / 100
        else:
            electrolyzer_efficiency = 0.75

        if show_nh3:
            h2_to_nh3_efficiency = st.number_input("H2 → NH3 Efficiency (%)", 10.0, value=52.5, step=0.1) / 100
        else:
            h2_to_nh3_efficiency = 0.525

        if show_meoh:
            h2_to_methanol_efficiency = st.number_input("H2 → Methanol Efficiency (%)", 10.0, value=49.5, step=0.1) / 100
        else:
            h2_to_methanol_efficiency = 0.495

    st.markdown("---")

    if st.button("Calculate", type="primary"):
        lcoe = calculate_lcoe(power_capacity, capex, opex, discount_rate, project_lifetime, capacity_factor)
        lcoh = lcoa = lcom = None
        if product in ("Hydrogen", "Ammonia", "Methanol"):
            lcoh = calculate_lcoh(lcoe, electrolyzer_efficiency)
        if product == "Ammonia" and lcoh is not None:
            lcoa = calculate_lcoa(lcoh, h2_to_nh3_efficiency)
        if product == "Methanol" and lcoh is not None:
            lcom = calculate_lcom(lcoh, h2_to_methanol_efficiency)

        st.header("Results")
        res_cols = st.columns(3)

        if product == "Electricity (Electrons)":
            with res_cols[0]: st.metric("LCOE", f"${format_number(lcoe)}", help="USD/MWh")
        elif product == "Hydrogen":
            with res_cols[0]: st.metric("LCOH", f"${format_number(lcoh)}", help="USD/kg")
            with res_cols[1]: st.metric("Upstream LCOE", f"${format_number(lcoe)}", help="USD/MWh")
        elif product == "Ammonia":
            with res_cols[0]: st.metric("LCOA", f"${format_number(lcoa)}", help="USD/tonne")
            with res_cols[1]: st.metric("LCOH (feedstock)", f"${format_number(lcoh)}", help="USD/kg")
            with res_cols[2]: st.metric("Upstream LCOE", f"${format_number(lcoe)}", help="USD/MWh")
        elif product == "Methanol":
            with res_cols[0]: st.metric("LCOM", f"${format_number(lcom)}", help="USD/tonne")
            with res_cols[1]: st.metric("LCOH (feedstock)", f"${format_number(lcoh)}", help="USD/kg")
            with res_cols[2]: st.metric("Upstream LCOE", f"${format_number(lcoe)}", help="USD/MWh")

        st.markdown("---")

        rows = []
        if product == "Electricity (Electrons)":
            rows.append(["LCOE", f"${format_number(lcoe)}", "USD/MWh", "Levelized Cost of Energy (electricity)"])
        elif product == "Hydrogen":
            rows.append(["LCOH", f"${format_number(lcoh)}", "USD/kg", "Levelized Cost of Hydrogen"])
            rows.append(["Upstream LCOE", f"${format_number(lcoe)}", "USD/MWh", "Electricity cost feeding electrolysis"])
        elif product == "Ammonia":
            rows.append(["LCOA", f"${format_number(lcoa)}", "USD/tonne", "Levelized Cost of Ammonia"])
            rows.append(["LCOH (feedstock)", f"${format_number(lcoh)}", "USD/kg", "Hydrogen cost used in synthesis"])
            rows.append(["Upstream LCOE", f"${format_number(lcoe)}", "USD/MWh", "Electricity cost feeding electrolysis"])
        elif product == "Methanol":
            rows.append(["LCOM", f"${format_number(lcom)}", "USD/tonne", "Levelized Cost of Methanol"])
            rows.append(["LCOH (feedstock)", f"${format_number(lcoh)}", "USD/kg", "Hydrogen cost used in synthesis"])
            rows.append(["Upstream LCOE", f"${format_number(lcoe)}", "USD/MWh", "Electricity cost feeding electrolysis"])

        results_df = pd.DataFrame(rows, columns=["Metric", "Value", "Unit", "Description"])
        st.subheader("Results Summary")
        st.dataframe(results_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.header("About This Calculator")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**LCOE** – average cost of electricity generation over the asset lifetime (USD/MWh).  \n**LCOH** – cost to produce hydrogen from electricity via electrolysis (USD/kg).")
    with c2:
        st.markdown("**LCOA** – cost to produce ammonia from hydrogen (USD/tonne).  \n**LCOM** – cost to produce methanol from hydrogen (USD/tonne).")

if __name__ == "__main__":
    main()
