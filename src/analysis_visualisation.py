import xarray as xr
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

# Directory where the yearly .nc files are stored
data_dir = 'slovakia_temperature_data'
years = range(1940, 2025)
window_length = 10  # Set the main moving average window length in years
all_data = []

# Load data for each year and concatenate into a single DataFrame
for year in years:
    file_path = os.path.join(data_dir, f'slovakia_temperature_monthly_{year}.nc')
    if os.path.exists(file_path):
        ds = xr.open_dataset(file_path)
        df = ds.to_dataframe().reset_index()
        if 't2m' in df.columns:
            df['2m_temperature'] = df['t2m'] - 273.15  # Convert from Kelvin to Celsius
        # Convert 'date' to datetime and drop unnecessary columns
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        df = df[['date', 'latitude', 'longitude', '2m_temperature']]
        all_data.append(df)

# Combine all yearly data into one DataFrame
full_data = pd.concat(all_data)

# Extract year and month for grouping
full_data['year'] = full_data['date'].dt.year
full_data['month'] = full_data['date'].dt.month

# Group by year and month to calculate monthly averages per location
monthly_data = full_data.groupby(['year', 'month', 'latitude', 'longitude']).mean().reset_index()

# Define the start and end year for each window sample
start_year = 1940
end_year = 2024
sample_windows = [(start, start + window_length - 1) for start in range(start_year, end_year - window_length + 1)]

# Calculate moving averages for the main window (e.g., 20 years)
monthly_averages = {}

for start, end in sample_windows:
    sample = monthly_data[(monthly_data['year'] >= start) & (monthly_data['year'] <= end)]
    monthly_avg = sample.groupby(['month'])['2m_temperature'].mean().reset_index()
    monthly_averages[f"{start}-{end}"] = monthly_avg

# Initialize arrays to store cumulative sum and count for running mean calculation
cumulative_sum = np.zeros(12)  # Stores the cumulative sum for each month
cumulative_count = np.zeros(12)  # Stores the count of values for each month

# Prepare data for animation
fig, (ax, ax_diff) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})
fig.suptitle(f"{window_length}-Year Moving Average Monthly Air Temperatures and Difference from Cumulative Mean ({start_year}-{end_year})")

# Main plot settings
# ax.set_xlabel("Month")
ax.set_ylabel("Average Temperature (°C)")
months = range(1, 13)
ax.set_ylim(-7, 23)
ax.grid(True)  # Enable grid for main plot

# Set custom x-axis labels to first three letters of each month
month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ax.set_xticks(months)
ax.set_xticklabels(month_labels)

# Secondary plot for differences
# ax_diff.set_xlabel("Month")
ax_diff.set_ylabel("Difference from Cumulative Mean (°C)")
ax_diff.set_ylim(-2, 4)
ax_diff.grid(True)  # Enable grid for difference plot
ax_diff.set_xticks(months)
ax_diff.set_xticklabels(month_labels)

# Initialize the main line plot and secondary bar plot
line, = ax.plot(months, np.zeros(12), 'o-', color='red')
text = ax.text(0.5, 0.95, "", transform=ax.transAxes, ha="center")
bars = ax_diff.bar(months, np.zeros(12), color='gray', alpha=0.6)

# Initialize a list to keep track of faded lines in main plot
faded_lines = []

# Update function for the animation
def update(frame):
    global cumulative_sum, cumulative_count  # Ensure access to global variables

    # Clear faded lines from previous frames on the first frame
    if frame[0] == list(monthly_averages.keys())[0]:  # First frame
        for faded_line in faded_lines:
            faded_line.remove()
        faded_lines.clear()
    
    window, data = frame
    text.set_text(f"{window} {window_length}-Year Average")
    avg_temps = data.set_index('month').reindex(range(1, 13))['2m_temperature']

    # Draw the previous curve with a faded grey effect
    faded_line, = ax.plot(months, avg_temps.values, 'o-', color='grey', alpha=0.1)
    faded_lines.append(faded_line)

    # Update the main line with the current frame data in red
    line.set_ydata(avg_temps.values)

    # Calculate differences from cumulative mean (up to the previous frame)
    if np.any(cumulative_count > 0):  # Ensure we have a previous mean to compare
        cumulative_mean = cumulative_sum / np.where(cumulative_count == 0, 1, cumulative_count)  # Avoid division by zero
        differences = avg_temps - cumulative_mean
        
        # Update bar heights for the difference plot
        for bar, diff in zip(bars, differences):
            bar.set_height(diff)
    
    # Update cumulative sum and count with current values (for future frames)
    cumulative_sum += avg_temps.values
    cumulative_count += 1
    
    return line, text, *faded_lines, *bars

# Create the animation frames
frames = [(window, data) for window, data in monthly_averages.items()]

# Set up the animation with modified speed and no repeat
ani = FuncAnimation(fig, update, frames=frames, blit=True, repeat=False, interval=200)  # Adjust interval to control speed

# Save the animation as a GIF
output_file = "temperature_trends.gif"
ani.save(output_file, writer=PillowWriter(fps=10))  # Adjust fps to control animation speed in GIF

plt.tight_layout(rect=[0, 0.03, 1, 0.95])  # Adjust layout for titles
plt.show()
