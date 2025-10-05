from flask import Flask, render_template, request, jsonify
import os
import json
import traceback
import tempfile

# Attempt to import Lightkurve; if unavailable, lk will be None
try:
    import lightkurve as lk
except Exception:
    lk = None
try:
    import numpy as np  # used for basic calculations if Lightkurve is available
    import pandas as pd
except Exception:
    np = None
    pd = None

# Placeholder for loading the trained model
# import pickle
# model = pickle.load(open('path_to_your_model.pkl', 'rb'))

app = Flask(__name__)

@app.route('/')
def index():
    """Home page with input form."""
    return render_template('index.html')

@app.route('/explore')
def explore():
    """Advanced 3D dataset explorer with filters and real-time orbit visualisation."""
    return render_template('explore.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Handle form submission and return prediction.

    Currently uses placeholder values. Replace this logic
    with actual preprocessing and model prediction when integrating your model.
    """
    # Retrieve input values, with graceful fallback if missing
    try:
        orbital_period = float(request.form.get('orbital_period', 0))
    except ValueError:
        orbital_period = 0.0
    try:
        transit_duration = float(request.form.get('transit_duration', 0))
    except ValueError:
        transit_duration = 0.0
    try:
        planet_radius = float(request.form.get('planet_radius', 0))
    except ValueError:
        planet_radius = 0.0

    # Placeholder for feature array; extend as needed
    features = [orbital_period, transit_duration, planet_radius]

    # ----- Placeholder prediction logic -----
    # Replace this with model.predict(features) and model.predict_proba(features)
    predicted_class = 'Pending integration'
    class_probabilities = {
        'Confirmed exoplanet': 0.0,
        'Planet candidate': 0.0,
        'False positive': 0.0
    }

    # Placeholder for interpretability (e.g., SHAP values)
    feature_contributions = []

    return render_template(
        'result.html',
        predicted_class=predicted_class,
        probabilities=class_probabilities,
        contributions=feature_contributions,
        features=features
    )

# ------------------------------------------------------------------------------
# File upload and streaming analysis route
@app.route('/upload', methods=['POST'])
def upload():
    """Handle a time-series (light curve) file upload and perform transit search.

    This endpoint accepts a user-uploaded file (e.g., CSV of time vs flux),
    and would normally run a box least-squares (BLS) transit-search algorithm
    compiled to WebAssembly for speed and privacy. In this placeholder version
    we simply acknowledge receipt of the file and return a dummy detection.
    """
    uploaded_file = request.files.get('lightcurve')
    message = "No file uploaded or empty filename."
    analysis_result = None
    candidate_dips = []
    # Only proceed if a file has been uploaded
    if uploaded_file and uploaded_file.filename:
        filename = uploaded_file.filename
        try:
            # Read the uploaded file into a temporary pandas DataFrame
            if pd is not None:
                df = pd.read_csv(uploaded_file)
            else:
                df = None
            # If Lightkurve is available and the data frame looks OK
            if lk is not None and df is not None and {'time', 'flux'}.issubset(set(df.columns)):
                # Construct a LightCurve object from the user's time and flux
                lc = lk.LightCurve(time=df['time'].values, flux=df['flux'].values)
                # Flatten the light curve to remove trends
                flat_lc = lc.flatten()
                # Run a Box Least Squares period search; search within a reasonable period range
                # We restrict the minimum and maximum period to avoid excessive computation
                bls = flat_lc.to_periodogram(method='bls', minimum_period=0.2, maximum_period=30.0)
                best_period = float(bls.period_at_max_power)
                # Estimate transit depth (approximately) from the maximum power; convert to a radius ratio
                # This is a rough proxy: planet-to-star radius ratio ~ sqrt(depth)
                depth = float(bls.power_at_max_power)
                radius_ratio = np.sqrt(abs(depth)) if depth > 0 else 0.0
                # Use a default stellar radius of 1 R_sun for approximation
                planet_radius = radius_ratio  # in units relative to star radius, assume R_sun=1
                # Summarize the analysis
                analysis_result = {
                    'filename': filename,
                    'best_period': best_period,
                    'planet_radius': planet_radius
                }
                # Append the new planet to our data file under the 'custom' dataset
                try:
                    data_path = os.path.join('exoplanet_webapp', 'static', 'data', 'exoplanets.json')
                    with open(data_path, 'r') as f:
                        current_data = json.load(f)
                except Exception:
                    current_data = {}
                if 'custom' not in current_data:
                    current_data['custom'] = []
                # Use the filename (without extension) as the planet name
                planet_name = os.path.splitext(filename)[0]
                current_data['custom'].append({
                    'name': planet_name,
                    'period': best_period,
                    'radius': planet_radius
                })
                # Write updated data back to the JSON file
                try:
                    with open(data_path, 'w') as f:
                        json.dump(current_data, f, indent=2)
                except Exception:
                    pass
                message = f"Analysis complete: period={best_period:.3f} days, estimated radius={planet_radius:.3f} (R_star units)"
                # Provide a simple candidate dips list (empty for now)
                candidate_dips = []
            else:
                # If Lightkurve isn't available or the file lacks required columns
                file_head = uploaded_file.read(1024)
                message = f"Received file: {filename} (showing first {len(file_head)} bytes). "\
                          "Unable to analyze because Lightkurve is not installed or file format is incorrect."
        except Exception as e:
            # On any unexpected error, log and show traceback in message for debugging
            traceback_str = traceback.format_exc()
            message = f"Error processing file: {e}\n{traceback_str}"
    return render_template('upload_result.html', message=message, dips=candidate_dips, analysis=analysis_result)

if __name__ == '__main__':
    # Run the app in debug mode for development
    app.run(debug=True)
