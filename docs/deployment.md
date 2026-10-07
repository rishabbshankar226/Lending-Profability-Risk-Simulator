# Public demo preparation

The source branch and pull request are the review destination. **A public dashboard has not been deployed.** Merge/release and hosting remain a later review step under the project plan.

## Prepared Streamlit Community Cloud route

Use the [official deployment workflow](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app). After release approval:

1. Connect the authorized GitHub repository `rishabbshankar226/Lending-Profability-Risk-Simulator`.
2. Select the approved release branch and `app.py` as the entrypoint.
3. Set Python 3.12 in the deployment's advanced settings. Use the committed `requirements.txt`.
4. Deploy with the preloaded `data/applications.csv` and matching manifest; no secrets are required.
5. Verify the app is available to intended public viewers without invitations/login. Save the actual returned URL.

No hosting URL is guessed in this repository. No account was created, paid hosting selected, or deployment initiated during this implementation.

## Release verification still required

Check the default view and all five tabs in a real browser at desktop and narrow widths. Inspect actual chart marks, labels, wrapping, horizontal tables, keyboard navigation, console and network behavior. Exercise apply/reset, both cohort cutoffs, the stress grid, validation errors and both downloads; compare their run IDs and values with the displayed scenario.

The current cloud browser returned `ERR_CONNECTION_REFUSED` for the workspace localhost server. AppTest checks are simulated and cannot replace this inspection. Do not label the dashboard visually verified until it has occurred.

Capture screenshots and a 60–90 second walkthrough recording after these checks. Keep the script in `walkthrough.md`. Confirm the hosting service's current hibernation/resource behavior; measure cold starts separately from local calculations. A local server health response is not evidence of public availability.
