from django.shortcuts import render
from .forms import CustomAuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
import pandas as pd
from .code import new_attendance, extract_attendance_times
import tempfile
from django.http import HttpResponse
import io
import json
import os
import matplotlib.pyplot as plt
import base64
import openpyxl


# Create your views here.
def home(request):
    return render(request, 'home.html' )

class CustomLoginView(LoginView):
    # Use the standard registration path so the template under
    # core/templates/registration/login.html is picked up.
    template_name = 'registration/login.html'
    authentication_form = CustomAuthenticationForm
    redirect_authenticated_user = True  # if already logged in redirect to LOGIN_REDIRECT_URL

    def form_valid(self, form):
        # Standard login first
        resp = super().form_valid(form)
        remember = form.cleaned_data.get('remember_me')
        if remember:
            # 2 weeks expiry
            self.request.session.set_expiry(1209600)  # seconds
        else:
            # expire when user closes browser
            self.request.session.set_expiry(0)
        return resp

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')  # or rely on LOGOUT_REDIRECT_URL in settings

def dashboard(request):
    # Initialize variables to avoid UnboundLocalError
    daily_table_html = ""
    totals_table_html = ""
    error_message = None

    if request.method == "POST":
        try:
            # Upload Excel file
            new_record = request.FILES["my_record"]

            # Read sheets
            df_record = pd.read_excel(new_record, sheet_name="Logs")
            df_names = pd.read_excel(new_record, sheet_name="Summary")
            df_names['number'] = range(1, len(df_names) + 1)
            scor = df_names.loc[df_names['number'] > 3]
            names = scor['Unnamed: 1']

            # Process data
            cleaned_df = new_attendance(df_record)
            daily_summary, staff_totals = extract_attendance_times(cleaned_df, names)

            # Optional: print for debugging
            print(daily_summary.head(5))
            print(staff_totals.head(5))

            # Save JSON for session if needed
            tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            staff_totals.to_json(tmp_file, orient="split")
            tmp_file.close()
            request.session["cleaned_totals"] = tmp_file.name

            tmp_fil = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            daily_summary.to_json(tmp_fil, orient="split")
            tmp_fil.close()
            request.session["cleaned_daily"] = tmp_fil.name

            # Generate HTML tables with Bootstrap classes
            daily_table_html = daily_summary.to_html(
                classes="table table-striped table-bordered table-hover",
                index=False,
                border=0
            )
            totals_table_html = staff_totals.to_html(
                classes="table table-striped table-bordered table-hover",
                index=False,
                border=0
            )

        except Exception as e:
            error_message = f"An error occurred while processing the files: {str(e)}"

    # Render template with tables
    return render(
        request,
        'temp/dashboard.html',
        {
            'daily_table_html': daily_table_html,
            'totals_table_html': totals_table_html,
            'error': error_message
        }
    )


def daily(request):
    report_json = request.session.get("cleaned_daily")

    if not report_json:
        return render(request, "temp/daily.html", {
            "message": "No results available. Please upload files."
        })

    from io import StringIO
    import os
    try:
        if isinstance(report_json, str) and os.path.exists(report_json):
            report = pd.read_json(report_json, orient="split")
        else:
            report = pd.read_json(StringIO(report_json), orient="split")
    except Exception as e:
        print(f"Error loading B daily report: {e}")
        return render(request, "temp/daily.html", {"message": f"Error loading report: {e}"})

    print("DEBUG: Report shape =", report.shape)

    

    table_html = report.to_html(classes="table table-bordered", index=False)
    return render(request, "temp/daily.html", {"table": table_html})

def monthly(request):
    report_json = request.session.get("cleaned_totals")

    if not report_json:
        return render(request, "temp/monthly.html", {
            "message": "No results available. Please upload files."
        })

    from io import StringIO
    import os
    try:
        if isinstance(report_json, str) and os.path.exists(report_json):
            report = pd.read_json(report_json, orient="split")
        else:
            report = pd.read_json(StringIO(report_json), orient="split")
    except Exception as e:
        print(f"Error loading B monthly report: {e}")
        return render(request, "temp/monthly.html", {"message": f"Error loading report: {e}"})

    print("DEBUG: Report shape =", report.shape)

    

    table_html = report.to_html(classes="table table-bordered", index=False)
    return render(request, "temp/monthly.html", {"table": table_html})

def download_results(request):
    report_json = request.session.get("cleaned_daily")
    print ("DEBUG: Retrieved report_json from session:", report_json)

    if not report_json:
        return HttpResponse("No results to download.", status=400)
    from io import StringIO
    import os
            
    try:
        if isinstance(report_json, str) and os.path.exists(report_json):
            report = pd.read_json(report_json, orient="split")
        else:
            report = pd.read_json(StringIO(report_json), orient="split")
    except Exception as e:
        print(f"Error loading B monthly report: {e}")
        return render(request, "temp/monthly.html", {"message": f"Error loading report: {e}"})

    # Save to in-memory buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        report.to_excel(writer, index=False, sheet_name="Daily Attendance Report")
    buffer.seek(0)

    # Send as downloadable response
    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Daily_attendance_report.xlsx"'
    return response

def download_monthly_results(request):
    report_json = request.session.get("cleaned_totals")
    print ("DEBUG: Retrieved report_json from session:", report_json)

    if not report_json:
        return HttpResponse("No results to download.", status=400)
    from io import StringIO
    import os
            
    try:
        if isinstance(report_json, str) and os.path.exists(report_json):
            report = pd.read_json(report_json, orient="split")
        else:
            report = pd.read_json(StringIO(report_json), orient="split")
    except Exception as e:
        print(f"Error loading B monthly report: {e}")
        return render(request, "temp/monthly.html", {"message": f"Error loading report: {e}"})

    # Save to in-memory buffer
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        report.to_excel(writer, index=False, sheet_name="Monthly Attendance Report")
    buffer.seek(0)

    # Send as downloadable response
    response = HttpResponse(
        buffer,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="Montly_attendance_report.xlsx"'
    return response