from extension_functions import *
from unimpairment_functions import *
from rim_inflow_functions import *
from evaporation_functions import *

if __name__ == "__main__":
    i_final_year = 2021

    ti_storage_range = pd.date_range("1921-09-30", f"{i_final_year}-09-30", freq="ME")
    ti_calculate_range = pd.date_range("1921-10-31", f"{i_final_year}-09-30", freq="ME")

    # this holds the already extended evap rates
    s_evap_dss_path = r"./Inputs/evaporation_rates.dss"

    # option to plot comparison
    b_compareData = True
    s_prev_rim_inflows_fn = "CS3_FthYub_ReadAllInflowDatatoDSS_05.18.23.csv" # file path and name must be provided to plot/calculate comparison
    s_prev_rim_inflow_sheet = "Inflows"

    # first if the needed output folders don't exist, create them
    os.makedirs('./Intermediate', exist_ok=True)
    os.makedirs('./Figures', exist_ok=True)
    os.makedirs('./Outputs', exist_ok=True)

    # read in the data that we already read in
    df_full_data = pd.read_csv('./Intermediate/feather_yuba_full_gauge_data.csv', index_col=0, parse_dates=True)

    print("Calculating evaporation...")

    # calculate the evaporation amounts for all of our reservoirs
    calc_evap_JKSMD(s_evap_dss_path, df_full_data)
    calc_evap_BOWMN(s_evap_dss_path, df_full_data)
    calc_evap_FRNCH(s_evap_dss_path, df_full_data)

    df_full_data.to_csv('./Intermediate/feather_yuba_full_gauge_data_wevap.csv')

    ### unimpairing the data
    df_unimpaired_data = pd.DataFrame(index=ti_storage_range)

    print("Calculating unimpaired flows...")

    df_unimpaired_data['11409000'] = unimpaired_11409000(df_full_data)

    # drop the first row used for storage
    df_unimpaired_data = df_unimpaired_data.loc[ti_calculate_range,:]

    # save to csv
    df_unimpaired_data.to_csv('./Intermediate/feather_yuba_unimpaired_data.csv')

    # redistribute negatives
    df_pos_unimpaired_data = remove_negatives_timeseries(df_unimpaired_data)

    # save to csv
    df_pos_unimpaired_data.to_csv('./Intermediate/feather_yuba_unimpaired_data_pos.csv')

    df_extended_data = pd.DataFrame(index=ti_storage_range)
    df_synthetic_data = pd.DataFrame(index=ti_storage_range)

    print("Extending flows...")
    # extend some with the s-curve disaggregation
    extend_data(df_unimpaired_data['11409000'], df_full_data['11413000'], df_extended_data, df_synthetic_data, 1939, 2021, False, '11413000', i_x_start_year=1922, i_final_year=1968)

    # final rim inflows
    df_rim_inflows = pd.DataFrame(index=ti_storage_range)
    
    print("Calculating rim inflows...")
    # This is input to other nodes so we need it before others
    I_NFY029(df_extended_data, df_full_data, df_unimpaired_data, df_rim_inflows)
    
    # extend some with the s-curve disaggregation that depend on rim inflows
    extend_data(df_rim_inflows["I_NFY029"], df_full_data.loc[:, "WILSON_CREEK"], df_extended_data, df_synthetic_data, 1976, 2004, False, 'WILSON_CREEK', i_x_start_year=1922, i_final_year=i_final_year)
    # this unimpaired depends on WILSON CREEK
    df_unimpaired_data['11416500'] = unimpaired_11416500(df_full_data, df_extended_data).loc[ti_calculate_range]
    df_pos_unimpaired_data = remove_negatives_timeseries(df_unimpaired_data)
    
    extend_data(df_rim_inflows["I_NFY029"], df_pos_unimpaired_data["11416500"], df_extended_data, df_synthetic_data, 1928, i_final_year, False, '11416500', i_x_start_year=1922, i_final_year=i_final_year)
    
    # # save to csv
    df_extended_data.to_csv('./Intermediate/feather_yuba_extended_data.csv')
    df_synthetic_data.to_csv('./Intermediate/feather_yuba_synthetic_data.csv')

    # this function also calculates I_FRNCH
    I_BOWMN(df_extended_data, df_rim_inflows)

    # We have one extra date at the beginning for storage
    df_rim_inflows = df_rim_inflows.loc[ti_calculate_range]
    df_rim_inflows.to_csv('./Outputs/feather_yuba_rim_inflows.csv')

    # Comparison with Previous Rim Inflow dataset
    if b_compareData:

        # read in data
        df_reference = pd.read_csv(s_prev_rim_inflows_fn, index_col=0, parse_dates=True)

        # calculate differences
        df_diffs = abs(df_reference[df_rim_inflows.columns] - df_rim_inflows).max().to_frame('Max Difference')
        df_diffs['Na Values'] = df_rim_inflows.isna().sum()
        df_diffs['Median Value - Original'] = df_reference[df_rim_inflows.columns].mean()
        df_diffs['Max Percent Difference'] = (abs(df_reference[df_rim_inflows.columns] - df_rim_inflows)).max() / df_reference[df_rim_inflows.columns].mean()*100

        print("Maximum differences:")
        print(df_diffs.sort_values(by='Max Difference', ascending=False).to_string())

        print('Creating comparison plots...')

        create_rim_inflow_comparison_plots(df_rim_inflows, df_reference)
