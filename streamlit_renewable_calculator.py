import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

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
    """Return PV CAPEX, PV OPEX, and total (USD) for a block sized by MW. Inputs are in million USD units."""
    capex_usd_per_mw = float(capex_mln_per_mw) * 1_000_000
    opex_usd_per_mw_per_year = float(opex_mln_per_mw_per_year) * 1_000_000
    pv_capex = capacity_mw * capex_usd_per_mw
    annual_opex = capacity_mw * opex_usd_per_mw_per_year
    pv_opex = sum(annual_opex / ((1 + r) ** t) for t in range(1, n + 1))
    return pv_capex, pv_opex, pv_capex + pv_opex  # USD

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

def fmt1(x):  # KPIs to 1 decimal place
    try:
        return f"{x:,.1f}"
    except Exception:
        return str(x)

# -----------------------------
# App
# -----------------------------
def main():
    st.title("⚡ Renewable Energy Calculator")
    st.caption("Enerquill Advisory – Value-chain KPIs, cost blocks, and sensitivity")
    st.markdown("---")

    product = st.radio(
        "Select end product/value chain",
        options=["Electricity (Electrons)", "Hydrogen", "Ammonia", "Methanol"],
        horizontal=True,
    )
    mode = st.selectbox(
        "Cost input mode",
        ["Simple multipliers", "Detailed breakdown"],
    )

    st.markdown("---")
    st.header("Input Parameters (million USD units)")

    # ---------- Generation (aligned rows)
    row1 = st.columns(3)
    with row1[0]:
        gen_mw = st.number_input("Generation Capacity (MW)", min_value=0.1, value=100.0, step=0.1)
    with row1[1]:
        capex_gen_mln = st.number_input("Gen CAPEX (USD mln/MW)", min_value=0.001, value=1.10, step=0.01)
    with row1[2]:
        opex_gen_mln = st.number_input("Gen OPEX (USD mln/MW/yr)", min_value=0.001, value=0.015, step=0.001)

    row2 = st.columns(3)
    with row2[0]:
        cf = st.number_input("Capacity Factor (%)", min_value=1.0, value=25.0, step=0.1) / 100
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

    # ---------- Electrolyzer (optional)
    pv_capex_elz = pv_opex_elz = pv_cost_elz = 0.0
    elz_mw = 0.0
    capex_elz_mln = opex_elz_mln = 0.0
    electrolyzer_eff = 0.75
    if need_h2:
        st.markdown("---")
        st.subheader("Electrolyzer Block")
        if mode == "Simple multipliers":
            cols = st.columns(3)
            with cols[0]:
                elz_size_ratio = st.number_input("Electrolyzer size vs Gen (%)", min_value=1.0, value=100.0, step=1.0) / 100
            with cols[1]:
                elz_capex_mult = st.number_input("Electrolyzer CAPEX as % of Gen CAPEX", min_value=0.0, value=80.0, step=1.0) / 100
            with cols[2]:
                elz_opex_mult = st.number_input("Electrolyzer OPEX as % of Gen OPEX", min_value=0.0, value=80.0, step=1.0) / 100
            elz_mw = gen_mw * elz_size_ratio
            capex_elz_mln = capex_gen_mln * elz_capex_mult
            opex_elz_mln = opex_gen_mln * elz_opex_mult
        else:
            cols = st.columns(3)
            with cols[0]:
                elz_mw = st.number_input("Electrolyzer Capacity (MW)", min_value=0.1, value=100.0, step=0.1)
            with cols[1]:
                capex_elz_mln = st.number_input("Electrolyzer CAPEX (USD mln/MW)", min_value=0.001, value=1.20, step=0.01)
            with cols[2]:
                opex_elz_mln = st.number_input("Electrolyzer OPEX (USD mln/MW/yr)", min_value=0.001, value=0.024, step=0.001)

        electrolyzer_eff = st.number_input("Electrolyzer Efficiency (%)", min_value=10.0, value=75.0, step=0.1) / 100
        pv_capex_elz, pv_opex_elz, pv_cost_elz = pv_costs_split(capex_elz_mln, opex_elz_mln, elz_mw, r, n)

    # ---------- Synthesis (optional)
    pv_capex_syn = pv_opex_syn = pv_cost_syn = 0.0
    syn_mw = 0.0
    capex_syn_mln = opex_syn_mln = 0.0
    nh3_eff = 0.525
    meoh_eff = 0.495
    if need_syn:
        st.markdown("---")
        st.subheader(f"Synthesis Block ({'Ammonia' if product=='Ammonia' else 'Methanol'})")
        if mode == "Simple multipliers":
            cols = st.columns(3)
            with cols[0]:
                syn_size_ratio = st.number_input("Synthesis size vs Electrolyzer (%)", min_value=1.0, value=100.0, step=1.0) / 100
            with cols[1]:
                syn_capex_mult = st.number_input("Synthesis CAPEX as % of Gen CAPEX", min_value=0.0, value=60.0, step=1.0) / 100
            with cols[2]:
                syn_opex_mult = st.number_input("Synthesis OPEX as % of Gen OPEX", min_value=0.0, value=60.0, step=1.0) / 100
            syn_mw = (elz_mw if need_h2 else gen_mw) * syn_size_ratio
            capex_syn_mln = capex_gen_mln * syn_capex_mult
            opex_syn_mln = opex_gen_mln * syn_opex_mult
        else:
            cols = st.columns(3)
            with cols[0]:
                syn_mw = st.number_input("Synthesis Capacity (MW-eq)", min_value=0.1, value=100.0, step=0.1)
            with cols[1]:
                capex_syn_mln = st.number_input("Synthesis CAPEX (USD mln/MW-eq)", min_value=0.001, value=0.90, step=0.01)
            with cols[2]:
                opex_syn_mln = st.number_input("Synthesis OPEX (USD mln/MW-eq/yr)", min_value=0.001, value=0.018, step=0.001)

        if product == "Ammonia":
            nh3_eff = st.number_input("H2 → NH3 Efficiency (%)", min_value=10.0, value=52.5, step=0.1) / 100
        if product == "Methanol":
            meoh_eff = st.number_input("H2 → Methanol Efficiency (%)", min_value=10.0, value=49.5, step=0.1) / 100
            # --- NEW CO2 inputs ---
            co2_cons_t_per_t_meoh = st.number_input("CO₂ consumption (t CO₂ / t MeOH)", min_value=0.0, value=1.375, step=0.01)
            co2_price_usd_per_t   = st.number_input("CO₂ price (USD / t CO₂)", min_value=0.0, value=50.0, step=1.0)
        else:
            co2_cons_t_per_t_meoh = 0.0
            co2_price_usd_per_t   = 0.0

        pv_capex_syn, pv_opex_syn, pv_cost_syn = pv_costs_split(capex_syn_mln, opex_syn_mln, syn_mw, r, n)

    st.markdown("---")

    if st.button("Calculate", type="primary"):
        pv_chain = pv_cost_gen + pv_cost_elz + pv_cost_syn
        lcoe_chain = lcoe_from_costs(pv_chain, pv_elec)

        # Final KPI
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

        st.markdown("---")

        # ---- CAPEX/OPEX Breakdown ----
        st.subheader("CAPEX/OPEX Breakdown – Full Value Chain")
        capex_parts = [pv_capex_gen, pv_capex_elz, pv_capex_syn]
        opex_parts  = [pv_opex_gen,  pv_opex_elz,  pv_opex_syn]
        labels      = ["Generation", "Electrolyzer", "Synthesis"]

        total_capex = float(sum(capex_parts))
        total_opex  = float(sum(opex_parts))

        if total_capex == 0 and total_opex == 0:
            st.info("No CAPEX/OPEX values to plot for the selected configuration.")
        else:
            fig1, ax1 = plt.subplots(figsize=(6.5, 4))
            bar_width = 0.4
            capex_x = -bar_width / 2
            opex_x  =  bar_width / 2
            bottom_capex = 0.0
            bottom_opex  = 0.0
            for val, lab in zip(capex_parts, labels):
                if val > 0:
                    ax1.bar(capex_x, val / 1e6, bar_width, bottom=bottom_capex, label=f"{lab} CAPEX")
                    bottom_capex += val / 1e6
            for val, lab in zip(opex_parts, labels):
                if val > 0:
                    ax1.bar(opex_x, val / 1e6, bar_width, bottom=bottom_opex, label=f"{lab} OPEX", alpha=0.7)
                    bottom_opex += val / 1e6
            ax1.set_xticks([capex_x, opex_x])
            ax1.set_xticklabels(["CAPEX", "OPEX"])
            ax1.set_ylabel("Present Value (million USD)")
            ax1.set_title("Full Chain Cost Components")
            handles, leg_labels = ax1.get_legend_handles_labels()
            if handles:
                ax1.legend(loc="upper right", fontsize=8)
            st.pyplot(fig1)

        # ---- Tornado Sensitivity ----
        st.subheader("Sensitivity – Final KPI (Tornado)")
        sens_pct = st.slider("Variation per parameter", 5, 50, 20, step=5) / 100

        def recompute(capex_gen=capex_gen_mln, opex_gen=opex_gen_mln, cf_=cf, r_=r,
                      capex_elz=capex_elz_mln, opex_elz=opex_elz_mln, elz_mw_=elz_mw,
                      capex_syn=capex_syn_mln, opex_syn=opex_syn_mln, syn_mw_=syn_mw,
                      elz_eff=electrolyzer_eff, nh3_=nh3_eff, meoh_=meoh_eff,
                      co2_cons_=co2_cons_t_per_t_meoh, co2_price_=co2_price_usd_per_t):
            pv_capex_g, pv_opex_g, pv_cost_g = pv_costs_split(capex_gen, opex_gen, gen_mw, r_, n)
            pv_cost_e = pv_cost_s = 0.0
            if need_h2:
                _, _, pv_cost_e = pv_costs_split(capex_elz, opex_elz, elz_mw_, r_, n)
            if need_syn:
                _, _, pv_cost_s = pv_costs_split(capex_syn, opex_syn, syn_mw_, r_, n)
            pv_chain_loc = pv_cost_g + pv_cost_e + pv_cost_s
            lcoe_chain_loc = lcoe_from_costs(pv_chain_loc, pv_elec)
            if product == "Electricity (Electrons)":
                return lcoe_chain_loc
            elif product == "Hydrogen":
                return lcoh_from_lcoe(lcoe_chain_loc, elz_eff)
            elif product == "Ammonia":
                return lcoa_from_lcoh(lcoh_from_lcoe(lcoe_chain_loc, elz_eff), nh3_)
            else:
                return lcom_from_lcoh(lcoh_from_lcoe(lcoe_chain_loc, elz_eff), meoh_) + co2_cons_ * co2_price_

        baseline = {
            "Electricity (Electrons)": lcoe_chain,
            "Hydrogen": lcoh_from_lcoe(lcoe_chain, electrolyzer_eff),
            "Ammonia": lcoa_from_lcoh(lcoh_from_lcoe(lcoe_chain, electrolyzer_eff), nh3_eff),
            "Methanol": lcom_from_lcoh(lcoh_from_lcoe(lcoe_chain, electrolyzer_eff), meoh_eff) + co2_cons_t_per_t_meoh * co2_price_usd_per_t,
        }[product]

        entries = []
        params = [
            ("Gen CAPEX (mln/MW)", "capex_gen"),
            ("Gen OPEX (mln/MW/yr)", "opex_gen"),
            ("Capacity Factor (%)", "cf"),
            ("Discount Rate (%)", "r"),
        ]
        if need_h2:
            params += [("Electrolyzer CAPEX (mln/MW)", "capex_elz"),
                       ("Electrolyzer OPEX (mln/MW/yr)", "opex_elz"),
                       ("Electrolyzer Efficiency (%)", "elz_eff")]
        if need_syn:
            syn_label = "NH3" if product == "Ammonia" else "MeOH"
            params += [(f"{syn_label} CAPEX (mln/MW)", "capex_syn"),
                       (f"{syn_label} OPEX (mln/MW/yr)", "opex_syn"),
                       (f"H2 → {syn_label} Efficiency (%)", "syn_eff")]
        if product == "Methanol":
            params += [("CO₂ consumption (t/t MeOH)", "co2_cons"),
                       ("CO₂ price (USD/t CO₂)", "co2_price")]

        for label, key in params:
            low_kwargs, high_kwargs = {}, {}
            if key == "capex_gen":
                low_kwargs["capex_gen"] = capex_gen_mln * (1 - sens_pct)
                high_kwargs["capex_gen"] = capex_gen_mln * (1 + sens_pct)
            elif key == "opex_gen":
                low_kwargs["opex_gen"] = opex_gen_mln * (1 - sens_pct)
                high_kwargs["opex_gen"] = opex_gen_mln * (1 + sens_pct)
            elif key == "cf":
                low_kwargs["cf_"] = max(0.05, cf * (1 - sens_pct))
                high_kwargs["cf_"] = min(0.95, cf * (1 + sens_pct))
            elif key == "r":
                low_kwargs["r_"] = max(0.0, r * (1 - sens_pct))
                high_kwargs["r_"] = r * (1 + sens_pct)
            elif key == "capex_elz":
                low_kwargs["capex_elz"] = max(0.0, capex_elz_mln * (1 - sens_pct))
                high_kwargs["capex_elz"] = capex_elz_mln * (1 + sens_pct)
            elif key == "opex_elz":
                low_kwargs["opex_elz"] = max(0.0, opex_elz_mln * (1 - sens_pct))
                high_kwargs["opex_elz"] = opex_elz_mln * (1 + sens_pct)
            elif key == "elz_eff":
                low_kwargs["elz_eff"] = max(0.1, electrolyzer_eff * (1 - sens_pct))
                high_kwargs["elz_eff"] = min(0.95, electrolyzer_eff * (1 + sens_pct))
            elif key == "capex_syn":
                low_kwargs["capex_syn"] = max(0.0, capex_syn_mln * (1 - sens_pct))
                high_kwargs["capex_syn"] = capex_syn_mln * (1 + sens_pct)
            elif key == "opex_syn":
                low_kwargs["opex_syn"] = max(0.0, opex_syn_mln * (1 - sens_pct))
                high_kwargs["opex_syn"] = opex_syn_mln * (1 + sens_pct)
            elif key == "syn_eff":
                base_eff = nh3_eff if product == "Ammonia" else meoh_eff
                low_kwargs["nh3_" if product == "Ammonia" else "meoh_"] = max(0.1, base_eff * (1 - sens_pct))
                high_kwargs["nh3_" if product == "Ammonia" else "meoh_"] = min(0.95, base_eff * (1 + sens_pct))
            elif key == "co2_cons":
                low_kwargs["co2_cons_"] = max(0.0, co2_cons_t_per_t_meoh * (1 - sens_pct))
                high_kwargs["co2_cons_"] = co2_cons_t_per_t_meoh * (1 + sens_pct)
            elif key == "co2_price":
                low_kwargs["co2_price_"] = max(0.0, co2_price_usd_per_t * (1 - sens_pct))
                high_kwargs["co2_price_"] = co2_price_usd_per_t * (1 + sens_pct)

            low = recompute(**low_kwargs)
            high = recompute(**high_kwargs)
            entries.append((label, baseline - low, high - baseline,
                            max(abs(baseline - low), abs(high - baseline))))

        # order by impact
        entries.sort(key=lambda x: x[3], reverse=True)
        labels_sorted = [e[0] for e in entries]
        lows = [e[1] for e in entries]
        highs = [e[2] for e in entries]

        fig2, ax2 = plt.subplots(figsize=(7.5, 6))
        y_pos = np.arange(len(labels_sorted))
        ax2.barh(y_pos, lows, align='center', label='-Δ (low)', alpha=0.8)
        ax2.barh(y_pos, highs, left=lows, align='center', label='+Δ (high)', alpha=0.6)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(labels_sorted)
        ax2.set_xlabel(f"Change in {final_kpi_label}")
        ax2.set_title(f"Tornado – Sensitivity of {final_kpi_label}")
        ax2.legend(loc='lower right', fontsize=8)
        st.pyplot(fig2)

if __name__ == "__main__":
    main()
