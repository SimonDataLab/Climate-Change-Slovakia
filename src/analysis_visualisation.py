import xarray as xr
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
import matplotlib.cm as cm
import matplotlib.colors as mcolors

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
        df['valid_time'] = pd.to_datetime(df['valid_time'], format='%Y%m%d')
        df = df[['valid_time', 'latitude', 'longitude', '2m_temperature']]
        all_data.append(df)

# Combine all yearly data into one DataFrame
full_data = pd.concat(all_data)

# Extract year and month for grouping
full_data['year'] = full_data['valid_time'].dt.year
full_data['month'] = full_data['valid_time'].dt.month

# Group by year and month to calculate monthly averages per location
monthly_data = full_data.groupby(['year', 'month', 'latitude', 'longitude']).mean().reset_index()

# Define the start and end year for each window sample
start_year = 1940
end_year = 2025
sample_windows = [(start, start + window_length - 1) for start in range(start_year, end_year - window_length + 1)]

# Calculate moving averages for the main window
monthly_averages = {}
for start, end in sample_windows:
    sample = monthly_data[(monthly_data['year'] >= start) & (monthly_data['year'] <= end)]
    monthly_avg = sample.groupby(['month'])['2m_temperature'].mean().reset_index()
    monthly_averages[f"{start}-{end}"] = monthly_avg

# Initialize arrays to store cumulative sum and count for running mean calculation
cumulative_sum = np.zeros(12)
cumulative_count = np.zeros(12)

# Prepare data for animation
fig, (ax, ax_diff) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})
fig.suptitle(f"Warming Slovakia: {window_length}-Year Temperature Normals ({start_year}-{end_year-1})",
             fontsize=16, fontweight="bold", color="darkred")

# Main plot settings
ax.set_ylabel("Average Temperature (°C)")
months = range(1, 13)
ax.set_ylim(-8, 23)
ax.grid(True)
month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
ax.set_xticks(months)
ax.set_xticklabels(month_labels)

# Secondary plot for differences
ax_diff.set_ylabel("Difference from Cumulative Mean (°C)")
ax_diff.set_ylim(-2, 8)
ax_diff.grid(True)
ax_diff.set_xticks(months)
ax_diff.set_xticklabels(month_labels)

# Initialize plots
line, = ax.plot(months, np.zeros(12), 'o-', color='red')
cumulative_line, = ax.plot(months, np.zeros(12), '--', color='black', alpha=0.3)
text = ax.text(0.5, 0.95, "", transform=ax.transAxes, ha="center")
bars = ax_diff.bar(months, np.zeros(12), color='gray', alpha=0.6)
faded_lines = []

# Colormap normalization
norm = mcolors.Normalize(vmin=-6, vmax=6)
cmap = cm.get_cmap('coolwarm')

def update(frame):
    global cumulative_sum, cumulative_count
    window, data = frame

    if window == list(monthly_averages.keys())[0]:
        for faded_line in faded_lines:
            faded_line.remove()
        faded_lines.clear()

    text.set_text(f"{window} {window_length}-Year Average")
    avg_temps = data.set_index('month').reindex(range(1, 13))['2m_temperature']

    faded_line, = ax.plot(months, avg_temps.values, 'o-', color='grey', alpha=0.1)
    faded_lines.append(faded_line)
    line.set_ydata(avg_temps.values)

    # Annotate "flat" months
    for ann in ax.texts[1:]:
        ann.remove()

    if np.any(cumulative_count > 0):
        cumulative_mean = cumulative_sum / np.where(cumulative_count == 0, 1, cumulative_count)
        cumulative_line.set_ydata(cumulative_mean)
        differences = avg_temps.values - cumulative_mean
        for bar, diff in zip(bars, differences):
            bar.set_height(diff)
            bar.set_color(cmap(norm(diff)))

    cumulative_sum += avg_temps.values
    cumulative_count += 1

    return line, text, cumulative_line, *faded_lines, *bars

frames = [(window, data) for window, data in monthly_averages.items()]
ani = FuncAnimation(fig, update, frames=frames, blit=True, repeat=False, interval=200)

output_file = "temperature_trends.gif"
ani.save(output_file, writer=PillowWriter(fps=10))

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()

