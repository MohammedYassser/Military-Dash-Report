import dash
from dash import html, dcc, dash_table, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import pyodbc
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

# ----------------------------
# Database connection function
# ----------------------------
def get_connection():
    return pyodbc.connect(
        f"DRIVER={os.getenv('DB_DRIVER')};"
        f"SERVER={os.getenv('DB_SERVER')};"
        f"DATABASE={os.getenv('DB_NAME')};"
        f"UID={os.getenv('DB_USER')};"
        f"PWD={os.getenv('DB_PASSWORD')};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )

# ----------------------------
# Fetch all data once
# ----------------------------
def fetch_all_data():
    conn = get_connection()
    sql = "EXEC Rpt_Personnel_Military_Data 92, null, 1, null, null, 1, 0, null, null"
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

# Load everything once at startup
all_data = fetch_all_data()

# ----------------------------
# Initialize Dash app with Bootstrap theme
# ----------------------------
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.FLATLY])
app.title = "Military Data Report"

# Dropdown options
MILITARY_OPTIONS = [
    {"label": "مؤجل", "value": "مؤجل"},
    {"label": "صغار سن", "value": "صغار سن"},
    {"label": "معفى", "value": "معفى"},
    {"label": "أدى الخدمة العسكرية", "value": "أدى الخدمة العسكرية"},
    {"label": "لم يصبه الدور", "value": "لم يصبه الدور"},
    {"label": "اجنبى", "value": "اجنبى"},
    {"label": "عدم لياقه طبيه", "value": "عدم لياقه طبيه"},
    {"label": "None", "value": "__NONE__"},
]

# ----------------------------
# Layout
# ----------------------------
app.layout = dbc.Container([

    # Fixed Navbar with logo + centered title
    dbc.Navbar(
        dbc.Container([
            html.Img(
                src="/assets/MLogo.webp",
                height="80px",  # bigger logo
                style={"marginRight": "20px"}
            ),
            dbc.NavbarBrand(
                "Personnel Military Data",
                className="mx-auto fw-bold text-primary fs-2",  # center text
                style={"textAlign": "center", "flexGrow": "1"}
            ),
        ]),
        color="light",
        className="shadow-sm fixed-top",
        style={"height": "90px"}
    ),

    # Add spacing because navbar is fixed
    html.Div(style={"marginTop": "110px"}),

    # Filters row
    dbc.Row([
        dbc.Col([
            html.Label("Enter Employee ID:", className="fw-bold"),
            dcc.Input(
                id="emp-id",
                type="number",
                debounce=True,
                placeholder="Enter ID",
                className="form-control",
                style={"marginBottom": "10px"}
            ),
        ], width=3),

        dbc.Col([
            html.Label("Filter by Military Status:", className="fw-bold"),
            dcc.Dropdown(
                id="military-filter",
                options=MILITARY_OPTIONS,
                placeholder="Select Military Status",
                clearable=True,
                className="mb-2"
            ),
        ], width=3),

        dbc.Col([
            html.Div(id="message", className="text-danger mb-3"),
        ], width=6),
    ], justify="center", className="mb-4"),

    # Sorting row
    dbc.Row([
        dbc.Col([
            html.Label("Sort by Column:", className="fw-bold"),
            dcc.Dropdown(
                id="sort-column",
                options=[{"label": col, "value": col} for col in all_data.columns],
                placeholder="Select column",
                clearable=True,
                className="mb-2"
            ),
        ], width=3),

        dbc.Col([
            html.Label("Sort Order:", className="fw-bold"),
            dcc.RadioItems(
                id="sort-order",
                options=[
                    {"label": "Ascending", "value": "asc"},
                    {"label": "Descending", "value": "desc"}
                ],
                value="asc",
                inline=True,
                className="mb-2"
            ),
        ], width=3),
    ], className="mb-4"),

    # Data table
    dbc.Row([
        dbc.Col([
            dash_table.DataTable(
                id="data-table",
                columns=[{"name": col, "id": col} for col in all_data.columns],
                data=all_data.to_dict("records"),
                style_table={
                    "overflowX": "auto",
                    "overflowY": "auto",
                    "maxHeight": "75vh",
                },
                style_cell={"textAlign": "left", "padding": "5px", "minWidth": "120px"},
                style_header={"backgroundColor": "#0d6efd", "color": "white", "fontWeight": "bold"},
                fixed_rows={"headers": True}
            )
        ], width=12)
    ])
], fluid=True, style={"backgroundColor": "#656fff"})  # light blue background

# ----------------------------
# Helper: find the actual column name for Ar_Military
# ----------------------------
def find_column(df, target_name):
    target_lower = target_name.strip().lower()
    for c in df.columns:
        if c and c.strip().lower() == target_lower:
            return c
    for c in df.columns:
        if c and target_lower in c.strip().lower():
            return c
    return None

# ----------------------------
# Callback: filtering + sorting
# ----------------------------
@app.callback(
    [Output("data-table", "data"),
     Output("data-table", "columns"),
     Output("message", "children")],
    [Input("emp-id", "value"),
     Input("military-filter", "value"),
     Input("sort-column", "value"),
     Input("sort-order", "value")]
)
def update_table(emp_id, military_status, sort_col, sort_order):
    df_filtered = all_data.copy()

    # Employee ID filter
    if emp_id is not None and str(emp_id).strip() != "":
        df_filtered = df_filtered[df_filtered["Person_Instance_ID"] == emp_id]

    # Military filter
    ar_col = find_column(df_filtered, "Ar_Military")
    if ar_col:
        ar_series = df_filtered[ar_col].astype("string").str.strip()
        if military_status:
            if military_status == "__NONE__":
                df_filtered = df_filtered[ar_series.isna() | (ar_series == "")]
            else:
                df_filtered = df_filtered[ar_series == str(military_status).strip()]
    else:
        return [], [], "⚠️ Column 'Ar_Military' not found."

    # Sorting
    if sort_col and sort_col in df_filtered.columns:
        ascending = (sort_order == "asc")
        df_filtered = df_filtered.sort_values(by=sort_col, ascending=ascending)

    if df_filtered.empty:
        return [], [], "⚠️ No data found with current filters."

    return (
        df_filtered.to_dict("records"),
        [{"name": col, "id": col} for col in df_filtered.columns],
        ""
    )

# ----------------------------
# Run app
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
