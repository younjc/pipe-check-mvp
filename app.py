import streamlit as st
import base64
from openai import OpenAI
import json

# --- CONFIGURATION ---
st.set_page_config(
    page_title="PipeCheck AI MVP",
    page_icon="🚰",
    layout="centered"
)

# --- SIDEBAR: API KEY INPUT ---
st.sidebar.header="Configuration"
api_key = st.sidebar.text_input("Enter OpenAI API Key", type="password")
st.sidebar.info("This key is not saved. It is only used for this session.")

# --- MAIN UI ---
st.title("🚰 PipeCheck AI")
st.markdown("""
**Identify your water service line material.**
This tool uses AI to estimate pipe material based on visual evidence.
*Note: This is an estimate, not a laboratory test.*
""")

st.divider()

# --- STEP 1: EDUCATE & PREPARE ---
st.subheader("1. Prepare the Pipe")
st.info("""
Before taking a photo, perform the **Scratch Test**:
1. Find where the pipe enters your home (usually the basement).
2. Use a coin or key to gently scratch the outside of the pipe.
3. Check if a magnet sticks to it.
""")

# --- VISUAL AID ---
# This helps the user understand what they are looking for before uploading
st.image("https://www.epa.gov/sites/default/files/styles/large/public/2016-01/lead-copper-galv-pipes.jpg?itok=5w_Zou_B", caption="Visual guide: Lead (left) vs Copper (middle) vs Galvanized (right). Source: EPA", use_column_width=True)

# --- STEP 2: USER INPUTS ---
st.subheader("2. Upload & Verify")

col1, col2 = st.columns(2)
with col1:
    scratch_result = st.selectbox(
        "Scratch Test Color", 
        ["I didn't scratch it", "Shiny Silver", "Penny/Copper Color", "Dull Gray/No Change"]
    )
with col2:
    magnet_result = st.selectbox(
        "Magnet Test",
        ["I didn't check", "Magnet Sticks", "Magnet Does NOT Stick"]
    )

uploaded_file = st.file_uploader("Upload a clear photo of the pipe", type=["jpg", "png", "jpeg"])

# --- CORE LOGIC ---
def analyze_image(image_bytes, user_notes):
    if not api_key:
        return None, "Please enter an API Key in the sidebar."
    
    client = OpenAI(api_key=api_key)
    
    # Encode image
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    
    # STRICT SYSTEM PROMPT
    system_prompt = """
    You are a safety-focused expert trained to classify water service line materials.
    Your job is to analyze the image carefully, identify visible pipe material if possible, and explain your reasoning.
    
    You MUST follow these rules:
    1. Never claim certainty. Always give a probability estimate.
    2. If the image quality is poor, obstructed, too zoomed-out, or the pipe is painted or corroded, choose “UNKNOWN.”
    3. Only classify what you clearly see. Do not guess what is behind walls.
    4. Do not give health advice — just material classification and next-step recommendations.
    
    Definitions:
    - LEAD: dull gray pipe, easily scratched to reveal shiny silver metal, typically non-magnetic.
    - GALVANIZED_STEEL: hard, rigid steel pipe, usually magnetic, threaded fittings.
    - COPPER: orange/brown color unless heavily oxidized to green.
    - PLASTIC: white, black, blue, or other solid-colored polymer pipe.
    - POSSIBLE_LEAD: use when corrosion, paint, or dirt prevents confident classification but lead cannot be ruled out.

    Return your answer in this strict JSON format:
    {
      "material_estimate": "LEAD | COPPER | GALVANIZED_STEEL | PLASTIC | UNKNOWN | POSSIBLE_LEAD",
      "probability": 0.0-1.0,
      "reasoning": "Short explanation of visual evidence.",
      "next_steps": "Practical actions (magnet test, scratch test, official inspection)."
    }
    """

    user_prompt = f"""
    Analyze this water service line image.
    User Context from physical inspection:
    - Scratch Color: {user_notes['scratch']}
    - Magnet Test: {user_notes['magnet']}
    
    Incorporate this context into your probability estimate.
    """

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
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content), None
    except Exception as e:
        return None, str(e)

# --- STEP 3: EXECUTION ---
if st.button("Analyze Pipe Material"):
    if not uploaded_file:
        st.warning("Please upload an image first.")
    elif not api_key:
        st.error("Please enter your OpenAI API Key in the sidebar.")
    else:
        with st.spinner("Analyzing image patterns..."):
            # Display the uploaded image
            st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
            
            # Prepare context
            user_context = {
                "scratch": scratch_result,
                "magnet": magnet_result
            }
            
            # Call AI
            image_bytes = uploaded_file.getvalue()
            result, error = analyze_image(image_bytes, user_context)
            
            if error:
                st.error(f"Error: {error}")
            else:
                # --- DISPLAY RESULTS ---
                st.divider()
                st.subheader("Analysis Results")
                
                material = result.get("material_estimate", "UNKNOWN")
                prob = result.get("probability", 0)
                reasoning = result.get("reasoning", "No reasoning provided.")
                next_steps = result.get("next_steps", "Contact a professional.")
                
                # Dynamic Styling based on Safety
                if material == "LEAD" or material == "POSSIBLE_LEAD":
                    st.error(f"⚠️ DETECTION: {material} ({prob*100:.1f}% Confidence)")
                elif material == "UNKNOWN":
                    st.warning(f"❓ RESULT: {material}")
                else:
                    st.success(f"✅ ESTIMATE: {material} ({prob*100:.1f}% Confidence)")
                
                st.write(f"**Reasoning:** {reasoning}")
                
                st.info(f"**Recommended Next Steps:** {next_steps}")
                
                with st.expander("View Raw Data"):
                    st.json(result)
