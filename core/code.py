import pandas as pd

def new_attendance(df):
    df['number'] = range(1, len(df) + 1)
    scor = df.loc[df['number'] > 4]
    # Select every 3rd row
    scores = scor.iloc[0::3].copy()
    # Build the rename mapping for DAY columns dynamically
    rename_dict = {}
    for i, col in enumerate(scores.columns):
        if i == 0:
            rename_dict[col] = 'DAY1'
        elif i <= 32:  # limit to DAY32
            rename_dict[col] = f'DAY{i+1}'
        else:
            break
        
    new_score = scores.rename(columns=rename_dict)
        
    # Add missing DAY columns if less than 32
    for i in range(1, 33):
        col_name = f'DAY{i}'
        if col_name not in new_score.columns:
            new_score[col_name] = ""
        
    # Drop the helper 'number' column
    fin = new_score.drop('number', axis=1, errors='ignore')
    final = fin.dropna(axis=1, how='all')
    
    return final

def extract_attendance_times(final_df, staff_names):
    """
    Extracts attendance times from DAY1–DAY32 columns,
    classifies them into Resume (entry) and Exit (leave),
    and returns two DataFrames:
    1. daily_summary_df → detailed day-by-day counts
    2. staff_totals_df → summarized totals per staff
    """

    # Normalize column names
    final_df.columns = [col.strip().upper() for col in final_df.columns]

    # Map each DAY column to weekday (rotates every 5 days)
    weekday_cycle = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    day_to_weekday = {f'DAY{i}': weekday_cycle[(i - 1) % 5] for i in range(1, 33)}

    # Split strings like '11:5913:1715:3012:42...' into valid time chunks
    def split_time_chunks(text):
        cleaned = str(text).replace(" ", "").replace("\n", "")
        return [
            cleaned[i:i+5] for i in range(0, len(cleaned), 5)
            if len(cleaned[i:i+5]) == 5 and ':' in cleaned[i:i+5]
        ]

    # Handle mismatch between staff_names and rows
    expected_staff = len(staff_names)
    actual_rows = len(final_df)
    if actual_rows != expected_staff:
        print(f"⚠️ WARNING: Mismatch between staff_names ({expected_staff}) and rows ({actual_rows}). Truncating to smaller length.")
        min_len = min(expected_staff, actual_rows)
        final_df = final_df.iloc[:min_len]
        staff_names = staff_names[:min_len]

    # Initialize data storage
    summary_data = {
        "Staff": [],
        "Day": [],
        "Resume Count": [],
        "Exit Count": []
    }

    # Process each column (DAY1–DAY32)
    for col in final_df.columns:
        if not col.startswith("DAY"):
            continue

        weekday = day_to_weekday.get(col)
        if weekday is None:
            continue

        for idx, cell in enumerate(final_df[col]):
            times = split_time_chunks(cell)
            resume_count = 0
            exit_count = 0
            for time in times:
                try:
                    hour = int(time[:2])
                    if 7 <= hour <= 9:
                        resume_count += 1
                    elif 16 <= hour <= 19:
                        exit_count += 1
                except (ValueError, TypeError):
                    continue

            summary_data["Staff"].append(staff_names.iloc[idx] if isinstance(staff_names, pd.Series) else staff_names[idx])
            summary_data["Day"].append(weekday)
            summary_data["Resume Count"].append(resume_count)
            summary_data["Exit Count"].append(exit_count)

    # Convert to DataFrame
    daily_summary_df = pd.DataFrame(summary_data)

    # Aggregate per staff per weekday
    daily_summary_df = (
        daily_summary_df.groupby(["Staff", "Day"], as_index=False)
        .sum()
        .sort_values(["Staff", "Day"])
        .reset_index(drop=True)
    )

    # ----------------------------
    #  Compute total summary per staff
    # ----------------------------
    staff_totals_df = (
        daily_summary_df.groupby("Staff", as_index=False)
        .agg({
            "Resume Count": "sum",
            "Exit Count": "sum"
        })
    )

    # staff_totals_df["Days Present"] = (
    #     daily_summary_df.groupby("Staff", as_index=False)
    #     .agg({"Resume Count": "sum", "Exit Count": "sum"}).apply(lambda row: max(row["Resume Count"], row["Exit Count"]), axis=1))
    staff_totals_df["Days Present"] = staff_totals_df.apply(
        lambda row: max(row["Resume Count"], row["Exit Count"]),
        axis=1
    )
    # Sort for readability
    staff_totals_df = staff_totals_df.sort_values("Staff").reset_index(drop=True)

    return daily_summary_df, staff_totals_df


