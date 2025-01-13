import streamlit as st
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import pytz

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

def load_data():
    """Load and process data from Google Sheets"""
    creds = get_gsheet_credentials()
    client = gspread.authorize(creds)
    
    # Load both activity and schedule sheets
    activity_sheet = client.open("Priorities_Tracker_Database_Spreadsheet").sheet1
    schedule_sheet = client.open("Priorities_Tracker_Database_Spreadsheet").worksheet("Schedule")
    
    activity_data = activity_sheet.get_all_records()
    schedule_data = schedule_sheet.get_all_records()
    
    activity_df = pd.DataFrame(activity_data)
    schedule_df = pd.DataFrame(schedule_data)
    
    # Convert timestamps to datetime with explicit timezone
    if not activity_df.empty:
        activity_df['Timestamp'] = pd.to_datetime(activity_df['Timestamp']).dt.tz_localize('Asia/Kolkata')
    
    if not schedule_df.empty:
        schedule_df['Date'] = pd.to_datetime(schedule_df['Date'])
    
    return activity_df, schedule_df


def create_schedule_section():
    """Create and manage the schedule interface"""
    st.subheader("Schedule Activities")
    
    schedule_type = st.radio("Schedule Type", ["One-time", "Daily", "Weekly"], key="schedule_type_radio")
    
    if schedule_type == "One-time":
        date = st.date_input("Select Date", key="schedule_date")
    elif schedule_type == "Weekly":
        day = st.selectbox("Select Day", 
                          ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                          key="schedule_day")
        start_date = st.date_input("Start Date", key="schedule_start_date")
        end_date = st.date_input("End Date", key="schedule_end_date")
    
    priority = st.selectbox("Priority", 
                          ["Career", "Music", "Fitness", "Relationship", "Philosophy", "Finance"],
                          key="schedule_priority")
    planned_activity = st.text_input("Planned Activity", key="planned_activity")
    planned_duration = st.number_input("Planned Duration (hours)", 
                                     min_value=0.0, 
                                     step=0.25,
                                     key="planned_duration")
    planned_time = st.time_input("Planned Time", key="planned_time")
    
    if st.button("Add to Schedule", key="add_schedule_button"):
        try:
            creds = get_gsheet_credentials()
            client = gspread.authorize(creds)
            schedule_sheet = client.open("Priorities_Tracker_Database_Spreadsheet").worksheet("Schedule")
            
            ist = pytz.timezone('Asia/Kolkata')
            
            if schedule_type == "One-time":
                schedule_sheet.append_row([
                    date.strftime("%Y-%m-%d"),
                    planned_time.strftime("%H:%M"),
                    priority,
                    planned_activity,
                    planned_duration,
                    schedule_type,
                    "Pending"
                ])
            elif schedule_type == "Daily":
                current_date = datetime.now(ist).date()
                for i in range(7):  # Schedule for next 7 days
                    next_date = current_date + timedelta(days=i)
                    schedule_sheet.append_row([
                        next_date.strftime("%Y-%m-%d"),
                        planned_time.strftime("%H:%M"),
                        priority,
                        planned_activity,
                        planned_duration,
                        schedule_type,
                        "Pending"
                    ])
            else:  # Weekly
                current_date = start_date
                while current_date <= end_date:
                    if current_date.strftime("%A") == day:
                        schedule_sheet.append_row([
                            current_date.strftime("%Y-%m-%d"),
                            planned_time.strftime("%H:%M"),
                            priority,
                            planned_activity,
                            planned_duration,
                            schedule_type,
                            "Pending"
                        ])
                    current_date += timedelta(days=1)
            
            st.success("Schedule added successfully!")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


