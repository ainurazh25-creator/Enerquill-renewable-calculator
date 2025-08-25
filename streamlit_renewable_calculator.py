import streamlit as st
import numpy as np
import pandas as pd

# Configure page
st.set_page_config(
    page_title="Renewable Energy Calculator - Enerquill Advisory",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply custom CSS styling based on provided theme
st.markdown("""
    <style>
    /* Global font application */
    html, body, [class*="css"]  {
        font-family: 'Inter', system-ui, sans-serif !important;
    }

    /* Ensure Streamlit sidebar collapse button displays correctly */
    [data-testid="collapsedControl"] svg {
        display: inline !important;  /* show the arrow icon */
    }
    [data-testid="collapsedControl"]::before {
        content: '>>';  /* fallback if icon fails */
        font-family: 'Inter', system-ui, sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Custom button styling
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #0d6efd, #0a58ca); /* Primary blue */
        color: white;
        font-weight: bold;
        border-radius: 8px;
        border: none; /* Remove border */
        height: 3em;
        width: 100%;
        box-shadow: 0px 4px 8px rgba(0,0,0,0.2);
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(90deg, #0a58ca, #0d6efd);
        transform: translateY(-2px);
        box-shadow: 0px 6px 12px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

def calculate_lcoe(power_capacity_mw, capex_usd_per_mw, opex_usd_per_mw_per_year, discount_rate, project_lifetime_years, capacity_factor):
    """
    Calculates the Levelized Cost of Energy (LCOE).
    """
    total_capex = power_capacity_mw * capex_usd_per_mw
    annual_opex = power_capacity_mw * opex_usd_per_mw_per_year

    # Calculate present value of costs
    pv_capex = total_capex
    pv_opex = 0
    for year in range(1, project_lifetime_years + 1):
        pv_opex += annual_opex / ((1 + discount_rate)**year)
    total_pv_costs = pv_capex + pv_opex

    # Calculate present value of energy produced
    annual_energy_mwh = power_capacity_mw * 8760 * capacity_factor
    pv_energy_produced = 0
    for year in range(1, project_lifetime_years + 1):
        pv_energy_produced += annual_energy_mwh / ((1 + discount_rate)**year)

    if pv_energy_produced == 0:
        return float("inf")  # Avoid division by zero

    lcoe = total_pv_costs / pv_energy_produced
    return lcoe

def calculate_lcoh(lcoe_usd_per_mwh, electrolyzer_efficiency, h2_energy_content_mwh_per_kg=0.0333):
    """
    Calculates the Levelized Cost of Hydrogen (LCOH).
    """
    lcoh = lcoe_usd_per_mwh * (h2_energy_content_mwh_per_kg / electrolyzer_efficiency)
    return lcoh

def calculate_lcoa(lcoh_usd_per_kg, h2_to_nh3_efficiency, nh3_energy_content_mwh_per_tonne=5.17):
    """
    Calculates the Levelized Cost of Ammonia (LCOA).
    """
    lcoa = (lcoh_usd_per_kg / 0.0333) / h2_to_nh3_efficiency * nh3_energy_content_mwh_per_tonne
    return lcoa

def calculate_lcom(lcoh_usd_per_kg, h2_to_methanol_efficiency, methanol_energy_content_mwh_per_tonne=5.53):
    """
    Calculates the Levelized Cost of Methanol (LCOM).
    """
    lcom = (lcoh_usd_per_kg / 0.0333) / h2_to_methanol_efficiency * methanol_energy_content_mwh_per_tonne
    return lcom

def format_number(num):
    """Format numbers with thousand separators."""
    return f"{num:,.2f}"

# Main app
def main():
    # Header
    st.title("⚡ Renewable Energy Calculator")
    st.subheader("Calculate LCOE, LCOH, LCOA, and LCOM for your renewable energy projects")
    st.caption("Powered by Enerquill Advisory")
    
    st.markdown("---")
    
    # Input Parameters Section
    st.header("Input Parameters")
    
    # Create columns for input layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Project Parameters")
        power_capacity = st.number_input(
            "Power Capacity (MW)",
            min_value=0.1,
            value=100.0,
            step=0.1,
            help="Total power generation capacity of the renewable energy project"
        )
        
        capex = st.number_input(
            "CAPEX (USD/MW)",
            min_value=1000,
            value=1500000,
            step=1000,
            help="Capital expenditure per MW of capacity"
        )
        
        opex = st.number_input(
            "OPEX (USD/MW/year)",
            min_value=1000,
            value=30000,
            step=1000,
            help="Annual operational expenditure per MW of capacity"
        )
    
    with col2:
        st.subheader("Financial Parameters")
        discount_rate = st.number_input(
            "Discount Rate (%)",
            min_value=0.1,
            value=7.0,
            step=0.1,
            help="Discount rate for present value calculations"
        ) / 100
        
        project_lifetime = st.number_input(
            "Project Lifetime (years)",
            min_value=1,
            value=25,
            step=1,
            help="Expected operational lifetime of the project"
        )
        
        capacity_factor = st.number_input(
            "Capacity Factor (%)",
            min_value=1.0,
            value=40.0,
            step=0.1,
            help="Average capacity utilization over the year"
        ) / 100
    
    with col3:
        st.subheader("Conversion Efficiencies")
        electrolyzer_efficiency = st.number_input(
            "Electrolyzer Efficiency (%)",
            min_value=10.0,
            value=75.0,
            step=0.1,
            help="Efficiency of electricity to hydrogen conversion"
        ) / 100
        
        h2_to_nh3_efficiency = st.number_input(
            "H2 to NH3 Efficiency (%)",
            min_value=10.0,
            value=52.5,
            step=0.1,
            help="Efficiency of hydrogen to ammonia conversion"
        ) / 100
        
        h2_to_methanol_efficiency = st.number_input(
            "H2 to Methanol Efficiency (%)",
            min_value=10.0,
            value=49.5,
            step=0.1,
            help="Efficiency of hydrogen to methanol conversion"
        ) / 100
    
    st.markdown("---")
    
    # Calculate button
    if st.button("Calculate Levelized Costs", type="primary"):
        # Perform calculations
        lcoe = calculate_lcoe(power_capacity, capex, opex, discount_rate, project_lifetime, capacity_factor)
        lcoh = calculate_lcoh(lcoe, electrolyzer_efficiency)
        lcoa = calculate_lcoa(lcoh, h2_to_nh3_efficiency)
        lcom = calculate_lcom(lcoh, h2_to_methanol_efficiency)
        
        # Display results
        st.header("Calculation Results")
        
        # Create columns for results
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="LCOE",
                value=f"${format_number(lcoe)}",
                help="Levelized Cost of Energy (USD/MWh)"
            )
            st.caption("USD/MWh")
        
        with col2:
            st.metric(
                label="LCOH",
                value=f"${format_number(lcoh)}",
                help="Levelized Cost of Hydrogen (USD/kg)"
            )
            st.caption("USD/kg")
        
        with col3:
            st.metric(
                label="LCOA",
                value=f"${format_number(lcoa)}",
                help="Levelized Cost of Ammonia (USD/tonne)"
            )
            st.caption("USD/tonne")
        
        with col4:
            st.metric(
                label="LCOM",
                value=f"${format_number(lcom)}",
                help="Levelized Cost of Methanol (USD/tonne)"
            )
            st.caption("USD/tonne")
        
        st.markdown("---")
        
        # Summary table
        st.subheader("Results Summary")
        results_df = pd.DataFrame({
            'Metric': ['LCOE', 'LCOH', 'LCOA', 'LCOM'],
            'Value': [f"${format_number(lcoe)}", f"${format_number(lcoh)}", f"${format_number(lcoa)}", f"${format_number(lcom)}"],
            'Unit': ['USD/MWh', 'USD/kg', 'USD/tonne', 'USD/tonne'],
            'Description': [
                'Levelized Cost of Energy',
                'Levelized Cost of Hydrogen',
                'Levelized Cost of Ammonia',
                'Levelized Cost of Methanol'
            ]
        })
        
        st.dataframe(results_df, use_container_width=True, hide_index=True)
    
    # Information section
    st.markdown("---")
    st.header("About This Calculator")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **LCOE** represents the average cost of electricity generation over the lifetime of a power plant.
        
        **LCOH** calculates the cost of producing hydrogen through electrolysis using the renewable electricity.
        """)
    
    with col2:
        st.markdown("""
        **LCOA** and **LCOM** estimate the costs of producing ammonia and methanol respectively, using the hydrogen as a feedstock.
        
        This tool is provided by **Enerquill Advisory** for strategic energy decision-making and project evaluation.
        """)
    
    # Download section
    st.markdown("---")
    st.header("Download Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Excel Calculator**")
        st.caption("Download a fully functional Excel version for offline use")
        # Note: In a real deployment, you would need to provide the actual Excel file
        st.info("Contact Enerquill Advisory to receive the Excel version of this calculator.")
    
    with col2:
        st.markdown("**Python Script**")
        st.caption("Download the Python calculation engine")
        st.info("Contact Enerquill Advisory to receive the Python scripts for this calculator.")

if __name__ == "__main__":
    main()

