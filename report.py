import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec


# Step 1: Connect to the Database
def connect_to_db():
    conn = sqlite3.connect('service_monitoring.db')  # For SQLite, use 'your_database.db'
    return conn


# Step 2: Fetch Data from the Database
def fetch_ping_data(conn, start_timestamp, end_timestamp):
    query = """
    SELECT host, timestamp, time_ms
    FROM ping_results
    WHERE timestamp BETWEEN ? AND ?
    ORDER BY timestamp
    """
    df = pd.read_sql_query(query, conn, params=(start_timestamp, end_timestamp))
    return df


def fetch_hsts_data(conn):
    query = """
    SELECT url, status
    FROM hsts_results
    """
    df = pd.read_sql_query(query, conn)
    return df


def fetch_forward_secrecy_data(conn):
    query = """
    SELECT hostname, status
    FROM forward_secrecy_results
    """
    df = pd.read_sql_query(query, conn)
    return df


# Step 3: Calculate Statistics (Min, Max, Avg, Uptime %)
def calculate_statistics(df):
    stats = []

    for host in df['host'].unique():
        host_data = df[df['host'] == host]

        # Calculate min, max, and average response time
        min_time = host_data['time_ms'].min()
        max_time = host_data['time_ms'].max()
        avg_time = host_data['time_ms'].mean()

        # Calculate uptime percentage
        total_pings = len(host_data)
        successful_pings = len(host_data[host_data['time_ms'] > 0])
        uptime_percentage = (successful_pings / total_pings) * 100

        stats.append({
            'Host': host,
            'Min (ms)': min_time,
            'Max (ms)': max_time,
            'Avg (ms)': avg_time,
            'Uptime (%)': uptime_percentage
        })

    stats_df = pd.DataFrame(stats)
    return stats_df


# Step 4: Calculate HSTS Percentage for Each URL

# Step 4: Calculate HSTS Percentage for Each URL
def calculate_hsts_percentage(hsts_df):
    total_requests = hsts_df.groupby('url').size().reset_index(name='Total Requests')
    print(total_requests)
    hsts_percentage = hsts_df.groupby('url')['status'].value_counts(normalize=True).unstack().fillna(0) * 100
    hsts_percentage = hsts_percentage.reset_index()

    hsts_percentage.columns = ['URL','HSTS Disabled (%)', 'HSTS Enabled (%)','Error (%)']
    hsts_percentage = hsts_percentage.merge(total_requests, left_on='URL', right_on='url', how='left').drop(columns='url')

    # hsts_percentage ['Total Requests']= hsts_df.groupby('url').size()
    hsts_percentage['HSTS Enabled (%)'] = hsts_percentage['HSTS Enabled (%)'].astype(float)
    hsts_percentage['HSTS Disabled (%)'] = hsts_percentage['HSTS Disabled (%)'].astype(float)
    print(hsts_percentage)
    return hsts_percentage

def calculate_forward_secrecy_percentage(raw_data):
    total_requests = raw_data.groupby('hostname').size().reset_index(name='Total Requests')
    forword_secrecy_percentage = raw_data.groupby('hostname')['status'].value_counts(normalize=True).unstack().fillna(0) * 100
    forword_secrecy_percentage = forword_secrecy_percentage.reset_index()

    forword_secrecy_percentage.columns = ['Hostname','Forword Secrecy Disabled (%)', 'Forword Secrecy Enabled (%)','Error (%)']
    forword_secrecy_percentage = forword_secrecy_percentage.merge(total_requests, left_on='Hostname',right_on='hostname', how='left').drop(columns='hostname')

    forword_secrecy_percentage['Forword Secrecy Enabled (%)'] = forword_secrecy_percentage['Forword Secrecy Enabled (%)'].astype(float)
    forword_secrecy_percentage['Forword Secrecy Disabled (%)'] = forword_secrecy_percentage['Forword Secrecy Disabled (%)'].astype(float)
    return forword_secrecy_percentage
