import streamlit as st
import base64
import requests
import json
from openai import OpenAI

# --- CONFIGURATION ---
st.set_page_config(
    page_title="PipeCheck MVP",
    page_icon="🚰",
    layout="centered"
)

# --- SIDEBAR: NAVIGATION & API KEY ---
st.sidebar.header("Navigation") 
# Fixed: Changed "nyc_search_tool_icon" to a proper emoji
app_mode = st.sidebar.radio("Choose Tool:", ["📸 Photo Analysis AI", "🔎 NYC Address Lookup"])

st.sidebar.divider()
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("OpenAI API Key (for Photo AI)", type="password")

# ==========================================
# PAGE 1: NYC ADDRESS LOOKUP
# ==========================================
if app_mode == "🔎 NYC Address Lookup":
    st.title("NYC Lead Service Line Lookup")
    st.markdown("Check the official NYC DEP records for your building's service line data.")
    
    # --- HELPER FUNCTION ---
    def fetch_nyc_data(address_query):
        DEP_URL = "https://services.arcgis.com/at3rDjch5X7i9Bag/arcgis/rest/services/NYC_WaterConnection_DEP24V10_202410_PG_REV3/FeatureServer/0/query"
        
        safe_address = address_query.strip().upper().replace("'", "''")
        
        params = {
            "f": "json",
            "where": f"UPPER(Address) LIKE '{safe_address}%'",
            "outFields": "Address,TBBL,Material,City_Owned,Record_Typ",
            "returnGeometry": "false",
            "spatialRel": "esriSpatialRelIntersects"
        }
        
        try:
            resp = requests.get(DEP_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("features"):
                return None, "No matching record found."
            
            return data["features"][0]["attributes"], None
            
        except Exception as e:
            return None, str(e)

    # --- STATUS NORMALIZATION LOGIC ---
    def normalize_status(material_str):
        if not material_str: return "UNKNOWN"
        s = str(material_str).lower()
        
        # 1. Check for SAFE materials first
        if "non-lead" in s: return "NON_LEAD"
        if "copper" in s: return "NON_LEAD"
        if "plastic" in s: return "NON_LEAD"
        if "brass" in s: return "NON_LEAD"
        
        # 2. Check for UNKNOWN
        if "unknown" in s: return "UNKNOWN"

        # 3. Check for LEAD (Only if not unknown)
        if "lead" in s: return "LEAD"
        
        # 4. Check for ambiguous/risky
        if "galv" in s: return "POSSIBLE_LEAD"
        
        return "UNKNOWN"

    # --- UI FOR SEARCH ---
    # Fixed: Updated the example address
    st.info("💡 Tip: Enter the street number and name (e.g., '30-29 33 STREET').")
    address_input = st.text_input("Enter NYC Address:")

    if st.button("Search Database"):
        if not address_input:
            st.warning("Please enter an address.")
        else:
            with st.spinner(f"Querying NYC DEP Database for '{address_input}'..."):
                attributes, error = fetch_nyc_data(address_input)
                
                if error:
                    st.error(f"❌ Result: {error}")
                else:
                    raw_material = attributes.get("Material", "Unknown")
                    status = normalize_status(raw_material)
                    full_address = attributes.get("Address", address_input)
                    
                    st.divider()
                    
                    if status == "LEAD":
                        st.error(f"⚠️ RECORD FOUND: LEAD")
                        st.write(f"The city records indicate **{raw_material}**.")
                    elif status == "POSSIBLE_LEAD":
                        st.warning(f"⚠️ RECORD FOUND: POSSIBLE LEAD ({raw_material})")
                        st.write("Galvanized pipes can trap lead particles or be connected to lead.")
                    elif status == "NON_LEAD":
                        st.success(f"✅ RECORD FOUND: NON-LEAD ({raw_material})")
                    else:
                        st.info(f"❓ RECORD FOUND: UNKNOWN MATERIAL")
                    
                    st.json({
                        "Address": full_address,
                        "Reported Material": raw_material,
                        "Record Type": attributes.get("Record_Typ"),
                        "City Owned": attributes.get("City_Owned")
                    })
                    st.caption("Data Source: NYC DEP Open Data (ArcGIS)")

# ==========================================
# PAGE 2: PHOTO ANALYSIS AI
# ==========================================
elif app_mode == "📸 Photo Analysis AI":
    st.title("📸 PipeCheck AI")
    st.markdown("""
    **Identify your water service line material.**
    Upload a photo and let AI estimate the material.
    *Note: This is an estimate, not a laboratory test.*
    """)

    st.divider()

    st.subheader("1. Prepare the Pipe")
    st.info("""
    **Scratch Test Instructions:**
    1. Find where the pipe enters your home.
    2. Scratch the pipe with a coin/key.
    3. Check if a magnet sticks.
    """)
    
    st.image("https://www.epa.gov/sites/default/files/styles/large/public/2016-01/lead-copper-galv-pipes.jpg?itok=5w_Zou_B", caption="Visual guide: Lead (left) vs Copper (middle) vs Galvanized (right).", use_column_width=True)

    col1, col2 = st.columns(2)
    with col1:
        scratch_result = st.selectbox("Scratch Test Color", ["I didn't scratch it", "Shiny Silver", "Penny/Copper Color", "Dull Gray/No Change"])
    with col2:
        magnet_result = st.selectbox("Magnet Test", ["I didn't check", "Magnet Sticks", "Magnet Does NOT Stick"])

    uploaded_file = st.file_uploader("Upload a clear photo", type=["jpg", "png", "jpeg"])

    def analyze_image_with_ai(image_bytes, user_notes, key):
        if not key: return None, "Missing API Key"
        client = OpenAI(api_key=key)
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        
        system_prompt = """
        You are a safety-focused expert trained to classify water service line materials.
        You MUST follow these rules:
        1. Never claim certainty. Always give a probability estimate.
        2. If image is poor/obstructed, return UNKNOWN.
        3. Do not give health advice.
        
        Definitions:
        - LEAD: dull gray, shiny silver when scratched, non-magnetic.
        - GALVANIZED: gray/dull, magnetic.
        - COPPER: orange/brown (penny color).
        
        Return JSON:
        {
          "material_estimate": "LEAD | COPPER | GALVANIZED_STEEL | PLASTIC | UNKNOWN | POSSIBLE_LEAD",
          "probability": 0.0-1.0,
          "reasoning": "...",
          "next_steps": "..."
        }
        """
        
        user_prompt = f"Context: Scratch={user_notes['scratch']}, Magnet={user_notes['magnet']}."

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content), None
        except Exception as e:
            return None, str(e)

    if st.button("Analyze Photo"):
        if not uploaded_file:
            st.warning("Please upload an image.")
        elif not api_key:
            st.error("Please enter your OpenAI API Key in the sidebar.")
        else:
            with st.spinner("AI is analyzing..."):
                st.image(uploaded_file, caption="Your Uploaded Photo", use_column_width=True)
                
                user_context = {"scratch": scratch_result, "magnet": magnet_result}
                result, error = analyze_image_with_ai(uploaded_file.getvalue(), user_context, api_key)
                
                if error:
                    st.error(f"Error: {error}")
                else:
                    mat = result.get("material_estimate", "UNKNOWN")
                    prob = result.get("probability", 0)
                    if mat in ["LEAD", "POSSIBLE_LEAD"]:
                        st.error(f"⚠️ {mat} ({prob*100:.0f}%)")
                    elif mat == "UNKNOWN":
                        st.warning(f"❓ {mat}")
                    else:
                        st.success(f"✅ {mat} ({prob*100:.0f}%)")
                    
                    st.write(result.get("reasoning"))
                    st.info(f"Next Steps: {result.get('next_steps')}")
