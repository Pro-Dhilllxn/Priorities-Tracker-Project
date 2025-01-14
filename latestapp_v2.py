import streamlit as st
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import pytz  # For timezone conversion

# Set the timezone to IST
IST = pytz.timezone('Asia/Kolkata')

def get_gsheet_credentials():
    """Create credentials object from Streamlit secrets"""
    credentials = {
        "type": st.secrets["gcp_service_account"]["type"],
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
        "token_uri": st.secrets["gcp_service_account"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"],
        "universe_domain": st.secrets["gcp_service_account"]["universe_domain"]
    }
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    return Credentials.from_service_account_info(credentials, scopes=scopes)

def load_data(sheet_name):
    """Load and process data from Google Sheets"""
    creds = get_gsheet_credentials()
    client = gspread.authorize(creds)
    sheet = client.open("Priorities_Tracker_Database_Spreadsheet").worksheet(sheet_name)
    
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    
    # Convert timestamp to datetime and handle timezone
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])
        if df['Timestamp'].dt.tz is None:  # Check if timezone-naive
            df['Timestamp'] = df['Timestamp'].dt.tz_localize('UTC').dt.tz_convert(IST)
        else:  # If already timezone-aware, convert to IST
            df['Timestamp'] = df['Timestamp'].dt.tz_convert(IST)
    
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        if df['Date'].dt.tz is None:  # Check if timezone-naive
            df['Date'] = df['Date'].dt.tz_localize(IST)
        else:  # If already timezone-aware, convert to IST
            df['Date'] = df['Date'].dt.tz_convert(IST)
    
    return df