# Step 5: Plot Bar Chart for HSTS Percentages
def plot_hsts_percentage(hsts_percentage_df):
    fig, ax = plt.subplots(figsize=(12, 8))

    # Define bar width
    bar_width = 0.5
    index = range(len(hsts_percentage_df))

    # Plot stacked bar chart
    ax.bar(index, hsts_percentage_df['HSTS Enabled (%)'], bar_width, label='HSTS Enabled', color='#ff9999')
    ax.bar(index, hsts_percentage_df['HSTS Disabled (%)'], bar_width, bottom=hsts_percentage_df['HSTS Enabled (%)'],
           label='HSTS Disabled', color='#66b3ff')
    ax.bar(index, hsts_percentage_df['Error (%)'], bar_width,
           bottom=hsts_percentage_df['HSTS Enabled (%)'] + hsts_percentage_df['HSTS Disabled (%)'],
           label='Connection Errors', color='#ffcc99')

    # Customize the plot
    ax.set_xlabel('URL')
    ax.set_ylabel('Percentage (%)')
    ax.set_title('HSTS Status Percentage for Each URL')
    ax.set_xticks(index)
    ax.set_xticklabels(hsts_percentage_df['URL'], rotation=0, ha='right')
    ax.legend()

    plt.tight_layout()
    plt.show()

# Step 6: Create Pie Charts for Each URL's HSTS Status