def analyze_schedule_vs_actual(activity_df, schedule_df):
    """Analyze planned vs actual activities"""
    if schedule_df.empty:
        st.warning("No scheduled activities found. Please add some activities to your schedule.")
        return
        
    if activity_df.empty:
        st.warning("No logged activities found. Please log some activities to see the comparison.")
        return
    
    # Standardize date handling
    activity_df = activity_df.copy()
    schedule_df = schedule_df.copy()
    
    # Convert activity timestamps to date only for comparison
    activity_df['Date'] = activity_df['Timestamp'].dt.tz_localize(None).dt.date
    
    # Convert schedule dates to date only for comparison
    schedule_df['Date'] = pd.to_datetime(schedule_df['Date']).dt.date
    
    # Group actual activities by date and priority
    actual_activities = activity_df.groupby(['Date', 'Priority'])['Duration'].sum().reset_index()
    
    # Group scheduled activities by date and priority
    planned_activities = schedule_df.groupby(['Date', 'Priority'])['Planned_Duration'].sum().reset_index()
    
    # Merge planned and actual
    comparison = pd.merge(
        planned_activities,
        actual_activities,
        on=['Date', 'Priority'],
        how='outer'
    ).fillna(0)
    
    # Sort by date
    comparison = comparison.sort_values('Date')
    
    # Calculate completion rate safely
    comparison['Completion_Rate'] = 0.0
    mask = comparison['Planned_Duration'] > 0
    comparison.loc[mask, 'Completion_Rate'] = (
        (comparison.loc[mask, 'Duration'] / comparison.loc[mask, 'Planned_Duration'] * 100)
        .round(2)
    )
    
    # Calculate statistics
    total_planned = comparison['Planned_Duration'].sum()
    total_actual = comparison['Duration'].sum()
    overall_completion = (total_actual / total_planned * 100).round(2) if total_planned > 0 else 0
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Planned Hours", f"{total_planned:.1f}")
    with col2:
        st.metric("Total Actual Hours", f"{total_actual:.1f}")
    with col3:
        st.metric("Overall Completion Rate", f"{overall_completion}%")
    
    # Create visualization
    if not comparison.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=comparison['Date'],
            y=comparison['Planned_Duration'],
            name='Planned Hours',
            marker_color='#AED6F1'
        ))
        fig.add_trace(go.Bar(
            x=comparison['Date'],
            y=comparison['Duration'],
            name='Actual Hours',
            marker_color='#2E86C1'
        ))
        
        fig.update_layout(
            barmode='group',
            title='Planned vs Actual Hours by Date',
            xaxis_title="Date",
            yaxis_title="Hours",
            height=400,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display detailed comparison
        display_df = comparison.copy()
        display_df['Date'] = display_df['Date'].astype(str)
        display_df = display_df.sort_values('Date', ascending=False)
        st.dataframe(display_df, use_container_width=True, hide_index=True)


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
    
    df['Date'] = pd.to_datetime(df['Timestamp']).dt.date
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
    """Create and manage the timer interface."""
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
        else:
            if st.button("Stop Timer"):
                st.session_state.timer_running = False
                st.session_state.elapsed_time += time.time() - st.session_state.start_time
                st.session_state.start_time = None
    
    with col2:
        elapsed_time = st.session_state.elapsed_time
        if st.session_state.timer_running:
            elapsed_time += time.time() - st.session_state.start_time
        st.markdown(f"### {format_time(elapsed_time)}")
    
    return elapsed_time / 3600

def create_dashboard():
    """Create the analysis dashboard"""
    st.title("Activity Analysis Dashboard")
    
    # Load data
    df, schedule_df = load_data()
    
    if df.empty:
        st.warning("No data available to display")
        return
    
    # Time period filter
    st.sidebar.header("Filters")
    time_filter = st.sidebar.selectbox(
        "Time Period",
        ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
        key="dashboard_time_filter"
    )
    
    # Apply time filter
    if time_filter != "All time":
        days = int(time_filter.split()[1])
        cutoff_date = pd.Timestamp.now(tz='Asia/Kolkata') - pd.Timedelta(days=days)
        df = df[df['Timestamp'].dt.tz_localize(None) >= cutoff_date.tz_localize(None)]
    
    # Calculate KPIs
    kpis = calculate_kpis(df)
    
    # 1. Main KPIs Section
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
    
    # 2. Priority-specific Averages
    if 'priority_averages' in kpis and kpis['priority_averages']:
        st.subheader("Daily Averages by Priority")
        priority_cols = st.columns(len(kpis['priority_averages']))
        
        for col, (priority, avg) in zip(priority_cols, kpis['priority_averages'].items()):
            with col:
                st.metric(
                    f"{priority}",
                    f"{avg:.2f} hrs/day",
                    help=f"Average daily hours for {priority}"
                )
    
    # 3. Activity Streaks
    st.subheader("Activity Streaks")
    streaks = calculate_streaks(df)
    if streaks:
        for priority, streak_data in streaks.items():
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{priority}", f"{streak_data['current']} days")
            with col2:
                st.metric("Max Streak", f"{streak_data['max']} days")
            with col3:
                st.metric("Last Activity", streak_data['last_activity'].strftime("%Y-%m-%d"))
    
    # 4. Daily Hours Trend
    st.subheader("Daily Hours Trend")
    if not df.empty:
        daily_hours = df.groupby(df['Timestamp'].dt.date)['Duration'].sum().reset_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_hours['Timestamp'],
            y=daily_hours['Duration'],
            mode='lines+markers',
            name='Daily Hours',
            line=dict(color='#2E86C1')
        ))
        if kpis['avg_hours_per_day'] > 0:
            fig.add_hline(
                y=kpis['avg_hours_per_day'],
                line_dash="dash",
                line=dict(color='#E74C3C'),
                annotation_text=f"Average: {kpis['avg_hours_per_day']:.2f} hours"
            )
        fig.update_layout(
            title="Daily Hours vs Average",
            xaxis_title="Date",
            yaxis_title="Hours",
            hovermode='x',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True, key="daily_hours_trend")
    
    # 5. Priority Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Time Distribution by Priority")
        if not df.empty:
            priority_data = df.groupby('Priority')['Duration'].sum().reset_index()
            fig_pie = px.pie(
                priority_data,
                values='Duration',
                names='Priority',
                title='Distribution of Hours',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True, key="priority_distribution_pie")
    
    with col2:
        st.subheader("Priority Breakdown")
        if not df.empty:
            priority_stats = df.groupby('Priority').agg({
                'Duration': ['sum', 'mean', 'count']
            }).round(2)
            priority_stats.columns = ['Total Hours', 'Avg Hours', 'Activities']
            priority_stats = priority_stats.sort_values('Total Hours', ascending=False)
            st.dataframe(priority_stats, use_container_width=True)
    
    # 6. Schedule vs Actual Analysis
    st.subheader("Schedule Adherence")
    analyze_schedule_vs_actual(df, schedule_df, chart_key_suffix="dashboard")

    
    # 7. Recent Activities
    st.subheader("Recent Activities")
    if not df.empty:
        recent_activities = df.sort_values('Timestamp', ascending=False).head(5)
        recent_activities['Timestamp'] = recent_activities['Timestamp'].dt.strftime('%Y-%m-%d %H:%M')
        st.dataframe(
            recent_activities[['Timestamp', 'Priority', 'Activity_Description', 'Duration', 'Remarks']],
            hide_index=True,
            use_container_width=True
        )



