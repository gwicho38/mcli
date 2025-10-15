# Gravity Anomaly Visualization Dashboard

Monitor gravitational anomalies near politician locations and correlate with trading activity.

## Features

- **Interactive Map Visualization**: View politician locations on an interactive globe
- **Gravity Anomaly Heatmaps**: Visualize gravity measurements with color-coded intensity
- **Timeline Analysis**: Track gravity measurements over time
- **Trading Correlation**: Compare gravity data with politician trading activity
- **Multi-politician View**: Overview of all politicians or drill down to individuals

## Data Sources

- **Gravity Data**: Simulated from GRACE satellites and ground gravimeter patterns
  - In production: integrate with NASA GRACE Follow-On data, geological surveys
- **Politician Data**: Integrated with mcli's politician trading database
- **Location Data**: Official government records and district information

## Running Locally

```bash
# Install dependencies
pip install -r streamlit_requirements.txt

# Run the app
streamlit run streamlit_gravity_app.py
```

## Deployment to Streamlit Cloud

1. Push this repository to GitHub
2. Go to https://share.streamlit.io/
3. Deploy with main file: `streamlit_gravity_app.py`
4. Streamlit will automatically use `streamlit_requirements.txt`

## Integration with MCLI

This app is also available as a page in the main MCLI dashboard:

```bash
mcli ml dashboard
```

Then navigate to "Gravity Viz" in the sidebar.

## Future Enhancements

- [ ] Real-time GRACE satellite data integration
- [ ] Machine learning anomaly detection
- [ ] Automated alerts for unusual patterns
- [ ] Export functionality for reports
- [ ] Historical comparison tools
- [ ] Integration with geological survey databases