# Step 7: Process and Plot the Data
def plot_combined(df, stats_df, hsts_df, forward_secrecy_df,hsts_percentage_df,forward_secrecy_percentage_df):
    fig = plt.figure(figsize=(20,20))
    gs = GridSpec(6,1, height_ratios=[1,.25,1,.25,1,.25], width_ratios=[2])

    # Line plot for uptime monitoring
    ax1 = plt.subplot(gs[0, 0])
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    for host in df['host'].unique():
        host_data = df[df['host'] == host]
        ax1.plot(host_data['timestamp'], host_data['time_ms'], marker='o', linestyle='-', label=f'Host {host}')

    ax1.set_xlabel('Timestamp')
    ax1.set_ylabel('Response Time (ms)')
    ax1.set_title('SLO 1 \nUptime Monitoring')
    ax1.legend(title='Host')

    # Statistics table
    ax2 = plt.subplot(gs[1, 0])
    ax2.axis('off')
    table_data = stats_df.values
    column_labels = stats_df.columns
    table = ax2.table(cellText=table_data, colLabels=column_labels, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    ## HSTS chart
    bar_width = 0.5
    index = range(len(hsts_percentage_df))
    ax5 = plt.subplot(gs[2,0])
    # Plot stacked bar chart
    ax5.bar(index, hsts_percentage_df['HSTS Enabled (%)'], bar_width, label='HSTS Enabled', color='#ff9999')
    ax5.bar(index, hsts_percentage_df['HSTS Disabled (%)'], bar_width, bottom=hsts_percentage_df['HSTS Enabled (%)'],
           label='HSTS Disabled', color='#66b3ff')
    ax5.bar(index, hsts_percentage_df['Error (%)'], bar_width,
           bottom=hsts_percentage_df['HSTS Enabled (%)'] + hsts_percentage_df['HSTS Disabled (%)'],
           label='Connection Errors', color='#ffcc99')

    # Customize the plot
    ax5.set_xlabel('URL')
    ax5.set_ylabel('Percentage (%)')
    ax5.set_title('SLO 2 (Http Header) \nHSTS Status Percentage for Each URL')
    ax5.set_xticks(index)
    ax5.set_xticklabels(hsts_percentage_df['URL'], rotation=0, ha='right')
    ax5.legend()

    #hsts stats table

    ax4 = plt.subplot(gs[3,0])
    ax4.axis('off')
    table_data=hsts_percentage_df.values
    column_labels=hsts_percentage_df.columns
    table = ax4.table(cellText=table_data, colLabels=column_labels, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)



    ## Forword Secrecy chart
    bar_width = 0.5
    print(forward_secrecy_percentage_df)
    index = range(len(forward_secrecy_percentage_df))
    ax6 = plt.subplot(gs[4,0])
    # Plot stacked bar chart
    ax6.bar(index, forward_secrecy_percentage_df['Forword Secrecy Enabled (%)'], bar_width, label='Forword Secrecy Enabled', color='#ff9999')
    ax6.bar(index, forward_secrecy_percentage_df['Forword Secrecy Disabled (%)'], bar_width, bottom=forward_secrecy_percentage_df['Forword Secrecy Enabled (%)'],
           label='Forword Secrecy Disabled', color='#66b3ff')
    ax6.bar(index, forward_secrecy_percentage_df['Error (%)'], bar_width,
           bottom=forward_secrecy_percentage_df['Forword Secrecy Enabled (%)'] + forward_secrecy_percentage_df['Forword Secrecy Disabled (%)'],
           label='Connection Errors', color='#ffcc99')

    # Customize the plot
    ax6.set_xlabel('URL')
    ax6.set_ylabel('Percentage (%)')
    ax6.set_title('Forword Secrecy Status Percentage for Each URL')
    ax6.set_xticks(index)
    ax6.set_xticklabels(forward_secrecy_percentage_df['Hostname'], rotation=0, ha='right')
    ax6.legend()

    #hsts stats table

    ax7 = plt.subplot(gs[5,0])
    ax7.axis('off')
    table_data=forward_secrecy_percentage_df.values

    column_labels=forward_secrecy_percentage_df.columns
    print(column_labels)
    table = ax7.table(cellText=table_data, colLabels=column_labels, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    # Forward Secrecy pie chart


    # ax3 = plt.subplot(gs[1, 1])
    # if not forward_secrecy_df.empty:
    #     unique_hostnames = forward_secrecy_df['hostname'].unique()
    #     for hostname in unique_hostnames:
    #         hostname_data = forward_secrecy_df[forward_secrecy_df['hostname'] == hostname]
    #         sizes = hostname_data['status'].value_counts()
    #         labels = ['Enabled' if status == '1' else 'Disabled' for status in sizes.index]
    #         colors = ['#99ff99' if status == '1' else '#ffcc99' for status in sizes.index]
    #
    #         ax3.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=140)
    #         ax3.set_title(f'Forward Secrecy Status Distribution for {hostname}')

    plt.tight_layout()
    plt.savefig("Report.pdf", format="pdf", bbox_inches="tight")
    plt.show()


def main():
    start_timestamp = input("Enter start timestamp (YYYY-MM-DD HH:MM:SS): ")
    end_timestamp = input("Enter end timestamp (YYYY-MM-DD HH:MM:SS): ")

    conn = connect_to_db()  # Connect to the database
    try:
        df = fetch_ping_data(conn, start_timestamp, end_timestamp)  # Ping data
        stats_df = calculate_statistics(df)  # Statistics
        hsts_df = fetch_hsts_data(conn)  # HSTS data
        forward_secrecy_df = fetch_forward_secrecy_data(conn)  # Forward Secrecy data

        # Calculate HSTS percentage
        hsts_percentage_df = calculate_hsts_percentage(hsts_df)
        # Plot bar chart for HSTS percentages
        #plot_hsts_percentage(hsts_percentage_df)
        # Calculate HSTS percentage

        forward_secrecy_percentage_df = calculate_forward_secrecy_percentage(forward_secrecy_df)

        # Plot bar chart for HSTS percentages

        #plot_forward_secrecy_percentage(forward_secrecy_percentage_df)
        # Plot combined results
        plot_combined(df, stats_df, hsts_df, forward_secrecy_df,hsts_percentage_df,forward_secrecy_percentage_df)  # Plot all data combined

        # Plot separate pie charts for each URL's HSTS status


    finally:
        conn.close()  # Ensure the connection is closed


# Execute the program
if __name__ == "__main__":
    main()

# 2024-08-14 20:00:00
# 2024-08-14 21:00:00
