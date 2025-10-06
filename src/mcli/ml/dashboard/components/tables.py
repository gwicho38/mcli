"""Reusable table components"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Callable, Any


def display_dataframe_with_search(
    df: pd.DataFrame,
    search_columns: Optional[List[str]] = None,
    default_sort_column: Optional[str] = None,
    page_size: int = 20,
    key_prefix: str = "table"
) -> pd.DataFrame:
    """Display a dataframe with search and pagination"""

    if df.empty:
        st.info("No data available")
        return df

    # Search functionality
    if search_columns:
        search_term = st.text_input(
            "🔍 Search",
            key=f"{key_prefix}_search",
            placeholder=f"Search in: {', '.join(search_columns)}"
        )

        if search_term:
            mask = pd.Series([False] * len(df))
            for col in search_columns:
                if col in df.columns:
                    mask |= df[col].astype(str).str.contains(search_term, case=False, na=False)
            df = df[mask]

    # Sorting
    if default_sort_column and default_sort_column in df.columns:
        df = df.sort_values(by=default_sort_column, ascending=False)

    # Display count
    st.caption(f"Showing {len(df)} records")

    # Pagination
    if len(df) > page_size:
        total_pages = (len(df) - 1) // page_size + 1
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=1,
            key=f"{key_prefix}_page"
        )
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_display = df.iloc[start_idx:end_idx]
    else:
        df_display = df

    # Display dataframe
    st.dataframe(df_display, width="stretch", height=400)

    return df


def display_filterable_dataframe(
    df: pd.DataFrame,
    filter_columns: Optional[dict] = None,
    key_prefix: str = "filter"
) -> pd.DataFrame:
    """Display a dataframe with column-specific filters"""

    if df.empty:
        st.info("No data available")
        return df

    if filter_columns:
        with st.expander("🎯 Filters", expanded=False):
            cols = st.columns(len(filter_columns))

            for idx, (col_name, filter_type) in enumerate(filter_columns.items()):
                if col_name not in df.columns:
                    continue

                with cols[idx]:
                    if filter_type == "multiselect":
                        unique_values = df[col_name].unique().tolist()
                        selected = st.multiselect(
                            col_name,
                            options=unique_values,
                            default=unique_values,
                            key=f"{key_prefix}_{col_name}"
                        )
                        if selected:
                            df = df[df[col_name].isin(selected)]

                    elif filter_type == "text":
                        search_text = st.text_input(
                            col_name,
                            key=f"{key_prefix}_{col_name}"
                        )
                        if search_text:
                            df = df[df[col_name].astype(str).str.contains(search_text, case=False, na=False)]

                    elif filter_type == "date_range":
                        if pd.api.types.is_datetime64_any_dtype(df[col_name]):
                            min_date = df[col_name].min()
                            max_date = df[col_name].max()
                            date_range = st.date_input(
                                col_name,
                                value=(min_date, max_date),
                                key=f"{key_prefix}_{col_name}"
                            )
                            if len(date_range) == 2:
                                df = df[(df[col_name] >= pd.Timestamp(date_range[0])) &
                                       (df[col_name] <= pd.Timestamp(date_range[1]))]

    st.dataframe(df, width="stretch")

    return df


def display_table_with_actions(
    df: pd.DataFrame,
    actions: List[dict],
    row_id_column: str = "id",
    key_prefix: str = "action"
):
    """Display a table with action buttons for each row

    actions: List of dicts with keys: 'label', 'callback', 'icon' (optional)
    """

    if df.empty:
        st.info("No data available")
        return

    for idx, row in df.iterrows():
        with st.container():
            # Display row data in columns
            data_cols = st.columns([3] + [1] * len(actions))

            with data_cols[0]:
                st.write(row.to_dict())

            # Action buttons
            for action_idx, action in enumerate(actions):
                with data_cols[action_idx + 1]:
                    icon = action.get('icon', '')
                    button_label = f"{icon} {action['label']}" if icon else action['label']

                    if st.button(
                        button_label,
                        key=f"{key_prefix}_{row[row_id_column]}_{action_idx}"
                    ):
                        action['callback'](row)

            st.divider()


def display_expandable_table(
    df: pd.DataFrame,
    summary_columns: List[str],
    detail_callback: Callable[[Any], None],
    row_id_column: str = "id",
    key_prefix: str = "expand"
):
    """Display a table where each row can be expanded for details"""

    if df.empty:
        st.info("No data available")
        return

    for idx, row in df.iterrows():
        # Summary view
        summary_data = {col: row[col] for col in summary_columns if col in row}
        summary_text = " | ".join([f"{k}: {v}" for k, v in summary_data.items()])

        with st.expander(summary_text, expanded=False):
            detail_callback(row)


def export_dataframe(
    df: pd.DataFrame,
    filename: str = "data",
    formats: List[str] = ["csv", "json"],
    key_prefix: str = "export"
):
    """Provide export buttons for a dataframe"""

    if df.empty:
        return

    cols = st.columns(len(formats))

    for idx, fmt in enumerate(formats):
        with cols[idx]:
            if fmt == "csv":
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"{filename}.csv",
                    mime="text/csv",
                    key=f"{key_prefix}_csv"
                )
            elif fmt == "json":
                json_str = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name=f"{filename}.json",
                    mime="application/json",
                    key=f"{key_prefix}_json"
                )
            elif fmt == "excel":
                # Requires openpyxl
                try:
                    buffer = BytesIO()
                    df.to_excel(buffer, index=False, engine='openpyxl')
                    st.download_button(
                        label="📥 Download Excel",
                        data=buffer.getvalue(),
                        file_name=f"{filename}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"{key_prefix}_excel"
                    )
                except ImportError:
                    st.warning("Excel export requires openpyxl package")
