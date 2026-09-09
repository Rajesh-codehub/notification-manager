import streamlit as st
import requests
from datetime import datetime


# ============================================================
# Configuration
# ============================================================

import os

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
)


# ============================================================
# Streamlit Page Configuration
# ============================================================

st.set_page_config(
    page_title="Device Access Manager",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# Custom CSS
# ============================================================

st.markdown(
    """
    <style>
        .main {
            background-color: #f5f6f8;
        }

        .package {
            color: #6b7280;
            font-size: 12px;
            font-family: monospace;
            margin-bottom: 8px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# API Helper
# ============================================================

def api_request(method, endpoint, **kwargs):
    try:
        response = requests.request(
            method,
            f"{API_BASE_URL}{endpoint}",
            timeout=15,
            **kwargs,
        )

        return response

    except requests.exceptions.ConnectionError:
        st.error(
            "❌ Cannot connect to FastAPI. "
            "Make sure FastAPI is running on port 8000."
        )
        return None

    except requests.exceptions.RequestException as error:
        st.error(f"API error: {error}")
        return None


# ============================================================
# Get Devices
# ============================================================

def get_devices():
    response = api_request(
        "GET",
        "/api/devices",
    )

    if response is None:
        return []

    if response.ok:
        data = response.json()
        return data.get("devices", [])

    st.error(
        f"Failed to load devices. "
        f"HTTP {response.status_code}"
    )

    return []


# ============================================================
# Update Device Status
# ============================================================

def update_device_status(device_id, status):
    response = api_request(
        "PUT",
        "/api/update-status",
        json={
            "device_id": device_id,
            "status": status,
        },
    )

    if response is None:
        return False

    if response.ok:
        return True

    st.error(
        f"Failed to update device status. "
        f"HTTP {response.status_code}"
    )

    return False


# ============================================================
# Get Notifications
# ============================================================

def get_notifications(device_id):
    response = api_request(
        "GET",
        "/notifications",
        params={
            "device_id": device_id,
        },
    )

    if response is None:
        return []

    if response.ok:
        return response.json()

    st.error(
        f"Failed to load notifications. "
        f"HTTP {response.status_code}"
    )

    return []


# ============================================================
# Delete Notifications
# ============================================================

def delete_notifications(device_id):
    response = api_request(
        "DELETE",
        "/notifications",
        params={
            "device_id": device_id,
        },
    )

    if response is None:
        return False

    if response.ok:
        return True

    st.error(
        f"Failed to delete notifications. "
        f"HTTP {response.status_code}"
    )

    return False


# ============================================================
# Export Notifications
# ============================================================

def export_notifications(device_id):
    response = api_request(
        "GET",
        "/notifications/export",
        params={
            "device_id": device_id,
        },
    )

    if response is None:
        return None

    if response.ok:
        return response.content

    st.error(
        f"Failed to export notifications. "
        f"HTTP {response.status_code}"
    )

    return None


# ============================================================
# Timestamp Formatter
# ============================================================

def format_timestamp(timestamp):
    try:
        timestamp = int(timestamp)

        # Android normally sends milliseconds.
        # Handle seconds as well.
        if timestamp < 10_000_000_000:
            timestamp *= 1000

        date = datetime.fromtimestamp(
            timestamp / 1000
        )

        return date.strftime(
            "%d %b %Y, %I:%M:%S %p"
        )

    except Exception:
        return str(timestamp)


# ============================================================
# Session State
# ============================================================

if "page" not in st.session_state:
    st.session_state.page = "dashboard"

if "selected_device" not in st.session_state:
    st.session_state.selected_device = None

if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = False

if "csv_data" not in st.session_state:
    st.session_state.csv_data = None

if "csv_device_id" not in st.session_state:
    st.session_state.csv_device_id = None


# ============================================================
# Main Header
# ============================================================

st.title("📱 Device Access Manager")

st.caption(
    "Manage connected Android devices "
    "and view captured notifications."
)


# ============================================================
# NOTIFICATION PAGE
# ============================================================

if st.session_state.page == "notifications":

    device = st.session_state.selected_device

    if not device:
        st.session_state.page = "dashboard"
        st.rerun()

    # --------------------------------------------------------
    # Back Button
    # --------------------------------------------------------

    if st.button(
        "← Back to Devices",
        type="secondary",
    ):
        st.session_state.page = "dashboard"
        st.session_state.selected_device = None
        st.session_state.confirm_delete = False
        st.session_state.csv_data = None
        st.session_state.csv_device_id = None

        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # Device Information
    # --------------------------------------------------------

    device_name = (
        device.get("device_name")
        or "Unnamed Device"
    )

    device_id = (
        device.get("device_id")
        or "Unknown"
    )

    manufacturer = (
        device.get("manufacturer")
        or "Unknown"
    )

    model = (
        device.get("model")
        or "Unknown"
    )

    status = (
        device.get("status")
        or "inactive"
    )

    device_col1, device_col2 = st.columns(
        [4, 1]
    )

    with device_col1:
        st.subheader(
            f"🔔 {device_name}"
        )

        st.caption(
            f"Device ID: {device_id}"
        )

        st.write(
            f"**Manufacturer:** {manufacturer}"
        )

        st.write(
            f"**Model:** {model}"
        )

    with device_col2:
        if status == "active":
            st.success("ACTIVE")
        else:
            st.error("INACTIVE")

    st.divider()

    # --------------------------------------------------------
    # Load Notifications
    # --------------------------------------------------------

    notifications = get_notifications(
        device_id
    )

    # --------------------------------------------------------
    # Header + Export + Delete
    # --------------------------------------------------------

    title_col, export_col, delete_col = st.columns(
        [4, 1, 1]
    )

    with title_col:
        st.subheader(
            f"Notifications ({len(notifications)})"
        )

    # --------------------------------------------------------
    # Export CSV
    # --------------------------------------------------------

    with export_col:

        if notifications:

            if st.button(
                "📥 Export CSV",
                use_container_width=True,
                key="export_csv_button",
            ):

                csv_data = export_notifications(
                    device_id
                )

                if csv_data:

                    st.session_state.csv_data = (
                        csv_data
                    )

                    st.session_state.csv_device_id = (
                        device_id
                    )

                    st.rerun()

    # --------------------------------------------------------
    # Delete All
    # --------------------------------------------------------

    with delete_col:

        if notifications:

            if st.button(
                "🗑 Delete All",
                type="primary",
                use_container_width=True,
                key="delete_all_button",
            ):

                st.session_state.confirm_delete = True
                st.rerun()

    # --------------------------------------------------------
    # Download CSV Button
    # --------------------------------------------------------

    if (
        st.session_state.csv_data is not None
        and
        st.session_state.csv_device_id == device_id
    ):

        st.download_button(
            label="⬇️ Download Notifications CSV",
            data=st.session_state.csv_data,
            file_name=(
                f"notifications_{device_id}.csv"
            ),
            mime="text/csv",
            use_container_width=False,
            key="download_csv_button",
        )

    # --------------------------------------------------------
    # Delete Confirmation
    # --------------------------------------------------------

    if st.session_state.confirm_delete:

        st.warning(
            "⚠️ This will permanently delete all "
            "notifications for this device."
        )

        confirm_col1, confirm_col2 = st.columns(
            2
        )

        with confirm_col1:

            if st.button(
                "Yes, Delete Everything",
                type="primary",
                use_container_width=True,
                key="confirm_delete_button",
            ):

                deleted = delete_notifications(
                    device_id
                )

                if deleted:

                    st.session_state.confirm_delete = False
                    st.session_state.csv_data = None
                    st.session_state.csv_device_id = None

                    st.success(
                        "All notifications deleted."
                    )

                    st.rerun()

        with confirm_col2:

            if st.button(
                "Cancel",
                use_container_width=True,
                key="cancel_delete_button",
            ):

                st.session_state.confirm_delete = False
                st.rerun()

    # --------------------------------------------------------
    # Notification List
    # --------------------------------------------------------

    if not notifications:

        st.info(
            "🔔 No notifications captured "
            "for this device."
        )

    else:

        for notification in notifications:

            package_name = notification.get(
                "packageName",
                "Unknown Application",
            )

            title = notification.get(
                "title",
                "No title",
            )

            text = notification.get(
                "text",
                "",
            )

            sub_text = notification.get(
                "subText",
                "",
            )

            tag = notification.get(
                "tag",
                "",
            )

            post_time = notification.get(
                "postTime",
                "",
            )

            with st.container(
                border=True
            ):

                # Package
                st.markdown(
                    f'<div class="package">'
                    f'{package_name}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                # Title
                st.markdown(
                    f"### {title}"
                )

                # Notification text
                if text:
                    st.write(text)

                # Sub text
                if sub_text:
                    st.caption(
                        sub_text
                    )

                # Tag
                if tag:
                    st.caption(
                        f"🏷️ Tag: {tag}"
                    )

                # Time
                st.caption(
                    f"🕒 "
                    f"{format_timestamp(post_time)}"
                )


# ============================================================
# DASHBOARD PAGE
# ============================================================

else:

    # --------------------------------------------------------
    # Dashboard Header
    # --------------------------------------------------------

    header_col1, header_col2 = st.columns(
        [5, 1]
    )

    with header_col1:

        st.header(
            "Connected Devices"
        )

        st.caption(
            "Manage device access "
            "and view notifications."
        )

    with header_col2:

        if st.button(
            "↻ Refresh",
            use_container_width=True,
        ):
            st.rerun()

    st.divider()

    # --------------------------------------------------------
    # Get Devices
    # --------------------------------------------------------

    devices = get_devices()

    # --------------------------------------------------------
    # No Devices
    # --------------------------------------------------------

    if not devices:

        st.info(
            "📱 No devices registered yet."
        )

        st.caption(
            "Devices registered through the "
            "Android application will appear here."
        )

    # --------------------------------------------------------
    # Device List
    # --------------------------------------------------------

    else:

        st.write(
            f"**{len(devices)} device(s) registered**"
        )

        for index, device in enumerate(
            devices
        ):

            device_id = device.get(
                "device_id"
            )

            device_name = (
                device.get("device_name")
                or "Unnamed Device"
            )

            manufacturer = (
                device.get("manufacturer")
                or "N/A"
            )

            model = (
                device.get("model")
                or "N/A"
            )

            status = (
                device.get("status")
                or "inactive"
            )

            is_active = (
                status == "active"
            )

            # ------------------------------------------------
            # Device Card
            # ------------------------------------------------

            with st.container(
                border=True
            ):

                top_col1, top_col2 = st.columns(
                    [5, 1]
                )

                # Device Name
                with top_col1:

                    st.subheader(
                        f"📱 {device_name}"
                    )

                    st.caption(
                        f"Device ID: {device_id}"
                    )

                # Status
                with top_col2:

                    if is_active:
                        st.success(
                            "ACTIVE"
                        )
                    else:
                        st.error(
                            "INACTIVE"
                        )

                # Device Details
                info1, info2, info3 = st.columns(
                    3
                )

                with info1:
                    st.caption(
                        "MANUFACTURER"
                    )

                    st.write(
                        manufacturer
                    )

                with info2:
                    st.caption(
                        "MODEL"
                    )

                    st.write(
                        model
                    )

                with info3:
                    st.caption(
                        "REGISTERED"
                    )

                    created_at = device.get(
                        "created_at"
                    )

                    if created_at:

                        try:

                            registered_date = (
                                datetime.fromisoformat(
                                    created_at.replace(
                                        "Z",
                                        "+00:00",
                                    )
                                )
                            )

                            st.write(
                                registered_date.strftime(
                                    "%d %b %Y %H:%M"
                                )
                            )

                        except Exception:

                            st.write(
                                str(created_at)
                            )

                    else:

                        st.write(
                            "Unknown"
                        )

                st.divider()

                # ------------------------------------------------
                # Actions
                # ------------------------------------------------

                action_col1, action_col2 = (
                    st.columns([1, 2])
                )

                # ------------------------------------------------
                # Device Toggle
                # ------------------------------------------------

                with action_col1:

                    toggle_key = (
                        f"toggle_{device_id}"
                    )

                    previous_key = (
                        f"previous_status_{device_id}"
                    )

                    # Initialize toggle
                    if toggle_key not in st.session_state:

                        st.session_state[
                            toggle_key
                        ] = is_active

                    # Initialize previous status
                    if previous_key not in st.session_state:

                        st.session_state[
                            previous_key
                        ] = is_active

                    toggle_value = st.toggle(
                        "Device Access",
                        key=toggle_key,
                    )

                # ------------------------------------------------
                # Detect Toggle Change
                # ------------------------------------------------

                previous_value = (
                    st.session_state[
                        previous_key
                    ]
                )

                if (
                    toggle_value
                    != previous_value
                ):

                    new_status = (
                        "active"
                        if toggle_value
                        else "inactive"
                    )

                    success = (
                        update_device_status(
                            device_id,
                            new_status,
                        )
                    )

                    if success:

                        st.session_state[
                            previous_key
                        ] = toggle_value

                        device[
                            "status"
                        ] = new_status

                        if toggle_value:

                            st.toast(
                                f"{device_name} "
                                f"is now Active",
                                icon="🟢",
                            )

                        else:

                            st.toast(
                                f"{device_name} "
                                f"is now Inactive",
                                icon="🔴",
                            )

                    else:

                        st.session_state[
                            toggle_key
                        ] = previous_value

                        st.rerun()

                # ------------------------------------------------
                # View Notifications
                # ------------------------------------------------

                with action_col2:

                    if st.button(
                        "🔔 View Notifications",
                        key=(
                            f"notifications_"
                            f"{device_id}"
                        ),
                        use_container_width=True,
                    ):

                        st.session_state.selected_device = (
                            device
                        )

                        st.session_state.page = (
                            "notifications"
                        )

                        st.session_state.confirm_delete = (
                            False
                        )

                        st.session_state.csv_data = (
                            None
                        )

                        st.session_state.csv_device_id = (
                            None
                        )

                        st.rerun()
