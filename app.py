import streamlit as st
import numpy as np
import cv2
import pandas as pd
import time
from datetime import datetime
import math

st.set_page_config(page_title="Advanced Smart Conveyor Inspection", layout="wide")

st.title("🏭 Advanced Smart Conveyor Inspection and Sorting System")
st.write("This mini project simulates a realistic conveyor, moving belt lines, inspection machine, defect measurement, and automated sorting.")

# -------------------------------------------------
# Sidebar
# -------------------------------------------------
st.sidebar.header("Simulation Settings")
part_type = st.sidebar.selectbox("Part Type", ["Metal Plate", "Metal Block", "Gear"])
defect_type = st.sidebar.selectbox(
    "Defect Type",
    ["No Defect", "Scratch", "Crack", "Hole Defect", "Missing Material", "Dent"]
)
machine_health = st.sidebar.selectbox("Machine Health", ["GOOD", "WARNING", "CRITICAL"])
speed = st.sidebar.slider("Conveyor Speed", 2, 20, 8)
operator_name = st.sidebar.text_input("Operator Name", "Dhanasree")

st.sidebar.header("Machine Parameters")
temperature = st.sidebar.slider("Temperature (°C)", 20, 120, 72)
vibration = st.sidebar.slider("Vibration (mm/s)", 0.0, 2.0, 0.45, 0.01)
pressure = st.sidebar.slider("Pressure (bar)", 10, 80, 35)
rpm = st.sidebar.slider("Roller RPM", 100, 2500, 900)

col1, col2 = st.sidebar.columns(2)
start_sim = col1.button("Start")
reset_sim = col2.button("Reset")

# -------------------------------------------------
# Session state
# -------------------------------------------------
if "pass_count" not in st.session_state:
    st.session_state.pass_count = 0
if "rework_count" not in st.session_state:
    st.session_state.rework_count = 0
if "reject_count" not in st.session_state:
    st.session_state.reject_count = 0
if "history" not in st.session_state:
    st.session_state.history = []

if reset_sim:
    st.session_state.pass_count = 0
    st.session_state.rework_count = 0
    st.session_state.reject_count = 0
    st.session_state.history = []

# -------------------------------------------------
# Part sizes
# -------------------------------------------------
def get_part_size(part_name):
    if part_name == "Metal Plate":
        return {"length_mm": 180, "width_mm": 90, "height_mm": 12}
    elif part_name == "Metal Block":
        return {"length_mm": 150, "width_mm": 100, "height_mm": 80}
    elif part_name == "Gear":
        return {"outer_diameter_mm": 95, "inner_diameter_mm": 28, "thickness_mm": 18}
    return {}

# -------------------------------------------------
# Defect info
# -------------------------------------------------
def get_defect_info(defect_name):
    if defect_name == "Scratch":
        return {"length_mm": 18.5, "width_mm": 1.2, "x": 92, "y": 38}
    elif defect_name == "Crack":
        return {"length_mm": 14.2, "width_mm": 0.8, "x": 76, "y": 66}
    elif defect_name == "Hole Defect":
        return {"diameter_mm": 6.4, "x": 98, "y": 45}
    elif defect_name == "Missing Material":
        return {"length_mm": 12.0, "width_mm": 10.5, "x": 155, "y": 10}
    elif defect_name == "Dent":
        return {"diameter_mm": 8.8, "depth_mm": 1.7, "x": 108, "y": 52}
    return {"x": 0, "y": 0}

def get_severity(defect_name):
    if defect_name in ["Crack", "Missing Material"]:
        return "High"
    elif defect_name in ["Scratch", "Hole Defect"]:
        return "Medium"
    elif defect_name == "Dent":
        return "Low"
    return "None"

def get_confidence(defect_name):
    vals = {
        "No Defect": 99,
        "Scratch": 91,
        "Crack": 95,
        "Hole Defect": 89,
        "Missing Material": 96,
        "Dent": 87
    }
    return vals.get(defect_name, 80)

# -------------------------------------------------
# Decision logic
# -------------------------------------------------
def make_decision(defect_name, health_name, temp, vib):
    if defect_name == "No Defect" and health_name == "GOOD" and temp < 80 and vib < 0.6:
        return "PASS"
    elif health_name == "CRITICAL":
        return "REJECT"
    elif defect_name in ["Crack", "Missing Material"]:
        return "REJECT"
    elif defect_name in ["Scratch", "Dent", "Hole Defect"] or health_name == "WARNING":
        return "REWORK"
    return "PASS"