import matplotlib
matplotlib.use("Agg")  # Prevent GUI
import matplotlib.pyplot as plt
import seaborn as sns
import os
from django.conf import settings
import base64
from io import BytesIO

def get_graph():
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    graph = base64.b64encode(image_png)
    graph = graph.decode('utf-8')
    buffer.close()
    return graph
def get_plot(daily_summary_df):
    plt.switch_backend('AGG')
    sns.set(style="whitegrid")
    plt.figure(figsize=(14,6))
    daily_pivot = daily_summary_df.pivot(index="Staff", columns="Day", values="Resume Count").fillna(0)
    daily_pivot.plot(kind='bar', stacked=False, figsize=(14,6))
    plt.title("Daily Resume Count per Staff")
    plt.ylabel("Resume Count")
    plt.xlabel("Staff")
    plt.xticks(rotation=45)
    plt.tight_layout()
    graph = get_graph()
    return graph






def visualize_attendance(daily_summary_df, staff_totals_df, save_plots=True):
    """
    Creates attendance charts and saves them to MEDIA_ROOT.
    Returns a dict of relative paths for use in templates.
    """
    
    # Ensure MEDIA_ROOT exists
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    # --- Daily Percent Chart ---
    fig1, ax1 = plt.subplots(figsize=(12,6))
    daily_percent = (daily_summary_df.groupby("Day")["Resume Count"].sum() / len(staff_totals_df) * 100)
    daily_percent.plot(kind='bar', color='skyblue', ax=ax1)
    ax1.set_title("Daily Attendance %")
    ax1.set_ylabel("Attendance %")
    ax1.set_xlabel("Day")
    fig1.tight_layout()
    daily_percent_file = "daily_percent.png"
    fig1.savefig(os.path.join(settings.MEDIA_ROOT, daily_percent_file))
    plt.close(fig1)
    paths["daily_percent_path"] = daily_percent_file

    # --- Staff Performance Chart ---
    fig2, ax2 = plt.subplots(figsize=(12,6))
    staff_totals_df.set_index("Staff")[["Resume Count","Exit Count"]].plot(
        kind='bar', stacked=True, color=['skyblue','salmon'], ax=ax2
    )
    ax2.set_title("Staff Total Resume & Exit")
    ax2.set_ylabel("Count")
    fig2.tight_layout()
    staff_perf_file = "staff_performance.png"
    fig2.savefig(os.path.join(settings.MEDIA_ROOT, staff_perf_file))
    plt.close(fig2)
    paths["staff_performance_path"] = staff_perf_file

    # --- Absentee Heatmap ---
    fig3, ax3 = plt.subplots(figsize=(12,6))
    heatmap_df = daily_summary_df.pivot(index="Staff", columns="Day", values="Resume Count").fillna(0)
    sns.heatmap(heatmap_df, annot=True, fmt="g", cmap="YlGnBu", ax=ax3)
    ax3.set_title("Attendance Heatmap")
    fig3.tight_layout()
    heatmap_file = "absentee_heatmap.png"
    fig3.savefig(os.path.join(settings.MEDIA_ROOT, heatmap_file))
    plt.close(fig3)
    paths["absentee_heatmap_path"] = heatmap_file

    return paths




# def visualize_attendance(daily_summary_df, staff_totals_df, request):
#     """
#     Creates attendance visualizations, saves them to temporary PNG files,
#     and stores the file paths in Django session for later use.
    