def format_time(seconds):
    """Convert seconds to HH:MM:SS format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

def calculate_streaks(df):
    """Calculate activity streaks by priority"""
    if df.empty:
        return {}
    
    df['Date'] = df['Timestamp'].dt.date
    streaks = {}
    
    for priority in df['Priority'].unique():
        priority_df = df[df['Priority'] == priority]
        priority_dates = sorted(priority_df['Date'].unique())
        
        current_streak = 1
        max_streak = 1
        last_date = priority_dates[0]
        
        for date in priority_dates[1:]:
            if (date - last_date).days == 1:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 1
            last_date = date
            
        streaks[priority] = {
            'current': current_streak,
            'max': max_streak,
            'last_activity': max(priority_dates)
        }
    
    return streaks

def calculate_kpis(df):
    """Calculate key performance indicators from the data"""
    kpis = {}
    
    # Total hours
    kpis['total_hours'] = df['Duration'].sum()
    
    # Calculate date range and overall average
    date_range = (df['Timestamp'].max() - df['Timestamp'].min()).days + 1
    kpis['avg_hours_per_day'] = kpis['total_hours'] / date_range if date_range > 0 else 0
    
    # Calculate daily averages per priority
    df['Date'] = df['Timestamp'].dt.date
    priority_daily_totals = df.groupby(['Date', 'Priority'])['Duration'].sum().reset_index()
    priority_avgs = priority_daily_totals.groupby('Priority')['Duration'].mean()
    kpis['priority_averages'] = priority_avgs.to_dict()
    
    # Most active priority (based on total hours)
    most_active = df.groupby('Priority')['Duration'].sum().idxmax()
    kpis['most_active_priority'] = most_active
    
    return kpis

def create_timer_section():
    """Create and manage the timer interface"""
    st.subheader("Activity Timer")
    
    if 'timer_running' not in st.session_state:
        st.session_state.timer_running = False
        st.session_state.start_time = None
        st.session_state.elapsed_time = 0
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if not st.session_state.timer_running:
            if st.button("Start Timer"):
                st.session_state.timer_running = True
                st.session_state.start_time = time.time()
                st.rerun()
        else:
            if st.button("Stop Timer"):
                st.session_state.timer_running = False
                if st.session_state.start_time:
                    st.session_state.elapsed_time = time.time() - st.session_state.start_time
                st.rerun()
    
    with col2:
        if st.session_state.timer_running:
            st.session_state.elapsed_time = time.time() - st.session_state.start_time
        st.markdown(f"### {format_time(st.session_state.elapsed_time)}")
    
    return st.session_state.elapsed_time / 3600

def create_dashboard(time_filter):
    """Create the analysis dashboard"""
    st.title("Activity Analysis Dashboard")
    
    # Load data
    df = load_data("Sheet1")
    
    # Apply time filter
    if time_filter != "All time":
        days = int(time_filter.split()[1])
        cutoff_date = datetime.now(IST) - timedelta(days=days)
        df = df[df['Timestamp'] >= cutoff_date]
    
    # Calculate KPIs
    kpis = calculate_kpis(df)
    
    # Display KPIs
    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Hours Invested",
            f"{kpis['total_hours']:.1f}",
            help="Total hours spent across all priorities"
        )
    
    with col2:
        st.metric(
            "Average Hours per Day",
            f"{kpis['avg_hours_per_day']:.2f}",
            help="Average hours spent per day during the selected period"
        )
    
    with col3:
        st.metric(
            "Most Active Priority",
            kpis['most_active_priority'],
            help="Priority with the most total hours logged"
        )
    
    # Priority-specific KPIs
    st.subheader("Daily Averages by Priority")
    priority_cols = st.columns(len(kpis['priority_averages']))
    
    for col, (priority, avg) in zip(priority_cols, kpis['priority_averages'].items()):
        with col:
            st.metric(
                f"{priority}",
                f"{avg:.2f}",
                help=f"Average hours per day for {priority}"
            )
    
    # Display streaks
    st.subheader("Activity Streaks")
    streaks = calculate_streaks(df)
    for priority, streak_data in streaks.items():
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(f"{priority}", f"{streak_data['current']} days")
        with col2:
            st.metric("Max Streak", streak_data['max'])
        with col3:
            st.metric("Last Activity", streak_data['last_activity'].strftime("%Y-%m-%d"))
    
    # Daily Hours Trend
    st.subheader("Daily Hours Trend")
    daily_hours = df.groupby(df['Timestamp'].dt.date)['Duration'].sum().reset_index()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_hours['Timestamp'],
        y=daily_hours['Duration'],
        mode='lines+markers',
        name='Daily Hours'
    ))
    fig.add_hline(
        y=kpis['avg_hours_per_day'],
        line_dash="dash",
        annotation_text=f"Average: {kpis['avg_hours_per_day']:.2f} hours"
    )
    fig.update_layout(
        title="Daily Hours vs Average",
        xaxis_title="Date",
        yaxis_title="Hours",
        hovermode='x'
    )
    st.plotly_chart(fig)
    
    # Priority Distribution
    st.subheader("Time Distribution by Priority")
    priority_data = df.groupby('Priority')['Duration'].sum().reset_index()
    fig_pie = px.pie(
        priority_data,
        values='Duration',
        names='Priority',
        title='Time Distribution by Priority'
    )
    st.plotly_chart(fig_pie)
    
    # Recent Activities
    st.subheader("Recent Activities")
    recent_activities = df.sort_values('Timestamp', ascending=False).head(5)
    st.dataframe(
        recent_activities[['Timestamp', 'Priority', 'Activity_Description', 'Duration', 'Remarks']],
        hide_index=True
    )

def create_schedule_section():
    """Create and manage the schedule interface"""
    st.title("Schedule Planner")
    
    # Load schedule data
    schedule_df = load_data("Schedule")
    
    # Filter today's schedule
    today = datetime.now(IST).date()
    today_schedule = schedule_df[pd.to_datetime(schedule_df['Date']).dt.date == today]
    
    # Format the 'Date' column to display only the date (without time)
    today_schedule['Date'] = today_schedule['Date'].dt.date
    
    # Display today's schedule
    st.subheader("Today's Schedule")
    st.dataframe(today_schedule, hide_index=True)
    
    # Add new schedule
    st.subheader("Add New Schedule")
    with st.form("schedule_form"):
        date = st.date_input("Date", value=datetime.now(IST).date())  # Set default date to today in IST
        priority = st.selectbox("Priority", ["Career", "Music", "Fitness", "Relationship", "Philosophy", "Finance"])
        planned_activity = st.text_input("Planned Activity")
        planned_duration = st.number_input("Planned Duration (in hours)", min_value=0.0, step=0.25)
        
        if st.form_submit_button("Add Schedule"):
            try:
                creds = get_gsheet_credentials()
                client = gspread.authorize(creds)
                sheet = client.open("Priorities_Tracker_Database_Spreadsheet").worksheet("Schedule")
                
                new_row = [date.strftime("%Y-%m-%d"), priority, planned_activity, planned_duration]
                sheet.append_row(new_row)
                
                st.success("Schedule added successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")

def create_plan_vs_actual_analysis(time_filter):
    """Create visualizations for planned vs actual hours"""
    st.title("Plan vs Actual Analysis")
    
    # Load data
    schedule_df = load_data("Schedule")
    logged_df = load_data("Sheet1")
    
    # Check if required columns exist
    if 'Duration' not in logged_df.columns:
        st.error("The 'Duration' column is missing in the logged activities data.")
        return
    
    if 'Planned_Duration' not in schedule_df.columns:
        st.error("The 'Planned_Duration' column is missing in the schedule data.")
        return
    
    # Convert 'Date' column to datetime in both DataFrames
    schedule_df['Date'] = pd.to_datetime(schedule_df['Date'])
    if schedule_df['Date'].dt.tz is None:
        schedule_df['Date'] = schedule_df['Date'].dt.tz_localize(IST)
    else:
        schedule_df['Date'] = schedule_df['Date'].dt.tz_convert(IST)
    
    # Convert 'Timestamp' column to datetime and handle timezone
    logged_df['Timestamp'] = pd.to_datetime(logged_df['Timestamp'])
    if logged_df['Timestamp'].dt.tz is None:
        logged_df['Timestamp'] = logged_df['Timestamp'].dt.tz_localize(IST)
    else:
        logged_df['Timestamp'] = logged_df['Timestamp'].dt.tz_convert(IST)
    
    logged_df['Date'] = logged_df['Timestamp'].dt.date
    
    # Apply time filter
    if time_filter != "All time":
        days = int(time_filter.split()[1])
        cutoff_date = (datetime.now(IST) - timedelta(days=days)).date()  # Convert to date
        logged_df = logged_df[logged_df['Date'] >= cutoff_date]
        schedule_df = schedule_df[schedule_df['Date'].dt.date >= cutoff_date]
    
    # Aggregate planned hours by date and priority
    planned_hours = schedule_df.groupby(['Date', 'Priority'])['Planned_Duration'].sum().reset_index()
    
    # Aggregate actual hours by date and priority
    actual_hours = logged_df.groupby(['Date', 'Priority'])['Duration'].sum().reset_index()
    
    # Ensure 'Date' column in actual_hours is datetime and timezone-aware
    actual_hours['Date'] = pd.to_datetime(actual_hours['Date']).dt.tz_localize(IST)
    
    # Rename 'Duration' column to 'Duration_actual' in actual_hours
    actual_hours = actual_hours.rename(columns={'Duration': 'Duration_actual'})
    
    # Merge planned and actual hours
    comparison_df = pd.merge(
        planned_hours,
        actual_hours,
        on=['Date', 'Priority'],
        how='outer',  # Include all dates and priorities from both DataFrames
    )
    
    # Fill NaN values in 'Duration_actual' and 'Planned_Duration' with 0
    comparison_df['Duration_actual'] = comparison_df['Duration_actual'].fillna(0)
    comparison_df['Planned_Duration'] = comparison_df['Planned_Duration'].fillna(0)
    
    # Calculate the difference between planned and actual hours
    comparison_df['Difference'] = comparison_df['Duration_actual'] - comparison_df['Planned_Duration']
    
    # Calculate KPIs for each priority
    kpi_df = comparison_df.groupby('Priority').agg(
        Total_Planned_Hours=('Planned_Duration', 'sum'),
        Total_Actual_Hours=('Duration_actual', 'sum'),
        Total_Difference=('Difference', 'sum')
    ).reset_index()
    
    # Calculate Percentage Deviation
    kpi_df['Percentage_Deviation'] = kpi_df.apply(
        lambda row: (row['Total_Difference'] / row['Total_Planned_Hours']) * 100 if row['Total_Planned_Hours'] != 0 else 0,
        axis=1
    )
    
    # Format Percentage Deviation with a % symbol
    kpi_df['Percentage_Deviation'] = kpi_df['Percentage_Deviation'].apply(lambda x: f"{x:.2f}%")
    
    # Display KPIs
    st.subheader("Performance KPIs by Priority")
    st.dataframe(kpi_df, hide_index=True)
    
    # Visualize planned vs actual hours
    st.subheader("Planned vs Actual Hours Over Time")
    
    # Reshape the DataFrame for Plotly
    melted_df = pd.melt(
        comparison_df,
        id_vars=['Date', 'Priority'],
        value_vars=['Planned_Duration', 'Duration_actual'],
        var_name='Type',
        value_name='Hours'
    )
    
    # Create a clustered bar chart for each priority
    fig = px.bar(
        melted_df,
        x='Date',
        y='Hours',
        color='Priority',
        facet_col='Type',  # Split into separate bars for planned and actual
        barmode='group',
        labels={'Hours': 'Hours', 'Type': 'Type'},
        title="Planned vs Actual Hours by Priority",
        color_discrete_sequence=px.colors.qualitative.Plotly  # Use 6 distinct colors
    )
    st.plotly_chart(fig)

# Main app
def main():
    st.set_page_config(page_title="Activity Tracker", layout="wide")
    
    # Time period filter in the sidebar
    st.sidebar.header("Filters")
    time_filter = st.sidebar.selectbox(
        "Time Period",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
        key="time_filter"  # Unique key for this selectbox
    )
    
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Log Activity", "Analysis Dashboard", "Schedule Planner", "Plan vs Actual Analysis"])
    
    with tab1:
        st.title("Activity Logger")
        priority = st.selectbox("Priority", ["Career", "Music", "Fitness", "Relationship", "Philosophy", "Finance"])
        activity = st.text_input("Activity Description")
        
        # Add timer section
        elapsed_hours = create_timer_section()
        
        # Show manual duration input if timer is not running
        if not st.session_state.timer_running:
            duration = st.number_input("Duration (in hours)", 
                                     min_value=0.0, 
                                     step=0.25,
                                     value=float(elapsed_hours) if elapsed_hours > 0 else 0.0)
        
        remarks = st.text_area("Remarks (Optional)")
        
        if st.button("Log Activity"):
            try:
                creds = get_gsheet_credentials()
                client = gspread.authorize(creds)
                sheet = client.open("Priorities_Tracker_Database_Spreadsheet").sheet1
                
                # Convert to IST timezone
                now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
                final_duration = elapsed_hours if elapsed_hours > 0 else duration
                sheet.append_row([now, priority, activity, final_duration, remarks])
                
                # Reset timer after logging
                st.session_state.timer_running = False
                st.session_state.start_time = None
                st.session_state.elapsed_time = 0
                
                st.success("Activity logged successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    
    with tab2:
        create_dashboard(time_filter)
    
    with tab3:
        create_schedule_section()
    
    with tab4:
        create_plan_vs_actual_analysis(time_filter)

if __name__ == "__main__":
    main()