# -------------------------------------------------
# Drawing helpers
# -------------------------------------------------
def draw_roller(frame, cx, cy, angle):
    cv2.circle(frame, (cx, cy), 24, (115, 115, 115), -1)
    cv2.circle(frame, (cx, cy), 24, (70, 70, 70), 2)
    for a in [0, 90, 180, 270]:
        rad = math.radians(a + angle)
        x2 = int(cx + 18 * math.cos(rad))
        y2 = int(cy + 18 * math.sin(rad))
        cv2.line(frame, (cx, cy), (x2, y2), (50, 50, 50), 2)

def draw_belt_lines(frame, offset):
    for i in range(-100, 1200, 70):
        x = i + offset
        cv2.line(frame, (x, 178), (x, 312), (55, 55, 55), 3)

def draw_machine(frame, gate_down=False):
    # main inspection machine
    cv2.rectangle(frame, (500, 35), (660, 115), (95, 100, 125), -1)
    cv2.rectangle(frame, (500, 35), (660, 115), (180, 190, 220), 2)
    cv2.putText(frame, "Vision Sensor", (522, 82),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

    # support stand
    cv2.rectangle(frame, (570, 115), (590, 178), (135, 135, 145), -1)

    # laser / sensor line
    cv2.line(frame, (580, 115), (580, 175), (0, 255, 255), 2)

    # gate actuator
    cv2.rectangle(frame, (665, 70), (720, 105), (110, 110, 130), -1)
    cv2.rectangle(frame, (665, 70), (720, 105), (190, 190, 210), 2)
    cv2.putText(frame, "Gate", (675, 93),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    if gate_down:
        cv2.line(frame, (690, 105), (690, 180), (0, 255, 255), 6)
    else:
        cv2.line(frame, (690, 105), (720, 125), (0, 255, 255), 6)

def draw_realistic_plate(frame, x, y):
    cv2.rectangle(frame, (x, y), (x + 190, y + 95), (170, 178, 188), -1)
    cv2.rectangle(frame, (x, y), (x + 190, y + 95), (80, 80, 90), 2)
    cv2.line(frame, (x + 5, y + 10), (x + 185, y + 10), (210, 210, 220), 2)
    cv2.rectangle(frame, (x + 65, y + 30), (x + 125, y + 62), (120, 128, 140), -1)
    for hx, hy in [(x + 28, y + 22), (x + 162, y + 22), (x + 28, y + 72), (x + 162, y + 72)]:
        cv2.circle(frame, (hx, hy), 10, (60, 60, 70), -1)
        cv2.circle(frame, (hx, hy), 4, (28, 28, 35), -1)

def draw_realistic_block(frame, x, y):
    cv2.rectangle(frame, (x, y), (x + 155, y + 105), (158, 168, 182), -1)
    cv2.rectangle(frame, (x, y), (x + 155, y + 105), (78, 78, 88), 2)
    pts = np.array([[x, y], [x + 18, y - 12], [x + 173, y - 12], [x + 155, y]], np.int32)
    cv2.fillPoly(frame, [pts], (185, 195, 205))
    side = np.array([[x + 155, y], [x + 173, y - 12], [x + 173, y + 93], [x + 155, y + 105]], np.int32)
    cv2.fillPoly(frame, [side], (130, 140, 155))

def draw_realistic_gear(frame, x, y, rot_angle=0):
    cx, cy = x + 80, y + 60
    cv2.circle(frame, (cx, cy), 46, (175, 180, 188), -1)
    cv2.circle(frame, (cx, cy), 18, (65, 65, 72), -1)
    for angle in range(0, 360, 30):
        rad = np.deg2rad(angle + rot_angle)
        tx = int(cx + 55 * np.cos(rad))
        ty = int(cy + 55 * np.sin(rad))
        cv2.circle(frame, (tx, ty), 8, (175, 180, 188), -1)

def draw_defect(frame, x, y, defect_name):
    if defect_name == "Scratch":
        cv2.line(frame, (x + 25, y + 18), (x + 145, y + 76), (0, 0, 255), 3)

    elif defect_name == "Crack":
        pts = np.array([
            [x + 22, y + 75],
            [x + 50, y + 62],
            [x + 82, y + 70],
            [x + 110, y + 55],
            [x + 140, y + 66]
        ], np.int32)
        cv2.polylines(frame, [pts], False, (255, 0, 0), 2)

    elif defect_name == "Hole Defect":
        cv2.circle(frame, (x + 98, y + 45), 13, (0, 255, 255), 2)

    elif defect_name == "Missing Material":
        pts = np.array([[x + 150, y], [x + 190, y], [x + 190, y + 35]], np.int32)
        cv2.fillPoly(frame, [pts], (30, 30, 30))

    elif defect_name == "Dent":
        cv2.circle(frame, (x + 108, y + 52), 12, (95, 95, 95), -1)

def draw_part(frame, x, y, part_name, defect_name, inspected=False, decision="", gate_down=False, rot_angle=0):
    if part_name == "Metal Plate":
        draw_realistic_plate(frame, x, y)
        pw, ph = 190, 95
    elif part_name == "Metal Block":
        draw_realistic_block(frame, x, y)
        pw, ph = 173, 105
    else:
        draw_realistic_gear(frame, x, y, rot_angle)
        pw, ph = 160, 120

    if defect_name != "No Defect":
        draw_defect(frame, x, y, defect_name)

    if inspected:
        cv2.rectangle(frame, (x - 6, y - 6), (x + pw + 6, y + ph + 6), (0, 255, 255), 2)
        cv2.putText(frame, f"Detected: {defect_name}", (x - 5, y - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        d = get_defect_info(defect_name)
        if defect_name != "No Defect":
            px = x + d["x"]
            py = y + d["y"]
            cv2.circle(frame, (px, py), 6, (0, 255, 255), -1)
            cv2.putText(frame, f"Pos: ({d['x']}, {d['y']}) px", (x, y + ph + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)

        if decision:
            dcolor = (0, 170, 0) if decision == "PASS" else ((0, 165, 255) if decision == "REWORK" else (0, 0, 180))
            cv2.rectangle(frame, (x, y + ph + 35), (x + 165, y + ph + 70), dcolor, -1)
            cv2.putText(frame, decision, (x + 22, y + ph + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

def create_scene(x, inspected=False, decision="", roller_angle=0, belt_offset=0, gate_down=False, gear_angle=0):
    frame = np.zeros((560, 1220, 3), dtype=np.uint8)
    frame[:] = (22, 24, 35)

    cv2.putText(frame, "Advanced Smart Conveyor Motion Inspection", (300, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)

    # conveyor
    cv2.rectangle(frame, (40, 180), (1160, 320), (92, 92, 92), -1)
    cv2.rectangle(frame, (40, 180), (1160, 320), (145, 145, 145), 3)

    draw_belt_lines(frame, belt_offset)

    for i in range(90, 1120, 150):
        draw_roller(frame, i, 250, roller_angle)

    # inspection zone
    cv2.rectangle(frame, (500, 130), (690, 360), (0, 255, 255), 2)
    cv2.putText(frame, "Inspection Zone", (520, 118),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

    draw_machine(frame, gate_down)

    # sorting bins
    cv2.rectangle(frame, (735, 415), (845, 500), (0, 0, 180), -1)
    cv2.putText(frame, "REJECT", (745, 463), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    cv2.rectangle(frame, (875, 415), (1010, 500), (0, 165, 255), -1)
    cv2.putText(frame, "REWORK", (885, 463), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)

    cv2.rectangle(frame, (1040, 415), (1150, 500), (0, 170, 0), -1)
    cv2.putText(frame, "PASS", (1062, 463), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    draw_part(frame, x, 205, part_type, defect_type, inspected, decision, gate_down, gear_angle)

    # machine parameter panel
    cv2.rectangle(frame, (20, 20), (360, 72), (35, 35, 35), -1)
    cv2.putText(frame, f"T:{temperature} C   V:{vibration:.2f} mm/s   P:{pressure} bar", (28, 42),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1)
    cv2.putText(frame, f"RPM:{rpm}   Health:{machine_health}", (28, 63),
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1)

    # operator panel
    cv2.rectangle(frame, (20, 515), (860, 548), (35, 35, 35), -1)
    cv2.putText(frame, f"Operator: {operator_name} | Part: {part_type} | Defect: {defect_type}",
                (28, 538), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 1)

    return frame

# -------------------------------------------------
# UI top metrics
# -------------------------------------------------
st.subheader("📊 Dashboard")
a, b, c, d = st.columns(4)
a.metric("PASS Count", st.session_state.pass_count)
b.metric("REWORK Count", st.session_state.rework_count)
c.metric("REJECT Count", st.session_state.reject_count)
d.metric("Roller RPM", rpm)

# selected object size display
st.subheader("📏 Selected Object Size")
size_info = get_part_size(part_type)

if part_type == "Gear":
    s1, s2, s3 = st.columns(3)
    s1.metric("Outer Diameter", f"{size_info['outer_diameter_mm']} mm")
    s2.metric("Inner Diameter", f"{size_info['inner_diameter_mm']} mm")
    s3.metric("Thickness", f"{size_info['thickness_mm']} mm")
else:
    s1, s2, s3 = st.columns(3)
    s1.metric("Length", f"{size_info['length_mm']} mm")
    s2.metric("Width", f"{size_info['width_mm']} mm")
    s3.metric("Height", f"{size_info['height_mm']} mm")

frame_placeholder = st.empty()
status_placeholder = st.empty()
detail_placeholder = st.empty()
progress_bar = st.progress(0)

if not start_sim:
    frame_placeholder.image(
        create_scene(80, belt_offset=0, roller_angle=0, gear_angle=0),
        channels="BGR",
        use_container_width=True
    )
    status_placeholder.info("Choose settings and click Start.")

# -------------------------------------------------
# Motion simulation
# -------------------------------------------------
if start_sim:
    start_x = 60
    end_x = 930
    inspected = False
    decision = ""
    gate_down = False

    defect_info = get_defect_info(defect_type)
    severity = get_severity(defect_type)
    confidence = get_confidence(defect_type)

    positions = list(range(start_x, end_x, speed))
    roller_angle = 0
    belt_offset = 0
    gear_angle = 0

    for idx, x in enumerate(positions):
        if 500 <= x <= 690:
            inspected = True
            gate_down = True
            decision = make_decision(defect_type, machine_health, temperature, vibration)
        else:
            gate_down = False

        roller_angle += rpm / 90
        belt_offset = (belt_offset - speed * 2) % 70
        gear_angle += speed * 3

        frame = create_scene(
            x,
            inspected=inspected,
            decision=decision,
            roller_angle=roller_angle,
            belt_offset=belt_offset,
            gate_down=gate_down,
            gear_angle=gear_angle
        )
        frame_placeholder.image(frame, channels="BGR", use_container_width=True)

        percent = int((idx + 1) / len(positions) * 100)
        progress_bar.progress(percent)

        if inspected:
            if defect_type == "No Defect":
                detail_text = f"""
**Inspection Active**
- Defect: No Defect
- Confidence: {confidence}%
- Final Decision: {decision}
- Machine Temperature: {temperature} °C
- Vibration: {vibration:.2f} mm/s
- Pressure: {pressure} bar
"""
            else:
                detail_text = f"""
**Inspection Active**
- Defect Type: {defect_type}
- Severity: {severity}
- Confidence: {confidence}%
- Position: ({defect_info['x']}, {defect_info['y']}) px
- Final Decision: {decision}
- Machine Temperature: {temperature} °C
- Vibration: {vibration:.2f} mm/s
- Pressure: {pressure} bar
"""
                if "length_mm" in defect_info:
                    detail_text += f"- Length: {defect_info['length_mm']} mm\n"
                if "width_mm" in defect_info:
                    detail_text += f"- Width: {defect_info['width_mm']} mm\n"
                if "diameter_mm" in defect_info:
                    detail_text += f"- Diameter: {defect_info['diameter_mm']} mm\n"
                if "depth_mm" in defect_info:
                    detail_text += f"- Depth: {defect_info['depth_mm']} mm\n"

            detail_placeholder.markdown(detail_text)
            status_placeholder.warning(
                f"Inspection active | Defect: {defect_type} | Machine: {machine_health} | Decision: {decision}"
            )
        else:
            detail_placeholder.markdown("**Part moving on conveyor...**")
            status_placeholder.info(
                f"Part moving on conveyor... | Time: {datetime.now().strftime('%H:%M:%S')}"
            )

        time.sleep(0.08)

    if decision == "PASS":
        st.session_state.pass_count += 1
    elif decision == "REWORK":
        st.session_state.rework_count += 1
    elif decision == "REJECT":
        st.session_state.reject_count += 1

    st.session_state.history.append({
        "Time": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "Operator": operator_name,
        "Part": part_type,
        "Object Size": str(size_info),
        "Defect": defect_type,
        "Severity": severity,
        "Confidence (%)": confidence,
        "Position": f"({defect_info.get('x', 0)}, {defect_info.get('y', 0)})",
        "Temperature (°C)": temperature,
        "Vibration (mm/s)": vibration,
        "Pressure (bar)": pressure,
        "RPM": rpm,
        "Machine Health": machine_health,
        "Decision": decision
    })

    if decision == "PASS":
        status_placeholder.success("Simulation complete: PASS")
    elif decision == "REWORK":
        status_placeholder.warning("Simulation complete: REWORK")
    else:
        status_placeholder.error("Simulation complete: REJECT")

# -------------------------------------------------
# History table
# -------------------------------------------------
if st.session_state.history:
    st.subheader("📋 Inspection History")
    df = pd.DataFrame(st.session_state.history[::-1])
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download History CSV",
        data=csv,
        file_name="inspection_history.csv",
        mime="text/csv"
    )