#     Parameters:
#     - daily_summary_df: DataFrame ['Staff','Day','Resume Count','Exit Count']
#     - staff_totals_df: DataFrame ['Staff','Resume Count','Exit Count','Days Present']
#     - request: Django HttpRequest object (for session)
    
#     Returns:
#     - dict of chart names to temporary file paths
#     """
    
#     sns.set(style="whitegrid")
#     chart_paths = {}

#     # -----------------------
#     # 1️⃣ Daily Resume per staff
#     # -----------------------
#     daily_pivot = daily_summary_df.pivot(index="Staff", columns="Day", values="Resume Count").fillna(0)
#     fig1, ax1 = plt.subplots(figsize=(14,6))
#     daily_pivot.plot(kind='bar', stacked=False, ax=ax1)
#     ax1.set_title("Daily Resume Count per Staff")
#     ax1.set_ylabel("Resume Count")
#     ax1.set_xticklabels(ax1.get_xticklabels(), rotation=45)
#     plt.tight_layout()
    
#     tmp1 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#     fig1.savefig(tmp1.name, bbox_inches='tight')
#     plt.close(fig1)
#     chart_paths["daily_percent_path"] = tmp1.name
#     request.session["daily_percent_path"] = tmp1.name

#     # -----------------------
#     # 2️⃣ Daily Exit per staff
#     # -----------------------
#     daily_exit_pivot = daily_summary_df.pivot(index="Staff", columns="Day", values="Exit Count").fillna(0)
#     fig2, ax2 = plt.subplots(figsize=(14,6))
#     daily_exit_pivot.plot(kind='bar', stacked=False, color='salmon', ax=ax2)
#     ax2.set_title("Daily Exit Count per Staff")
#     ax2.set_ylabel("Exit Count")
#     ax2.set_xticklabels(ax2.get_xticklabels(), rotation=45)
#     plt.tight_layout()
    
#     tmp2 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#     fig2.savefig(tmp2.name, bbox_inches='tight')
#     plt.close(fig2)
#     chart_paths["daily_exit_path"] = tmp2.name
#     request.session["daily_exit_path"] = tmp2.name

#     # -----------------------
#     # 3️⃣ Total Resume vs Exit per staff (stacked)
#     # -----------------------
#     fig3, ax3 = plt.subplots(figsize=(12,6))
#     staff_totals_df.set_index("Staff")[["Resume Count", "Exit Count"]].plot(
#         kind='bar', stacked=True, color=['skyblue','salmon'], ax=ax3
#     )
#     ax3.set_title("Total Resume and Exit Counts per Staff")
#     ax3.set_ylabel("Total Count")
#     ax3.set_xticklabels(ax3.get_xticklabels(), rotation=45)
#     plt.tight_layout()
    
#     tmp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#     fig3.savefig(tmp3.name, bbox_inches='tight')
#     plt.close(fig3)
#     chart_paths["staff_performance_path"] = tmp3.name
#     request.session["staff_performance_path"] = tmp3.name

#     # -----------------------
#     # 4️⃣ Attendance Heatmap
#     # -----------------------
#     heatmap_df = daily_summary_df.copy()
#     heatmap_df["Total"] = heatmap_df["Resume Count"] + heatmap_df["Exit Count"]
#     heatmap_pivot = heatmap_df.pivot(index="Staff", columns="Day", values="Total").fillna(0)
    
#     fig4, ax4 = plt.subplots(figsize=(12,6))
#     sns.heatmap(heatmap_pivot, annot=True, fmt="g", cmap="YlGnBu", cbar_kws={'label': 'Attendance Count'}, ax=ax4)
#     ax4.set_title("Heatmap of Attendance per Staff per Day (Resume + Exit)")
#     ax4.set_ylabel("Staff")
#     ax4.set_xlabel("Day")
#     plt.tight_layout()
    
#     tmp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
#     fig4.savefig(tmp4.name, bbox_inches='tight')
#     plt.close(fig4)
#     chart_paths["absentee_heatmap_path"] = tmp4.name
#     request.session["absentee_heatmap_path"] = tmp4.name

#     print("✅ Visualizations created, saved to temporary files, and paths stored in session!")
    
#     return chart_paths