# Main app
def main():
    st.set_page_config(page_title="Activity Tracker", layout="wide")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Log Activity", "Schedule", "Analysis Dashboard"])
    
    with tab1:
        st.title("Activity Logger")
        priority = st.selectbox("Priority", 
                              ["Career", "Music", "Fitness", "Relationship", "Philosophy", "Finance"],
                              key="log_priority")  # Added unique key
        activity = st.text_input("Activity Description", key="log_activity")  # Added unique key
        
        elapsed_hours = create_timer_section()
        
        if not st.session_state.timer_running:
            duration = st.number_input("Duration (in hours)", 
                                     min_value=0.0, 
                                     step=0.25,
                                     value=float(elapsed_hours) if elapsed_hours > 0 else 0.0,
                                     key="log_duration")  # Added unique key
        
        remarks = st.text_area("Remarks (Optional)", key="log_remarks")  # Added unique key
        
        if st.button("Log Activity", key="log_activity_button"):  # Added unique key
            try:
                creds = get_gsheet_credentials()
                client = gspread.authorize(creds)
                sheet = client.open("Priorities_Tracker_Database_Spreadsheet").sheet1
                
                # Use IST timezone for timestamp
                ist = pytz.timezone('Asia/Kolkata')
                now = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
                
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
        create_schedule_section()
    
    with tab3:
        activity_df, schedule_df = load_data()
        create_dashboard()
        analyze_schedule_vs_actual(activity_df, schedule_df, chart_key_suffix="tab3")



if __name__ == "__main__":
    main()

