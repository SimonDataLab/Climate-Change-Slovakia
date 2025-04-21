import cdsapi
import pandas as pd
import os
import xarray as xr

# Initialize the CDS API client
c = cdsapi.Client()

# Define the range of years and frequency
years = [str(year) for year in range(1940, 2025)]
frequency = 'monthly'  # Change to 'daily' for daily data, but monthly is recommended for this large range

# Define the dataset based on the chosen frequency
if frequency == 'daily':
    dataset_name = 'reanalysis-era5-land'  # Dataset for daily data
    time_param = '12:00'  # Using noon as the daily reading
elif frequency == 'monthly':
    dataset_name = 'reanalysis-era5-single-levels-monthly-means'  # Dataset for monthly data
    time_param = '00:00'  # Monthly average

# Create directory for storing yearly files
output_dir = 'slovakia_temperature_data'
os.makedirs(output_dir, exist_ok=True)

# Loop through each year and download the data
for year in years:
    output_file = os.path.join(output_dir, f'slovakia_temperature_{frequency}_{year}.nc')
    if not os.path.exists(output_file):
        print(f"Downloading {frequency} data for {year}...")
        download_params = {
            'product_type': 'monthly_averaged_reanalysis' if frequency == 'monthly' else 'reanalysis',
            'variable': '2m_temperature',
            'year': year,
            'month': [str(m).zfill(2) for m in range(1, 13)],  # All months
            'time': time_param,
            'area': [
                49.6, 16.8, 47.7, 22.6,  # Bounding box for Slovakia [North, West, South, East]
            ],
            'format': 'netcdf'
        }
        
        # Retrieve and save data for each year
        c.retrieve(dataset_name, download_params, output_file)
        print(f"{frequency.capitalize()} data for {year} downloaded and saved as {output_file}")
    else:
        print(f"File for {year} already exists. Skipping download.")

# Process each year's data and save to a combined Excel file
combined_data = []

for year in years:
    input_file = os.path.join(output_dir, f'slovakia_temperature_{frequency}_{year}.nc')
    
    try:
        # Load the data with xarray
        ds = xr.open_dataset(input_file)
        
        # Convert to DataFrame and reset index
        df = ds.to_dataframe().reset_index()
        
        # Convert temperature to Celsius if in Kelvin
        if 't2m' in df.columns:
            df['2m_temperature'] = df['t2m'] - 273.15
        
        # Ensure longitude and latitude are included and rename 'date' to 'time' if necessary
        if 'valid_time' in df.columns:
            df.rename(columns={'valid_time': 'time'}, inplace=True)
        columns_to_include = ['time', 'latitude', 'longitude', '2m_temperature']
        df = df[columns_to_include]

        # Format 'time' to 'yyyy/mm/dd'
        df['time'] = pd.to_datetime(df['time'], format='%Y%m%d').dt.strftime('%Y/%m/%d')
        
        # Append the year's data to the combined list
        combined_data.append(df)

    except Exception as e:
        print(f"Error processing {input_file}: {e}")

# Concatenate all yearly data
if combined_data:
    final_df = pd.concat(combined_data)
    excel_file = 'slovakia_temperature_1940_2024_combined.xlsx'
    final_df.to_excel(excel_file, sheet_name='Temperature Data', index=False)
    print(f"All data from 1940 to 2024 has been written to {excel_file}.")
else:
    print("No data was downloaded or processed.")

